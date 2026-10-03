"""Native Google and Ollama transports. No tool emulation or automatic retries."""

import json
import os
import platform
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass
from importlib.metadata import version


class ProtocolError(RuntimeError):
    pass


class UsageError(ProtocolError):
    pass


@dataclass
class Reply:
    assistant: object
    calls: list
    usage: dict
    model_version: str | None
    text: str = ""


TOOLS = {
    "request_clue": {
        "description": "Request the next clue for a listed topic.",
        "parameters": {
            "type": "object",
            "properties": {"query_id": {"type": "string"}},
            "required": ["query_id"],
        },
    },
    "submit_answer": {
        "description": "Submit your one final answer and end the episode.",
        "parameters": {
            "type": "object",
            "properties": {"suspect_id": {"type": "string"}},
            "required": ["suspect_id"],
        },
    },
}


def checked_usage(input_tokens, output_tokens, thinking_tokens=None, total=None):
    for value in (input_tokens, output_tokens):
        if type(value) is not int or value < 0:
            raise UsageError("missing or invalid usage accounting")
    if thinking_tokens is not None and (
        type(thinking_tokens) is not int or thinking_tokens < 0
    ):
        raise UsageError("invalid thinking accounting")
    computed = input_tokens + output_tokens
    if total is not None and total != computed:
        raise UsageError("inconsistent usage accounting")
    return dict(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        thinking_tokens=thinking_tokens,
        total_tokens=computed,
    )


def error_label(exc):
    # Provider exceptions can contain request URLs, headers, or credentials.
    # Never serialize their text, traceback, or HTTP bodies.
    if isinstance(exc, UsageError):
        return "missing_usage"
    if isinstance(exc, TimeoutError) or "Timeout" in type(exc).__name__:
        return "timeout"
    code = getattr(exc, "code", None)
    if code == 429:
        return "quota_error"
    if code in (400, 404, 422) or isinstance(exc, ProtocolError):
        return "protocol_incompatible"
    if code in (401, 403):
        return "access_denied"
    return "provider_error"


def local_json(endpoint, payload=None, timeout=20):
    data = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(
        "http://127.0.0.1:11434/api/" + endpoint,
        data=data,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def ollama_identity(model="qwen3.5:9b"):
    record = next((m for m in local_json("tags")["models"] if m["name"] == model), None)
    if record is None:
        raise ProtocolError("requested local model is not installed")
    info = local_json("show", {"model": model})
    details = info["details"]
    capacity = next(
        (v for k, v in info["model_info"].items() if k.endswith(".context_length")),
        None,
    )
    if details.get("quantization_level") != "Q4_K_M":
        raise ProtocolError("local model must use Q4_K_M")
    if not {"tools", "thinking"} <= set(info.get("capabilities", [])):
        raise ProtocolError("local model needs native tools and thinking")
    if type(capacity) is not int or capacity < 32768:
        raise ProtocolError("insufficient local context capacity")
    return {
        "requested_model": model,
        "digest": record["digest"],
        "quantization": details["quantization_level"],
        "ollama_version": local_json("version")["version"],
        "context_capacity": capacity,
        "num_ctx": 32768,
        "capabilities": sorted(info["capabilities"]),
        "distribution_parameters": info.get("parameters"),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "hardware": subprocess.run(
            ["sysctl", "hw.memsize", "machdep.cpu.brand_string"],
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip()
        if platform.system() == "Darwin"
        else platform.processor(),
    }


class OllamaProvider:
    paid = False

    def __init__(self, model, settings, identity):
        self.name = model
        self.model = model.split("/", 1)[1]
        self.settings = settings
        self.identity = identity
        if ollama_identity(self.model) != identity:
            raise ProtocolError("Ollama runtime drift; prepare a new manifest")

    def start(self, prompt):
        self.last_usage = None
        self.last_result_bound = 0
        return [{"role": "user", "content": prompt}]

    def input_tokens_bound(self, messages, tools):
        if self.last_usage is None:
            return len(json.dumps(messages, ensure_ascii=False).encode()) + 2048
        return (
            self.last_usage["input_tokens"]
            + self.last_usage["output_tokens"]
            + self.last_result_bound
            + 256
        )

    def add_results(self, messages, reply, results):
        messages.append(reply.assistant)
        self.last_result_bound = (
            len(json.dumps(results, ensure_ascii=False).encode()) + 256
        )
        for name, result in results:
            messages.append(
                {"role": "tool", "tool_name": name, "content": json.dumps(result)}
            )

    def generate(self, messages, tools, max_output, timeout):
        response = local_json(
            "chat",
            {
                "model": self.model,
                "messages": messages,
                "tools": [
                    {"type": "function", "function": {"name": n, **TOOLS[n]}}
                    for n in tools
                ],
                "stream": False,
                "think": self.settings["think"],
                "options": {
                    "num_ctx": self.identity["num_ctx"],
                    "num_predict": max_output,
                    "temperature": self.settings["temperature"],
                    "top_p": self.settings["top_p"],
                    "top_k": self.settings["top_k"],
                    "presence_penalty": self.settings["presence_penalty"],
                    "repeat_penalty": self.settings["repeat_penalty"],
                },
                "keep_alive": "10m",
            },
            timeout=timeout,
        )
        usage = checked_usage(
            response.get("prompt_eval_count"), response.get("eval_count")
        )
        self.last_usage = usage
        assistant = response["message"]
        calls = [
            (c["function"]["name"], c["function"]["arguments"])
            for c in assistant.get("tool_calls", [])
        ]
        # eval_count covers all generated tokens, including the thinking channel;
        # Ollama does not provide a separate thinking-token count.
        usage["thinking_accounting"] = "included in eval_count; component unavailable"
        return Reply(
            assistant, calls, usage, response.get("model"), assistant.get("content", "")
        )

    def check_loaded_context(self):
        loaded = next(
            (m for m in local_json("ps")["models"] if m["name"] == self.model), None
        )
        if loaded is None or loaded.get("context_length") != self.identity["num_ctx"]:
            raise ProtocolError("effective local context differs from frozen num_ctx")
        if loaded.get("digest") != self.identity["digest"]:
            raise ProtocolError("loaded local digest differs from frozen digest")
        return {
            k: loaded.get(k) for k in ("digest", "context_length", "size", "size_vram")
        }


class GoogleProvider:
    paid = True

    def __init__(self, model, settings, identity):
        from google import genai
        from google.genai import types

        if not os.environ.get("GOOGLE_API_KEY"):
            raise ProtocolError("GOOGLE_API_KEY is unavailable")
        self.name = model
        self.model = model.split("/", 1)[1]
        self.settings = settings
        self.identity = identity
        self.types = types
        self.client = genai.Client(
            api_key=os.environ["GOOGLE_API_KEY"],
            http_options=types.HttpOptions(
                retry_options=types.HttpRetryOptions(attempts=1)
            ),
        )
        available = self.client.models.get(model=self.model)
        if (
            available.input_token_limit < identity["context_capacity"]
            or available.output_token_limit < settings["max_tokens"]
            or "generateContent" not in available.supported_actions
        ):
            raise ProtocolError("Gemini access or context capacity is incompatible")
        self.access_identity = {
            "requested_model": self.model,
            "returned_name": available.name,
            "model_version": available.version,
            "input_token_limit": available.input_token_limit,
            "output_token_limit": available.output_token_limit,
            "google_genai_version": version("google-genai"),
        }

    def start(self, prompt):
        self.last_usage = None
        self.last_result_bound = 0
        return [self.types.Content(role="user", parts=[self.types.Part(text=prompt)])]

    def add_results(self, messages, reply, results):
        self.last_result_bound = (
            len(json.dumps(results, ensure_ascii=False).encode()) + 256
        )
        # Keep the original model Content, including opaque thought signatures.
        messages.append(reply.assistant)
        messages.append(
            self.types.Content(
                role="user",
                parts=[
                    self.types.Part.from_function_response(name=n, response=r)
                    for n, r in results
                ],
            )
        )

    def input_tokens_bound(self, messages, tools):
        # The Developer API counts contents but does not accept tool schemas.
        # Bound the small schema separately; never count opaque signature bytes.
        result = self.client.models.count_tokens(
            model=self.model,
            contents=messages,
            config=self.types.CountTokensConfig(
                http_options=self.types.HttpOptions(
                    timeout=20000, retry_options=self.types.HttpRetryOptions(attempts=1)
                )
            ),
        )
        if type(result.total_tokens) is not int or result.total_tokens < 0:
            raise UsageError("missing input token count")
        schema_bound = len(
            json.dumps(
                [{"name": n, **TOOLS[n]} for n in tools], ensure_ascii=False
            ).encode()
        )
        counted_bound = result.total_tokens + schema_bound + 256
        usage_bound = (
            (
                self.last_usage["input_tokens"]
                + self.last_usage["output_tokens"]
                + self.last_result_bound
                + 256
            )
            if self.last_usage
            else 0
        )
        return max(counted_bound, usage_bound)

    def generate(self, messages, tools, max_output, timeout):
        types = self.types
        response = self.client.models.generate_content(
            model=self.model,
            contents=messages,
            config=types.GenerateContentConfig(
                temperature=self.settings["temperature"],
                max_output_tokens=max_output,
                thinking_config=types.ThinkingConfig(
                    thinking_level=self.settings["thinking_level"],
                    include_thoughts=True,
                ),
                tools=[
                    types.Tool(
                        function_declarations=[
                            types.FunctionDeclaration(name=n, **TOOLS[n]) for n in tools
                        ]
                    )
                ],
                automatic_function_calling=types.AutomaticFunctionCallingConfig(
                    disable=True
                ),
                http_options=types.HttpOptions(
                    timeout=max(1, int(timeout * 1000)),
                    retry_options=types.HttpRetryOptions(attempts=1),
                ),
            ),
        )
        raw = response.usage_metadata
        if raw is None or raw.thoughts_token_count is None:
            raise UsageError("missing Gemini thinking-token accounting")
        candidates = raw.candidates_token_count
        if type(candidates) is not int:
            raise UsageError("missing Gemini output-token accounting")
        usage = checked_usage(
            raw.prompt_token_count,
            candidates + raw.thoughts_token_count,
            raw.thoughts_token_count,
            raw.total_token_count,
        )
        usage["thinking_accounting"] = (
            "candidates plus thoughts; thoughts billed as output"
        )
        self.last_usage = usage
        if not response.candidates or response.candidates[0].content is None:
            return Reply(None, [], usage, response.model_version)
        assistant = response.candidates[0].content
        calls = [
            (p.function_call.name, dict(p.function_call.args or {}))
            for p in assistant.parts or []
            if p.function_call
        ]
        text = "".join(p.text or "" for p in assistant.parts or [] if not p.thought)
        return Reply(assistant, calls, usage, response.model_version, text)


def make_provider(model, settings, identity):
    if model.startswith("google/"):
        return GoogleProvider(model, settings, identity)
    if model.startswith("ollama/"):
        return OllamaProvider(model, settings, identity)
    raise ProtocolError("unsupported native provider; no fallback is allowed")
