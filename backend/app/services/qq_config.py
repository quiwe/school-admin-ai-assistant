from dataclasses import dataclass

from sqlalchemy.orm import Session

from ..settings import settings
from .bot_config_utils import bool_setting, normalize_allowlist, normalize_id
from .runtime_config import get_setting, upsert_setting


@dataclass
class QQConfig:
    enabled: bool = False
    app_id: str = ""
    app_secret: str | None = None
    app_secret_configured: bool = False
    sandbox: bool = False
    owner_openid: str = ""
    allowlist: list[str] | None = None


normalize_openid = normalize_id


def load_qq_config(db: Session, include_secret: bool = False) -> QQConfig:
    app_secret = get_setting(db, "qq_app_secret") or settings.qq_secret
    app_id = get_setting(db, "qq_app_id") or settings.qq_appid or ""
    owner_openid = get_setting(db, "qq_owner_openid") or settings.qq_owner_openid or ""
    allowlist = normalize_allowlist(get_setting(db, "qq_allowlist") or settings.qq_allowlist)
    owner_openid = normalize_id(owner_openid)
    allowlist = [openid for openid in allowlist if openid != owner_openid]
    return QQConfig(
        enabled=bool_setting(get_setting(db, "qq_enabled"), settings.qq_enabled),
        app_id=app_id.strip(),
        app_secret=app_secret if include_secret else None,
        app_secret_configured=bool(app_secret),
        sandbox=bool_setting(get_setting(db, "qq_sandbox"), settings.qq_sandbox),
        owner_openid=owner_openid,
        allowlist=allowlist,
    )


def save_qq_config(
    db: Session,
    *,
    enabled: bool,
    app_id: str,
    app_secret: str | None,
    sandbox: bool,
    owner_openid: str,
    allowlist: list[str] | str | None,
) -> QQConfig:
    normalized_owner = normalize_openid(owner_openid)
    normalized_allowlist = [
        openid for openid in normalize_allowlist(allowlist) if openid != normalized_owner
    ]
    upsert_setting(db, "qq_enabled", "1" if enabled else "0")
    upsert_setting(db, "qq_app_id", app_id.strip())
    if app_secret is not None and app_secret.strip():
        upsert_setting(db, "qq_app_secret", app_secret.strip())
    upsert_setting(db, "qq_sandbox", "1" if sandbox else "0")
    upsert_setting(db, "qq_owner_openid", normalized_owner)
    upsert_setting(db, "qq_allowlist", "\n".join(normalized_allowlist))
    db.commit()
    return load_qq_config(db)
