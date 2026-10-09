"""Inference guard, timestamps, and credential redaction."""

import re
from datetime import datetime, timezone


def require_funding():
    # Direct transports cannot use credentials without a reserved dispatch permit.
    raise PermissionError(
        "Direct inference disabled: use a newly authorized, frozen evaluation plan"
    )


def now():
    return datetime.now(timezone.utc).isoformat()


def safe_content(value):
    if isinstance(value, dict):
        return {
            k: safe_content(v)
            for k, v in value.items()
            if not re.search(
                r"api.?key|access.?token|authorization|cookie|secret|headers", k, re.I
            )
        }
    if isinstance(value, list):
        return [safe_content(v) for v in value]
    if isinstance(value, str):
        return re.sub(r"(?:sk-|AIza)[A-Za-z0-9_-]{15,}", "[REDACTED]", value)
    return value
