import plistlib
import sys
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..models import Setting


SETTING_KEY = "auto_start_enabled"
WINDOWS_RUN_NAME = "SchoolAdminAIAssistant"
MACOS_LAUNCH_AGENT_LABEL = "com.quiwe.school-admin-ai-assistant"


class AutoStartError(RuntimeError):
    pass


@dataclass
class AutoStartStatus:
    enabled: bool
    current_enabled: bool
    supported: bool
    target_path: str
    message: str = ""


def is_packaged_app() -> bool:
    return bool(getattr(sys, "frozen", False))


def is_supported() -> bool:
    return is_packaged_app() and sys.platform in {"win32", "darwin"}


def executable_path() -> Path:
    return Path(sys.executable).resolve()


def read_preference(db: Session) -> bool:
    row = db.query(Setting).filter(Setting.key == SETTING_KEY).first()
    if row is None or row.value == "":
        return True
    return row.value.lower() in {"1", "true", "yes", "on"}


def save_preference(db: Session, enabled: bool) -> None:
    row = db.query(Setting).filter(Setting.key == SETTING_KEY).first()
    value = "true" if enabled else "false"
    if row:
        row.value = value
    else:
        db.add(Setting(key=SETTING_KEY, value=value))
    db.commit()


def get_status(db: Session) -> AutoStartStatus:
    preferred = read_preference(db)
    current = os_auto_start_enabled() if is_supported() else False
    target = str(executable_path()) if is_packaged_app() else ""
    message = ""
    if not is_supported():
        message = "开机自启动仅在 Windows/macOS 安装版中生效。"
    elif preferred != current:
        message = "设置已保存，系统启动项会在下次启动软件时自动同步。"
    return AutoStartStatus(
        enabled=preferred,
        current_enabled=current,
        supported=is_supported(),
        target_path=target,
        message=message,
    )


def apply_preference(db: Session) -> AutoStartStatus:
    preferred = read_preference(db)
    if is_supported():
        set_os_auto_start(preferred)
    return get_status(db)


def apply_saved_preference() -> None:
    db = SessionLocal()
    try:
        apply_preference(db)
    except Exception:
        # 自启动同步失败不应阻断主程序启动，用户仍可在设置页重新保存。
        pass
    finally:
        db.close()


def set_preference_and_apply(db: Session, enabled: bool) -> AutoStartStatus:
    save_preference(db, enabled)
    if is_supported():
        set_os_auto_start(enabled)
    return get_status(db)


def set_os_auto_start(enabled: bool) -> None:
    if sys.platform == "win32":
        set_windows_auto_start(enabled)
        return
    if sys.platform == "darwin":
        set_macos_auto_start(enabled)
        return
    raise AutoStartError("当前系统不支持开机自启动。")


def os_auto_start_enabled() -> bool:
    if sys.platform == "win32":
        return windows_auto_start_enabled()
    if sys.platform == "darwin":
        return macos_auto_start_enabled()
    return False


def windows_auto_start_enabled() -> bool:
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run") as key:
            value, _ = winreg.QueryValueEx(key, WINDOWS_RUN_NAME)
    except FileNotFoundError:
        return False
    return str(executable_path()) in value


def set_windows_auto_start(enabled: bool) -> None:
    import winreg

    with winreg.CreateKeyEx(
        winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Run",
        0,
        winreg.KEY_SET_VALUE,
    ) as key:
        if enabled:
            winreg.SetValueEx(key, WINDOWS_RUN_NAME, 0, winreg.REG_SZ, f'"{executable_path()}"')
        else:
            try:
                winreg.DeleteValue(key, WINDOWS_RUN_NAME)
            except FileNotFoundError:
                pass


def launch_agent_path() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{MACOS_LAUNCH_AGENT_LABEL}.plist"


def macos_auto_start_enabled() -> bool:
    path = launch_agent_path()
    if not path.exists():
        return False
    try:
        with path.open("rb") as file:
            data = plistlib.load(file)
    except Exception:
        return False
    args = data.get("ProgramArguments") or []
    return str(executable_path()) in args and bool(data.get("RunAtLoad"))


def set_macos_auto_start(enabled: bool) -> None:
    path = launch_agent_path()
    if not enabled:
        if path.exists():
            path.unlink()
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "Label": MACOS_LAUNCH_AGENT_LABEL,
        "ProgramArguments": [str(executable_path())],
        "RunAtLoad": True,
        "KeepAlive": False,
        "StandardOutPath": str(Path.home() / "Library" / "Logs" / "SchoolAdminAIAssistant-autostart.log"),
        "StandardErrorPath": str(Path.home() / "Library" / "Logs" / "SchoolAdminAIAssistant-autostart.err.log"),
    }
    with path.open("wb") as file:
        plistlib.dump(data, file)
