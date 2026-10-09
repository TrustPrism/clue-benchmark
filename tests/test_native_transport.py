import httpx
import pytest

from clue_benchmark.native_adapters import normalize_response, request_payload
from clue_benchmark.native_transport import NativeTransport


def test_funding_guard_precedes_credentials_and_network(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    for vendor in ("google", "openai", "anthropic", "ollama"):
        with pytest.raises(PermissionError):
            NativeTransport(vendor)({"model": "fixture"})


def test_http_native_payload_one_attempt_and_error_receipt(monkeypatch):
    # Explicit offline mock transport; no network or authorized live inference.
    monkeypatch.setattr("clue_benchmark.native_transport.require_funding", lambda: None)
    monkeypatch.setenv("OPENAI_API_KEY", "fixture-only")
    seen = []

    def handle(request):
        seen.append(request)
        return httpx.Response(503, json={"error": {"type": "service_unavailable"}})

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        raw = NativeTransport("openai", client=client)(
            {"model": "fixture", "tools": []}
        )
    assert len(seen) == 1 and str(seen[0].url) == "https://api.openai.com/v1/responses"
    response = normalize_response("openai", raw)
    assert response["transport"] == "service_unavailable"
    assert not response["receipt"]["usage_present"]
    assert response["receipt"]["provider_status_code"] == 503
    assert "fixture-only" not in str(response)


@pytest.mark.parametrize("code", [400, 401, 403, 404, 429, 503])
def test_google_error_receipt_retains_only_safe_status(code):
    response = normalize_response(
        "google",
        {
            "transport_status": "provider_error",
            "error": {"status_code": code, "message": "credential-fixture"},
        },
    )
    assert response["receipt"]["provider_status_code"] == code
    assert not response["receipt"]["usage_present"]
    assert "credential-fixture" not in str(response["receipt"])


@pytest.mark.parametrize("code", [True, "401", 999, -1, None])
def test_invalid_error_status_never_becomes_receipt(code):
    response = normalize_response("google", {"error": {"status_code": code}})
    assert response["receipt"]["provider_status_code"] is None


def test_google_sdk_rejection_retains_status_without_message(monkeypatch):
    from google.genai import errors

    monkeypatch.setattr("clue_benchmark.native_transport.require_funding", lambda: None)

    class Models:
        calls = 0

        def generate_content(self, **payload):
            self.calls += 1
            raise errors.ClientError(
                400,
                {
                    "error": {
                        "status": "INVALID_ARGUMENT",
                        "message": "credential-fixture",
                    }
                },
            )

    class Client:
        models = Models()

    client = Client()
    response = normalize_response(
        "google", NativeTransport("google", google_client=client)({"model": "fixture"})
    )
    assert client.models.calls == 1
    assert response["receipt"]["provider_status_code"] == 400
    assert response["transport"] == "provider_error"
    assert "credential-fixture" not in str(response)


def test_google_sdk_payload_and_response_translation(monkeypatch):
    from google.genai import types

    monkeypatch.setattr("clue_benchmark.native_transport.require_funding", lambda: None)

    class Models:
        calls = 0

        def generate_content(self, **payload):
            self.calls += 1
            types.GenerateContentConfig(**payload["config"])
            return types.GenerateContentResponse(
                model_version="fixture",
                usage_metadata=types.GenerateContentResponseUsageMetadata(
                    prompt_token_count=10,
                    candidates_token_count=2,
                    thoughts_token_count=0,
                    total_token_count=12,
                ),
                candidates=[
                    types.Candidate(
                        content=types.Content(
                            parts=[
                                types.Part(
                                    function_call=types.FunctionCall(
                                        name="answer", args={"target": "A"}
                                    )
                                )
                            ]
                        ),
                        finish_reason="STOP",
                    )
                ],
            )

    class Client:
        models = Models()

    client = Client()
    payload = request_payload(
        "google",
        "fixture",
        {"suspects": ["A", "B"], "queries": [], "evidence": []},
        "answer",
        {"max_output_tokens": 100},
    )
    response = normalize_response(
        "google", NativeTransport("google", google_client=client)(payload)
    )
    assert client.models.calls == 1 and response["calls"] == [
        {"name": "answer", "arguments": {"target": "A"}}
    ]
    assert (
        response["returned_model"] == "fixture"
        and response["receipt"]["counters"]["total_token_count"] == 12
    )


def test_google_actual_wire_schema_and_no_argument_abstention(monkeypatch):
    import json

    from google import genai
    from google.genai import types

    monkeypatch.setattr("clue_benchmark.native_transport.require_funding", lambda: None)
    seen = []

    def handle(request):
        seen.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "modelVersion": "fixture",
                "usageMetadata": {
                    "promptTokenCount": 10,
                    "candidatesTokenCount": 2,
                    "thoughtsTokenCount": 0,
                    "totalTokenCount": 12,
                },
                "candidates": [
                    {
                        "content": {
                            "parts": [{"functionCall": {"name": "abstain", "args": {}}}]
                        }
                    }
                ],
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handle)) as http_client:
        client = genai.Client(
            api_key="fixture-only",
            http_options=types.HttpOptions(httpx_client=http_client),
        )
        try:
            payload = request_payload(
                "google",
                "fixture",
                {"suspects": ["A", "B"]},
                "answer",
                {"max_output_tokens": 100},
            )
            response = normalize_response(
                "google", NativeTransport("google", google_client=client)(payload)
            )
        finally:
            client.close()
    assert len(seen) == 1
    answer, abstain = seen[0]["tools"][0]["functionDeclarations"]
    assert "parameters" not in answer
    # The pinned SDK serializes the protobuf field's snake_case name.
    assert answer["parameters_json_schema"] == {
        "type": "object",
        "properties": {"target": {"type": "string", "enum": ["A", "B"]}},
        "required": ["target"],
        "additionalProperties": False,
    }
    assert abstain == {"name": "abstain", "description": "Execute one abstain action."}
    assert response["calls"] == [{"name": "abstain", "arguments": {}}]
