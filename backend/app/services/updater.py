import hashlib
import os
import re
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path

import httpx

from .app_info import read_first_existing


GITHUB_REPO_URL = "https://github.com/quiwe/school-admin-ai-assistant"
GITHUB_LATEST_RELEASE_API_URL = "https://api.github.com/repos/quiwe/school-admin-ai-assistant/releases/latest"
GITHUB_LATEST_RELEASE_PAGE_URL = f"{GITHUB_REPO_URL}/releases/latest"
VERSION_POLICY_URL = "https://raw.githubusercontent.com/quiwe/school-admin-ai-assistant/main/version-policy.json"
INSTALLER_PATTERN = re.compile(r"SchoolAdminAIAssistant-Setup-v?[\d.]+\.exe$", re.IGNORECASE)


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
    return f"SchoolAdminAIAssistant-Setup-v{normalize_version(version)}.exe"


def find_installer_asset(assets: list[dict], latest_version: str) -> dict | None:
    expected_name = installer_name(latest_version)
    for asset in assets:
        if asset.get("name") == expected_name:
            return asset
    for asset in assets:
        name = asset.get("name") or ""
        if INSTALLER_PATTERN.search(name):
            return asset
    for asset in assets:
        name = asset.get("name") or ""
        if name.lower().endswith(".exe"):
            return asset
    return None


def download_installer(info: UpdateInfo) -> Path:
    if not info.download_url or not info.asset_name:
        raise UpdateError("最新 Release 中没有找到 Windows 安装包。")

    target = updates_dir() / info.asset_name
    temp_target = target.with_suffix(target.suffix + ".download")

    try:
        with httpx.Client(timeout=None, follow_redirects=True) as client:
            with client.stream("GET", info.download_url, headers={"User-Agent": "SchoolAdminAIAssistant"}) as response:
                response.raise_for_status()
                with temp_target.open("wb") as file:
                    for chunk in response.iter_bytes():
                        if chunk:
                            file.write(chunk)
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


def launch_installer(installer: Path) -> None:
    try:
        subprocess.Popen([str(installer)], cwd=str(installer.parent), close_fds=True)
    except Exception as exc:
        raise UpdateError(f"启动安装程序失败：{exc}") from exc

    if getattr(sys, "frozen", False):
        threading.Thread(target=exit_soon, daemon=True).start()


def exit_soon() -> None:
    time.sleep(1.5)
    os._exit(0)
