from pathlib import Path


def project_roots() -> list[Path]:
    current = Path(__file__).resolve()
    return [
        current.parents[3],
        current.parents[2],
        current.parents[1],
        current.parent,
    ]


def read_first_existing(filename: str, default: str = "") -> str:
    for root in project_roots():
        path = root / filename
        if path.exists():
            return path.read_text(encoding="utf-8").strip()
    return default


def latest_changelog_section(changelog: str) -> str:
    lines = changelog.splitlines()
    sections: list[list[str]] = []
    current: list[str] = []
    for line in lines:
        if line.startswith("## "):
            if current:
                sections.append(current)
            current = [line]
        elif current:
            current.append(line)
    if current:
        sections.append(current)
    return "\n".join(sections[0]).strip() if sections else changelog.strip()


def get_app_info() -> dict:
    changelog = read_first_existing("CHANGELOG.md", "暂无更新信息。")
    return {
        "name": "高校行政 AI 回复助手",
        "version": read_first_existing("VERSION", "0.0.0"),
        "developer": read_first_existing("DEVELOPER", "Unknown"),
        "latest_update": latest_changelog_section(changelog),
    }
