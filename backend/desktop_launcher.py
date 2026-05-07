import os
import socket
import sys
import threading
import webbrowser
from pathlib import Path

import uvicorn


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


def open_browser(port: int) -> None:
    webbrowser.open(f"http://127.0.0.1:{port}")


def main() -> None:
    root = app_dir()
    configure_runtime(root)
    port = find_free_port()
    threading.Timer(1.2, open_browser, args=(port,)).start()
    uvicorn.run("app.main:app", host="127.0.0.1", port=port, log_level="warning")


if __name__ == "__main__":
    main()
