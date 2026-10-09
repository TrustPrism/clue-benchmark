"""Concrete single-attempt native transports. Inference is always gated first.

Constructing this object neither reads credentials nor opens a connection.
No fallback provider, response repair, SDK retry, or automatic tool execution.
"""

import os

from .provider_events import require_funding

ENDPOINTS = {
    "openai": "https://api.openai.com/v1/responses",
    "anthropic": "https://api.anthropic.com/v1/messages",
    "ollama": "http://127.0.0.1:11434/api/chat",
}


def _camel(value):
    if isinstance(value, dict):
        return {
            k.split("_")[0] + "".join(p.title() for p in k.split("_")[1:]): _camel(v)
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [_camel(v) for v in value]
    return value


class NativeTransport:
    def __init__(self, vendor, timeout_seconds=600, client=None, google_client=None):
        if vendor not in (*ENDPOINTS, "google"):
            raise ValueError("Unsupported native vendor")
        if not 0 < timeout_seconds <= 600:
            raise ValueError("Undeclared timeout")
        self.vendor = vendor
        self.timeout = timeout_seconds
        self.client = client
        self.google_client = google_client

    def __call__(self, payload):
        require_funding()
        return self._request(payload)

    def call_authorized(self, payload, permit):
        """Dispatch only through an authorized evaluation reservation."""
        from .community_evaluation import DispatchPermit

        if not isinstance(permit, DispatchPermit):
            raise PermissionError("A reserved community dispatch permit is required")
        permit.check(self.vendor, payload)
        return self._request(payload)

    def _request(self, payload):
        if self.vendor == "google":
            return self._google(payload)
        import httpx

        headers = {"content-type": "application/json"}
        if self.vendor == "openai":
            headers["authorization"] = "Bearer " + os.environ["OPENAI_API_KEY"]
        elif self.vendor == "anthropic":
            headers.update(
                {
                    "x-api-key": os.environ["ANTHROPIC_API_KEY"],
                    "anthropic-version": "2023-06-01",
                }
            )
        owned = self.client is None
        client = self.client or httpx.Client(
            timeout=self.timeout,
            follow_redirects=False,
            transport=httpx.HTTPTransport(retries=0),
        )
        try:
            response = client.post(
                ENDPOINTS[self.vendor],
                json=payload,
                headers=headers,
                timeout=self.timeout,
            )
            try:
                raw = response.json()
            except ValueError:
                raw = {
                    "error": {
                        "type": "non_json_response",
                        "status_code": response.status_code,
                    }
                }
            if not isinstance(raw, dict):
                raw = {
                    "error": {
                        "type": "non_object_response",
                        "status_code": response.status_code,
                    }
                }
            if response.status_code != 200:
                raw["http_status_code"] = response.status_code
                raw["transport_status"] = (
                    "service_unavailable"
                    if response.status_code in (429, 502, 503, 504)
                    else "provider_error"
                )
            return raw
        except httpx.TimeoutException as exc:
            raise TimeoutError("Native transport timed out; receipt unknown") from exc
        except httpx.TransportError as exc:
            raise ConnectionError("Native connection failed; receipt unknown") from exc
        finally:
            if owned:
                client.close()

    def _google(self, payload):
        import httpx
        from google import genai
        from google.genai import errors, types

        owned = self.google_client is None
        client = self.google_client or genai.Client(
            api_key=os.environ["GEMINI_API_KEY"],
            http_options=types.HttpOptions(
                timeout=int(self.timeout * 1000),
                retry_options=types.HttpRetryOptions(attempts=1),
            ),
        )
        try:
            response = client.models.generate_content(**payload)
            # Use the SDK's typed response, including raw numeric usage. Tool
            # arguments have only target, so field casing is unchanged.
            return _camel(response.model_dump(mode="json", exclude_none=True))
        except errors.APIError as exc:
            return {
                "transport_status": "service_unavailable"
                if exc.code in (429, 502, 503, 504)
                else "provider_error",
                "error": {"type": type(exc).__name__, "status_code": exc.code},
            }
        except httpx.TimeoutException as exc:
            raise TimeoutError("Google transport timed out; receipt unknown") from exc
        except httpx.TransportError as exc:
            raise ConnectionError("Google connection failed; receipt unknown") from exc
        finally:
            if owned:
                client.close()
