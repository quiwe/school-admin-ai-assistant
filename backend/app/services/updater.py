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


GITEE_OWNER = os.environ.get("GITEE_OWNER", "quiwe")
GITEE_REPO = os.environ.get("GITEE_REPO", "school-admin-ai-assistant")
GITEE_ACCESS_TOKEN = os.environ.get("GITEE_ACCESS_TOKEN")
GITEE_REPO_URL = os.environ.get("GITEE_REPO_URL", f"https://gitee.com/{GITEE_OWNER}/{GITEE_REPO}")
GITEE_LATEST_RELEASE_API_URL = os.environ.get(
    "GITEE_LATEST_RELEASE_API_URL",
    f"https://gitee.com/api/v5/repos/{GITEE_OWNER}/{GITEE_REPO}/releases/latest",
)
GITEE_VERSION_POLICY_URL = os.environ.get(
    "GITEE_VERSION_POLICY_URL",
    f"{GITEE_REPO_URL}/raw/main/version-policy.json",
)
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
    update_source: str | None = None


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
    errors: list[str] = []
    try:
        return apply_version_policy(fetch_gitee_update_info(local_version), policy)
    except Exception as exc:
        errors.append(f"Gitee：{exc}")

    try:
        return apply_version_policy(fetch_github_update_info(local_version), policy)
    except Exception as exc:
        errors.append(f"GitHub：{exc}")
        raise UpdateError(f"检查更新失败：{'; '.join(errors)}") from exc


def fetch_github_update_info(local_version: str) -> UpdateInfo:
    try:
        latest_version, release_url = fetch_latest_release_from_redirect()
    except Exception as redirect_exc:
        try:
            release = fetch_latest_release_from_api()
            return update_info_from_github_release(release, local_version)
        except Exception as api_exc:
            raise UpdateError(f"检查更新失败，请确认网络可以访问 GitHub：{redirect_exc}; {api_exc}") from api_exc

    has_update = bool(latest_version and is_newer_version(latest_version, local_version))
    if not has_update:
        return UpdateInfo(
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
            update_source="github",
        )

    try:
        release = fetch_latest_release_from_api()
        return update_info_from_github_release(release, local_version)
    except Exception:
        asset_name = installer_name(latest_version)
        return UpdateInfo(
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
            update_source="github",
        )


def fetch_version_policy() -> dict:
    for url in [GITEE_VERSION_POLICY_URL, VERSION_POLICY_URL]:
        try:
            with httpx.Client(timeout=8, follow_redirects=True) as client:
                response = client.get(url, headers={"User-Agent": "SchoolAdminAIAssistant"})
                response.raise_for_status()
                data = response.json()
                return data if isinstance(data, dict) else {}
        except Exception:
            continue
    return {}


def gitee_params() -> dict[str, str]:
    return {"access_token": GITEE_ACCESS_TOKEN} if GITEE_ACCESS_TOKEN else {}


def fetch_gitee_release_from_api() -> dict:
    with httpx.Client(timeout=12, follow_redirects=True) as client:
        response = client.get(
            GITEE_LATEST_RELEASE_API_URL,
            params=gitee_params(),
            headers={"Accept": "application/json", "User-Agent": "SchoolAdminAIAssistant"},
        )
        response.raise_for_status()
        return response.json()


def fetch_gitee_attach_files(release: dict) -> list[dict]:
    release_id = release.get("id")
    if not release_id:
        return []
    url = f"https://gitee.com/api/v5/repos/{GITEE_OWNER}/{GITEE_REPO}/releases/{release_id}/attach_files"
    try:
        with httpx.Client(timeout=12, follow_redirects=True) as client:
            response = client.get(url, params=gitee_params(), headers={"User-Agent": "SchoolAdminAIAssistant"})
            response.raise_for_status()
            data = response.json()
            return data if isinstance(data, list) else []
    except Exception:
        return []


def fetch_gitee_update_info(local_version: str) -> UpdateInfo:
    release = fetch_gitee_release_from_api()
    latest_version = normalize_version(release.get("tag_name") or release.get("name") or "")
    if not latest_version:
        raise UpdateError("无法从 Gitee Release 识别最新版本号。")
    tag = release.get("tag_name") or f"v{latest_version}"
    release_url = release.get("html_url") or f"{GITEE_REPO_URL}/releases/tag/{tag}"
    assets = normalize_release_assets(release)
    if not assets:
        assets = fetch_gitee_attach_files(release)
    asset = find_installer_asset(assets, latest_version)
    asset_name = get_asset_name(asset) if asset else installer_name(latest_version)
    download_url = get_asset_download_url(asset) if asset else None
    if not download_url and asset_name:
        download_url = f"{GITEE_REPO_URL}/releases/download/{tag}/{asset_name}"
    return UpdateInfo(
        current_version=local_version,
        latest_version=latest_version,
        has_update=is_newer_version(latest_version, local_version),
        release_url=release_url,
        asset_name=asset_name,
        download_url=download_url,
        asset_size=get_asset_size(asset),
        digest=get_asset_digest(asset),
        published_at=release.get("published_at") or release.get("created_at"),
        body=(release.get("body") or release.get("description") or "").strip(),
        update_source="gitee",
    )


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


def update_info_from_github_release(release: dict, local_version: str) -> UpdateInfo:
    latest_version = normalize_version(release.get("tag_name") or release.get("name") or "")
    asset = find_installer_asset(normalize_release_assets(release), latest_version)
    return UpdateInfo(
        current_version=local_version,
        latest_version=latest_version or local_version,
        has_update=bool(latest_version and is_newer_version(latest_version, local_version)),
        release_url=release.get("html_url") or "",
        asset_name=get_asset_name(asset),
        download_url=get_asset_download_url(asset),
        asset_size=get_asset_size(asset),
        digest=get_asset_digest(asset),
        published_at=release.get("published_at"),
        body=(release.get("body") or "").strip(),
        update_source="github",
    )


def normalize_release_assets(release: dict) -> list[dict]:
    assets = release.get("assets") or release.get("attach_files") or release.get("attachments") or []
    return assets if isinstance(assets, list) else []


def get_asset_name(asset: dict | None) -> str | None:
    if not asset:
        return None
    return asset.get("name") or asset.get("filename") or asset.get("file_name") or asset.get("fileName")


def get_asset_download_url(asset: dict | None) -> str | None:
    if not asset:
        return None
    return (
        asset.get("browser_download_url")
        or asset.get("download_url")
        or asset.get("downloadUrl")
        or asset.get("download_href")
        or asset.get("url")
    )


def get_asset_size(asset: dict | None) -> int | None:
    if not asset:
        return None
    value = asset.get("size") or asset.get("file_size") or asset.get("fileSize")
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def get_asset_digest(asset: dict | None) -> str | None:
    if not asset:
        return None
    value = asset.get("digest") or asset.get("sha256")
    if value and not str(value).startswith("sha256:") and re.fullmatch(r"[a-fA-F0-9]{64}", str(value)):
        return f"sha256:{value}"
    return value


def installer_name(version: str) -> str:
    if sys.platform == "darwin":
        return f"SchoolAdminAIAssistant-macOS-v{normalize_version(version)}.dmg"
    return f"SchoolAdminAIAssistant-Setup-v{normalize_version(version)}.exe"


def find_installer_asset(assets: list[dict], latest_version: str) -> dict | None:
    expected_name = installer_name(latest_version)
    pattern = MACOS_INSTALLER_PATTERN if sys.platform == "darwin" else WINDOWS_INSTALLER_PATTERN
    extension = ".dmg" if sys.platform == "darwin" else ".exe"
    for asset in assets:
        if get_asset_name(asset) == expected_name:
            return asset
    for asset in assets:
        name = get_asset_name(asset) or ""
        if pattern.search(name):
            return asset
    for asset in assets:
        name = get_asset_name(asset) or ""
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
