import hashlib
import os
import re
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import httpx

from .app_info import read_first_existing


GITHUB_REPO_URL = "https://github.com/quiwe/school-admin-ai-assistant"
GITHUB_LATEST_RELEASE_API_URL = "https://api.github.com/repos/quiwe/school-admin-ai-assistant/releases/latest"
GITHUB_LATEST_RELEASE_PAGE_URL = f"{GITHUB_REPO_URL}/releases/latest"
VERSION_POLICY_URL = "https://raw.githubusercontent.com/quiwe/school-admin-ai-assistant/main/version-policy.json"
WINDOWS_INSTALLER_PATTERN = re.compile(r"SchoolAdminAIAssistant-Setup-v?[\d.]+\.exe$", re.IGNORECASE)
MACOS_INSTALLER_PATTERN = re.compile(r"SchoolAdminAIAssistant-macOS-v?[\d.]+\.dmg$", re.IGNORECASE)


class UpdateError(RuntimeError):
    pass


@dataclass
class UpdateInfo:
    current_version: str
    latest_version: str
    has_update: bool
    release_url: str
    asset_name: str | None
    download_url: str | None
    asset_size: int | None
    digest: str | None
    published_at: str | None
    body: str
    min_supported_version: str | None = None
    force_update: bool = False
    update_required_message: str | None = None


@dataclass
class UpdateProgress:
    status: str = "idle"
    phase: str = "idle"
    message: str = ""
    bytes_downloaded: int = 0
    bytes_total: int | None = None
    percent: float = 0.0
    latest_version: str | None = None
    asset_name: str | None = None
    installer_path: str | None = None
    error: str | None = None


_progress_lock = threading.Lock()
_progress = UpdateProgress()


def set_update_progress(**kwargs) -> None:
    with _progress_lock:
        for key, value in kwargs.items():
            setattr(_progress, key, value)


def get_update_progress() -> dict:
    with _progress_lock:
        return {
            "status": _progress.status,
            "phase": _progress.phase,
            "message": _progress.message,
            "bytes_downloaded": _progress.bytes_downloaded,
            "bytes_total": _progress.bytes_total,
            "percent": _progress.percent,
            "latest_version": _progress.latest_version,
            "asset_name": _progress.asset_name,
            "installer_path": _progress.installer_path,
            "error": _progress.error,
        }


def current_version() -> str:
    return read_first_existing("VERSION", "0.0.0").strip()


def normalize_version(version: str) -> str:
    return version.strip().removeprefix("v").removeprefix("V")


def version_tuple(version: str) -> tuple[int, ...]:
    parts = re.findall(r"\d+", normalize_version(version))
    return tuple(int(part) for part in parts) or (0,)


def is_newer_version(candidate: str, current: str) -> bool:
    candidate_parts = version_tuple(candidate)
    current_parts = version_tuple(current)
    max_len = max(len(candidate_parts), len(current_parts))
    candidate_parts += (0,) * (max_len - len(candidate_parts))
    current_parts += (0,) * (max_len - len(current_parts))
    return candidate_parts > current_parts


def app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[3]


def updates_dir() -> Path:
    path = app_root() / "data" / "updates"
    path.mkdir(parents=True, exist_ok=True)
    return path


def check_for_update() -> UpdateInfo:
    local_version = current_version()
    policy = fetch_version_policy()
    try:
        latest_version, release_url = fetch_latest_release_from_redirect()
    except Exception as redirect_exc:
        try:
            release = fetch_latest_release_from_api()
            return apply_version_policy(update_info_from_release(release, local_version), policy)
        except Exception as api_exc:
            raise UpdateError(f"检查更新失败，请确认网络可以访问 GitHub：{redirect_exc}; {api_exc}") from api_exc

    has_update = bool(latest_version and is_newer_version(latest_version, local_version))
    if not has_update:
        return apply_version_policy(UpdateInfo(
            current_version=local_version,
            latest_version=latest_version or local_version,
            has_update=False,
            release_url=release_url,
            asset_name=None,
            download_url=None,
            asset_size=None,
            digest=None,
            published_at=None,
            body="",
        ), policy)

    try:
        release = fetch_latest_release_from_api()
        return apply_version_policy(update_info_from_release(release, local_version), policy)
    except Exception:
        asset_name = installer_name(latest_version)
        return apply_version_policy(UpdateInfo(
            current_version=local_version,
            latest_version=latest_version,
            has_update=True,
            release_url=release_url,
            asset_name=asset_name,
            download_url=f"{GITHUB_REPO_URL}/releases/download/v{latest_version}/{asset_name}",
            asset_size=None,
            digest=None,
            published_at=None,
            body="发现新版本。GitHub API 暂时不可用，仍可下载安装包更新。",
        ), policy)


def fetch_version_policy() -> dict:
    try:
        with httpx.Client(timeout=8, follow_redirects=True) as client:
            response = client.get(VERSION_POLICY_URL, headers={"User-Agent": "SchoolAdminAIAssistant"})
            response.raise_for_status()
            data = response.json()
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def apply_version_policy(info: UpdateInfo, policy: dict) -> UpdateInfo:
    min_supported_version = normalize_version(str(policy.get("min_supported_version") or "").strip())
    force_update = bool(min_supported_version and is_newer_version(min_supported_version, info.current_version))
    info.min_supported_version = min_supported_version or None
    info.force_update = force_update
    info.update_required_message = str(policy.get("update_required_message") or "").strip() or None
    if force_update:
        info.has_update = True
        if not info.update_required_message:
            info.update_required_message = f"当前版本 {info.current_version} 已低于最低可用版本 {min_supported_version}，请更新后继续使用。"
    return info


def fetch_latest_release_from_redirect() -> tuple[str, str]:
    with httpx.Client(timeout=12, follow_redirects=True) as client:
        response = client.get(GITHUB_LATEST_RELEASE_PAGE_URL, headers={"User-Agent": "SchoolAdminAIAssistant"})
        response.raise_for_status()
        release_url = str(response.url)
    match = re.search(r"/releases/tag/(v?[\d][^/?#]*)", release_url)
    if not match:
        raise UpdateError("无法从 GitHub 发布页识别最新版本号。")
    return normalize_version(match.group(1)), release_url


def fetch_latest_release_from_api() -> dict:
    with httpx.Client(timeout=15, follow_redirects=True) as client:
        response = client.get(
            GITHUB_LATEST_RELEASE_API_URL,
            headers={"Accept": "application/vnd.github+json", "User-Agent": "SchoolAdminAIAssistant"},
        )
        response.raise_for_status()
        return response.json()


def update_info_from_release(release: dict, local_version: str) -> UpdateInfo:
    latest_version = normalize_version(release.get("tag_name") or release.get("name") or "")
    asset = find_installer_asset(release.get("assets") or [], latest_version)
    return UpdateInfo(
        current_version=local_version,
        latest_version=latest_version or local_version,
        has_update=bool(latest_version and is_newer_version(latest_version, local_version)),
        release_url=release.get("html_url") or "",
        asset_name=asset.get("name") if asset else None,
        download_url=asset.get("browser_download_url") if asset else None,
        asset_size=asset.get("size") if asset else None,
        digest=asset.get("digest") if asset else None,
        published_at=release.get("published_at"),
        body=(release.get("body") or "").strip(),
    )


def installer_name(version: str) -> str:
    if sys.platform == "darwin":
        return f"SchoolAdminAIAssistant-macOS-v{normalize_version(version)}.dmg"
    return f"SchoolAdminAIAssistant-Setup-v{normalize_version(version)}.exe"


def find_installer_asset(assets: list[dict], latest_version: str) -> dict | None:
    expected_name = installer_name(latest_version)
    pattern = MACOS_INSTALLER_PATTERN if sys.platform == "darwin" else WINDOWS_INSTALLER_PATTERN
    extension = ".dmg" if sys.platform == "darwin" else ".exe"
    for asset in assets:
        if asset.get("name") == expected_name:
            return asset
    for asset in assets:
        name = asset.get("name") or ""
        if pattern.search(name):
            return asset
    for asset in assets:
        name = asset.get("name") or ""
        if name.lower().endswith(extension):
            return asset
    return None


def download_installer(info: UpdateInfo, progress_callback: Callable[[int, int | None], None] | None = None) -> Path:
    if not info.download_url or not info.asset_name:
        raise UpdateError("最新 Release 中没有找到当前系统可用的安装包。")

    target = updates_dir() / info.asset_name
    temp_target = target.with_suffix(target.suffix + ".download")

    try:
        with httpx.Client(timeout=None, follow_redirects=True) as client:
            with client.stream("GET", info.download_url, headers={"User-Agent": "SchoolAdminAIAssistant"}) as response:
                response.raise_for_status()
                bytes_downloaded = 0
                bytes_total = info.asset_size
                if not bytes_total:
                    content_length = response.headers.get("content-length")
                    bytes_total = int(content_length) if content_length and content_length.isdigit() else None
                if progress_callback:
                    progress_callback(bytes_downloaded, bytes_total)
                with temp_target.open("wb") as file:
                    for chunk in response.iter_bytes(chunk_size=1024 * 512):
                        if chunk:
                            file.write(chunk)
                            bytes_downloaded += len(chunk)
                            if progress_callback:
                                progress_callback(bytes_downloaded, bytes_total)
        temp_target.replace(target)
    except Exception as exc:
        if temp_target.exists():
            temp_target.unlink(missing_ok=True)
        raise UpdateError(f"下载安装包失败：{exc}") from exc

    if info.asset_size and target.stat().st_size != info.asset_size:
        target.unlink(missing_ok=True)
        raise UpdateError("安装包下载不完整，请稍后重试。")

    verify_digest(target, info.digest)
    return target


def verify_digest(path: Path, digest: str | None) -> None:
    if not digest or not digest.startswith("sha256:"):
        return
    expected = digest.split(":", 1)[1].lower()
    actual = hashlib.sha256(path.read_bytes()).hexdigest().lower()
    if actual != expected:
        path.unlink(missing_ok=True)
        raise UpdateError("安装包校验失败，请稍后重试。")


def download_and_launch_update() -> Path:
    info = check_for_update()
    if not info.has_update:
        raise UpdateError("当前已经是最新版本。")
    installer = download_installer(info)
    launch_installer(installer)
    return installer


def start_download_and_launch_update() -> None:
    progress = get_update_progress()
    if progress["status"] in {"checking", "downloading", "launching"}:
        return

    set_update_progress(
        status="checking",
        phase="checking",
        message="正在检查新版本...",
        bytes_downloaded=0,
        bytes_total=None,
        percent=0.0,
        latest_version=None,
        asset_name=None,
        installer_path=None,
        error=None,
    )
    threading.Thread(target=download_and_launch_update_in_background, daemon=True).start()


def download_and_launch_update_in_background() -> None:
    try:
        info = check_for_update()
        if not info.has_update:
            set_update_progress(
                status="completed",
                phase="completed",
                message="当前已经是最新版本。",
                percent=100.0,
                latest_version=info.latest_version,
                asset_name=info.asset_name,
            )
            return

        set_update_progress(
            status="downloading",
            phase="downloading",
            message="正在下载安装包...",
            bytes_downloaded=0,
            bytes_total=info.asset_size,
            percent=0.0,
            latest_version=info.latest_version,
            asset_name=info.asset_name,
        )

        def update_download_progress(bytes_downloaded: int, bytes_total: int | None) -> None:
            percent = round(bytes_downloaded / bytes_total * 100, 1) if bytes_total else 0.0
            set_update_progress(
                status="downloading",
                phase="downloading",
                message=f"正在下载安装包... {percent:.1f}%" if bytes_total else "正在下载安装包...",
                bytes_downloaded=bytes_downloaded,
                bytes_total=bytes_total,
                percent=percent,
            )

        installer = download_installer(info, update_download_progress)
        set_update_progress(
            status="launching",
            phase="launching",
            message="下载完成，正在启动安装程序...",
            bytes_downloaded=installer.stat().st_size,
            bytes_total=info.asset_size or installer.stat().st_size,
            percent=100.0,
            installer_path=str(installer),
        )
        launch_installer(installer)
        set_update_progress(
            status="completed",
            phase="completed",
            message="安装程序已启动，请按提示完成更新。",
            percent=100.0,
            installer_path=str(installer),
        )
    except Exception as exc:
        set_update_progress(
            status="error",
            phase="error",
            message="自动更新失败，请打开发布页手动下载。",
            error=str(exc)[:500],
        )


def launch_installer(installer: Path) -> None:
    try:
        if sys.platform == "darwin":
            subprocess.Popen(["open", str(installer)], cwd=str(installer.parent), close_fds=True)
        else:
            subprocess.Popen([str(installer)], cwd=str(installer.parent), close_fds=True)
    except Exception as exc:
        raise UpdateError(f"启动安装程序失败：{exc}") from exc

    if getattr(sys, "frozen", False):
        threading.Thread(target=exit_soon, daemon=True).start()


def exit_soon() -> None:
    time.sleep(1.5)
    os._exit(0)
