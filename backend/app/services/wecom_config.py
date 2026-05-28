from dataclasses import dataclass

from sqlalchemy.orm import Session

from .runtime_config import get_setting, upsert_setting


@dataclass
class WeComConfig:
    enabled: bool = False
    bot_id: str = ""
    secret: str | None = None
    secret_configured: bool = False
    allowlist: list[str] | None = None


def normalize_allowlist(value: str | list[str] | None) -> list[str]:
    if isinstance(value, str):
        raw_items = value.replace(",", " ").split()
    else:
        raw_items = value or []
    seen: set[str] = set()
    normalized: list[str] = []
    for item in raw_items:
        userid = (item or "").strip()
        if userid and userid not in seen:
            normalized.append(userid)
            seen.add(userid)
    return normalized


def _bool_setting(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def load_wecom_config(db: Session, include_secret: bool = False) -> WeComConfig:
    secret = get_setting(db, "wecom_secret")
    bot_id = get_setting(db, "wecom_bot_id") or ""
    allowlist = normalize_allowlist(get_setting(db, "wecom_allowlist"))
    return WeComConfig(
        enabled=_bool_setting(get_setting(db, "wecom_enabled")),
        bot_id=bot_id.strip(),
        secret=secret if include_secret else None,
        secret_configured=bool(secret),
        allowlist=allowlist,
    )


def save_wecom_config(
    db: Session,
    *,
    enabled: bool,
    bot_id: str,
    secret: str | None,
    allowlist: list[str] | str | None,
) -> WeComConfig:
    normalized_allowlist = normalize_allowlist(allowlist)
    upsert_setting(db, "wecom_enabled", "1" if enabled else "0")
    upsert_setting(db, "wecom_bot_id", bot_id.strip())
    if secret is not None and secret.strip():
        upsert_setting(db, "wecom_secret", secret.strip())
    upsert_setting(db, "wecom_allowlist", "\n".join(normalized_allowlist))
    db.commit()
    return load_wecom_config(db)
