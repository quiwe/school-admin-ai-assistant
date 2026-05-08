import os
import socket
import sys
import threading
import time
from pathlib import Path

import uvicorn
import webview


def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def sqlite_url(path: Path) -> str:
    return f"sqlite:///{path.as_posix()}"


def find_free_port(start: int = 8765, attempts: int = 30) -> int:
    for port in range(start, start + attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("127.0.0.1", port))
            except OSError:
                continue
            return port
    raise RuntimeError("No free local port available.")


def configure_runtime(root: Path) -> None:
    data_dir = root / "data"
    upload_dir = data_dir / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    os.environ.setdefault("DATABASE_URL", sqlite_url(data_dir / "app.db"))
    os.environ.setdefault("UPLOAD_DIR", str(upload_dir))
    os.environ.setdefault("CORS_ORIGINS", "http://127.0.0.1:8765,http://localhost:8765")
    os.chdir(root)


def wait_for_server(port: int, timeout_seconds: float = 12) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.25)
            if sock.connect_ex(("127.0.0.1", port)) == 0:
                return True
        time.sleep(0.2)
    return False


def run_server(port: int) -> None:
    uvicorn.run("app.main:app", host="127.0.0.1", port=port, log_level="warning")


def main() -> None:
    root = app_dir()
    configure_runtime(root)
    port = find_free_port()
    server_thread = threading.Thread(target=run_server, args=(port,), daemon=True)
    server_thread.start()
    wait_for_server(port)

    webview.create_window(
        "高校行政 AI 回复助手",
        f"http://127.0.0.1:{port}",
        width=1280,
        height=820,
        min_size=(1100, 720),
        confirm_close=False,
    )
    webview.start(gui="edgechromium", debug=False)


if __name__ == "__main__":
    main()
