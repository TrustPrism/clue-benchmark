"""Native answer/abstention payloads and normalized provider receipts.

No model substitution, function-call text emulation, repair, or SDK retries.
The normalized contract retains vendor identity and raw numeric usage separately.
"""

import json

from .provider_events import now, require_funding


def tool_schemas(observation, stage):
    if stage not in ("answer", "answering"):
        raise ValueError("Only answer/abstention evaluation is supported")
    output = []
    for name in ("answer", "abstain"):
        parameters = {
            "type": "object",
            "properties": {
                "target": {"type": "string", "enum": observation["suspects"]}
            }
            if name == "answer"
            else {},
            "required": ["target"] if name == "answer" else [],
            "additionalProperties": False,
        }
        output.append(
            {
                "name": name,
                "description": f"Execute one {name} action.",
                "parameters": parameters,
            }
        )
    return output


def request_payload(vendor, model, observation, stage, settings):
    tools = tool_schemas(observation, stage)
    prompt = json.dumps(observation, sort_keys=True)
    if vendor == "google":
        return {
            "model": model,
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "config": {
                "max_output_tokens": settings["max_output_tokens"],
                "temperature": settings.get("temperature", 0),
                "thinking_config": {
                    "thinking_level": settings.get("thinking_level", "low")
                },
                "candidate_count": 1,
                "tools": [{"function_declarations": tools}],
                "tool_config": {
                    "function_calling_config": {
                        "mode": "ANY",
                        "allowed_function_names": [t["name"] for t in tools],
                    }
                },
                "automatic_function_calling": {"disable": True},
                "http_options": {"retry_options": {"attempts": 1}},
            },
        }
    if vendor == "openai":
        return {
            "model": model,
            "input": prompt,
            "max_output_tokens": settings["max_output_tokens"],
            "reasoning": {"effort": settings.get("reasoning_effort", "low")},
            "store": False,
            "tools": [{"type": "function", **t, "strict": True} for t in tools],
            "tool_choice": "required",
            "parallel_tool_calls": False,
        }
    if vendor == "anthropic":
        return {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": settings["max_output_tokens"],
            "tools": [
                {
                    "name": t["name"],
                    "description": t["description"],
                    "input_schema": t["parameters"],
                }
                for t in tools
            ],
            "tool_choice": {"type": "any", "disable_parallel_tool_use": True},
        }
    if vendor == "ollama":
        return {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "tools": [{"type": "function", "function": t} for t in tools],
            "options": {
                "num_predict": settings["max_output_tokens"],
                "num_ctx": settings.get("context_tokens", 32768),
                "temperature": settings.get("temperature", 0),
                "seed": settings.get("seed", 0),
            },
        }
    raise ValueError("Unsupported vendor")


def normalize_response(vendor, raw):
    calls = []
    text = ""
    usage = raw.get("usage", {})
    model = raw.get("model")
    finish = None
    prompt = output = thought = total = None
    if vendor == "google":
        usage = raw.get("usageMetadata", {})
        candidates = raw.get("candidates", [])
        for candidate in candidates:
            for part in candidate.get("content", {}).get("parts", []):
                if "functionCall" in part:
                    calls.append(
                        {
                            "name": part["functionCall"].get("name"),
                            "arguments": part["functionCall"].get("args", {}),
                        }
                    )
                if not part.get("thought"):
                    text += part.get("text", "")
        finish = candidates[0].get("finishReason") if candidates else None
        model = raw.get("modelVersion")
        prompt = usage.get("promptTokenCount")
        output = usage.get("candidatesTokenCount")
        thought = usage.get("thoughtsTokenCount")
        total = usage.get("totalTokenCount")
    elif vendor == "openai":
        for item in raw.get("output", []):
            if item.get("type") == "function_call":
                args = item.get("arguments")
                try:
                    args = json.loads(args) if isinstance(args, str) else args
                except json.JSONDecodeError:
                    args = None
                calls.append({"name": item.get("name"), "arguments": args})
            if item.get("type") == "message":
                text += "".join(c.get("text", "") for c in item.get("content", []))
        prompt = usage.get("input_tokens")
        billed = usage.get("output_tokens")
        thought = usage.get("output_tokens_details", {}).get("reasoning_tokens")
        if type(billed) is int and type(thought) is int and 0 <= thought <= billed:
            output = billed - thought
        total = usage.get("total_tokens")
        finish = raw.get("status")
    elif vendor == "anthropic":
        for item in raw.get("content", []):
            if item.get("type") == "tool_use":
                calls.append({"name": item.get("name"), "arguments": item.get("input")})
            if item.get("type") == "text":
                text += item.get("text", "")
        prompt = usage.get("input_tokens")
        output = usage.get("output_tokens")
        thought = 0
        # Cache counters are kept raw; unimplemented rate decomposition fails closed.
        if any(
            usage.get(k, 0)
            for k in ("cache_creation_input_tokens", "cache_read_input_tokens")
        ):
            prompt = None
        total = prompt + output if type(prompt) is int and type(output) is int else None
        finish = raw.get("stop_reason")
    elif vendor == "ollama":
        message = raw.get("message", {})
        text = message.get("content", "")
        calls = [
            {
                "name": c.get("function", {}).get("name"),
                "arguments": c.get("function", {}).get("arguments"),
            }
            for c in message.get("tool_calls", [])
        ]
        prompt = raw.get("prompt_eval_count")
        output = raw.get("eval_count")
        thought = 0
        total = prompt + output if type(prompt) is int and type(output) is int else None
        finish = raw.get("done_reason")
        usage = {
            k: raw.get(k)
            for k in (
                "prompt_eval_count",
                "eval_count",
                "total_duration",
                "load_duration",
                "prompt_eval_duration",
                "eval_duration",
            )
        }
    else:
        raise ValueError("Unsupported vendor")
    counters = {
        "prompt_token_count": prompt,
        "candidates_token_count": output,
        "thoughts_token_count": thought,
        "total_token_count": total,
        "tool_use_prompt_token_count": None,
    }
    if raw.get("error"):
        text = json.dumps(raw["error"], sort_keys=True)
    return {
        "transport": raw.get("transport_status", "ok"),
        "calls": calls,
        "text": text,
        "returned_model": model,
        "finish_reason": finish,
        "receipt": {
            "vendor": vendor,
            "raw_usage": usage,
            "usage_present": bool(usage),
            "counters": counters,
            "invalid_counters": [
                k
                for k, v in counters.items()
                if v is not None and (type(v) is not int or v < 0)
            ],
            "thinking_separately_observed": vendor in ("google", "openai"),
            "finish_reason": finish,
        },
    }


class NativeAdapter:
    def __init__(self, vendor, model, settings, transport):
        self.vendor = vendor
        self.model = model
        self.settings = settings
        self.transport = transport

    def __call__(self, observation, stage):
        require_funding()
        started = now()
        raw = self.transport(
            request_payload(self.vendor, self.model, observation, stage, self.settings)
        )
        result = normalize_response(self.vendor, raw)
        result.update(started_at=started, ended_at=now())
        return result
