"""Shared utilities for QQ Bot and WeCom Bot configuration."""


def normalize_id(value: str | None) -> str:
    return (value or "").strip()


def normalize_allowlist(value: str | list[str] | None) -> list[str]:
    if isinstance(value, str):
        raw_items = value.replace(",", " ").split()
    else:
        raw_items = value or []
    seen: set[str] = set()
    normalized: list[str] = []
    for item in raw_items:
        uid = normalize_id(item)
        if uid and uid not in seen:
            normalized.append(uid)
            seen.add(uid)
    return normalized


def bool_setting(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}
