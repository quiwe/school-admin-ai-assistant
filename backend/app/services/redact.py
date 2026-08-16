"""Redact secrets from error messages before exposing them to clients."""
import re

# Common secret shapes: OpenAI/DeepSeek keys, Google AI keys, and
# `key=` / `api_key=` / `token=` / `secret=` query-string assignments.
_SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{6,}"),
    re.compile(r"\bAIza[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"(?i)\b(key|api_key|token|secret|access_key|admin_key|password)=([^&\s'\"]{8,})"),
]

# Defense-in-depth: long opaque tokens that contain at least one digit
# (hashes, UUIDs, raw keys). The digit requirement avoids mangling
# harmless all-letter words such as hostnames.
_OPAQUE_TOKEN = re.compile(r"(?=[A-Za-z0-9_-]{0,24}\d)[A-Za-z0-9_-]{4}([A-Za-z0-9_-]{12,})")


def _redact(match: re.Match) -> str:
    value = match.group(0)
    if "=" in value:
        return value.split("=", 1)[0] + "=***"
    return value[:4] + "***"


def safe_error_message(exc: BaseException) -> str:
    message = str(exc)
    for pattern in _SECRET_PATTERNS:
        message = pattern.sub(_redact, message)
    message = _OPAQUE_TOKEN.sub(lambda m: m.group(0)[:4] + "***", message)
    return message[:500]
