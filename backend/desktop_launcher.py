import os
import secrets
import socket
import sys
import threading
import time
import traceback
import urllib.request
from urllib.parse import quote
from pathlib import Path

import uvicorn
import webview


def app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def resource_roots(root: Path) -> list[Path]:
    roots = [root]
    pyinstaller_root = getattr(sys, "_MEIPASS", None)
    if pyinstaller_root:
        roots.append(Path(pyinstaller_root))
    return roots


def sqlite_url(path: Path) -> str:
    return f"sqlite:///{path.as_posix()}"


def find_free_port(start: int = 8765, attempts: int = 30) -> int:
    for port in range(start, start + attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(("0.0.0.0", port))
            except OSError:
                continue
            return port
    raise RuntimeError("No free local port available.")


def configure_runtime(root: Path, port: int) -> None:
    data_dir = data_root(root)
    upload_dir = data_dir / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    access_key = student_access_key(data_dir)
    student_url = f"http://{local_network_ip()}:{port}/student-chat?access_key={quote(access_key)}"

    for path in [root / "backend", *resource_roots(root)]:
        if path.exists() and str(path) not in sys.path:
            sys.path.insert(0, str(path))

    os.environ["DATABASE_URL"] = sqlite_url(data_dir / "app.db")
    os.environ["UPLOAD_DIR"] = str(upload_dir)
    os.environ["CORS_ORIGINS"] = f"http://127.0.0.1:{port},http://localhost:{port},{student_url.rsplit('/student-chat', 1)[0]}"
    os.environ["STUDENT_ACCESS_KEY"] = access_key
    os.environ["STUDENT_CHAT_URL"] = student_url
    os.chdir(root)


def data_root(root: Path) -> Path:
    if getattr(sys, "frozen", False) and sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "SchoolAdminAIAssistant" / "data"
    return root / "data"


def student_access_key(data_dir: Path) -> str:
    path = data_dir / "student_access_key.txt"
    if path.exists():
        value = path.read_text(encoding="utf-8").strip()
        if value:
            return value
    value = secrets.token_urlsafe(16)
    path.write_text(value, encoding="utf-8")
    return value


def local_network_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            ip = sock.getsockname()[0]
            if ip and not ip.startswith("127."):
                return ip
    except Exception:
        pass
    try:
        ip = socket.gethostbyname(socket.gethostname())
        if ip and not ip.startswith("127."):
            return ip
    except Exception:
        pass
    return "127.0.0.1"


def log_path(root: Path) -> Path:
    path = root / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path / "startup.log"


def write_log(root: Path, message: str) -> None:
    try:
        with log_path(root).open("a", encoding="utf-8") as file:
            file.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")
    except Exception:
        pass


def wait_for_server(port: int, timeout_seconds: float = 20) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=0.5) as response:
                if response.status == 200:
                    return True
        except Exception:
            time.sleep(0.2)
    return False


def run_server(root: Path, port: int) -> None:
    try:
        write_log(root, f"Starting local API on 0.0.0.0:{port}")
        from app.main import app as fastapi_app

        config = uvicorn.Config(
            fastapi_app,
            host="0.0.0.0",
            port=port,
            log_level="warning",
            loop="asyncio",
            access_log=False,
        )
        server = uvicorn.Server(config)
        server.run()
    except Exception:
        write_log(root, "Server failed to start:")
        write_log(root, traceback.format_exc())


def icon_path(root: Path) -> str | None:
    for candidate_root in resource_roots(root):
        icon_name = "app-icon.png" if sys.platform == "darwin" else "app-icon.ico"
        icon = candidate_root / "assets" / icon_name
        if icon.exists():
            return str(icon)
    return None


def html_escape(value: str) -> str:
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def startup_error_html(root: Path, port: int) -> str:
    escaped_log_path = html_escape(str(log_path(root)))
    return f"""
    <!doctype html>
    <html lang="zh-CN">
      <head>
        <meta charset="utf-8" />
        <style>
          body {{ font-family: "Microsoft YaHei", system-ui, sans-serif; background: #f8fafc; color: #172033; padding: 48px; }}
          .panel {{ max-width: 760px; margin: 80px auto; background: #fff; border: 1px solid #dbe3ef; border-radius: 10px; padding: 28px; box-shadow: 0 8px 24px rgba(15, 23, 42, .08); }}
          h1 {{ margin: 0 0 12px; font-size: 24px; }}
          p {{ line-height: 1.7; }}
          code {{ background: #f1f5f9; padding: 2px 6px; border-radius: 4px; }}
        </style>
      </head>
      <body>
        <div class="panel">
          <h1>本地服务启动失败</h1>
          <p>桌面窗口已打开，但后台服务没有在 <code>127.0.0.1:{port}</code> 成功启动。</p>
          <p>请查看启动日志：<code>{escaped_log_path}</code></p>
          <p>如果刚安装完成，请关闭本窗口后重新启动；如果仍失败，把日志内容发给开发者排查。</p>
        </div>
      </body>
    </html>
    """


def open_desktop_window(root: Path, port: int, server_ready: bool) -> None:
    if server_ready:
        webview.create_window(
            "高校行政 AI 回复助手",
            f"http://127.0.0.1:{port}?desktop_build={int(time.time())}",
            width=1280,
            height=820,
            min_size=(1100, 720),
            confirm_close=False,
        )
    else:
        webview.create_window(
            "高校行政 AI 回复助手",
            html=startup_error_html(root, port),
            width=900,
            height=620,
            min_size=(760, 520),
            confirm_close=False,
        )


def main() -> None:
    root = app_dir()
    port = find_free_port()
    configure_runtime(root, port)
    write_log(root, f"Application root: {root}")
    write_log(root, f"Resource roots: {', '.join(str(item) for item in resource_roots(root))}")

    server_thread = threading.Thread(target=run_server, args=(root, port), daemon=True)
    server_thread.start()
    server_ready = wait_for_server(port)
    write_log(root, f"Server ready: {server_ready}")

    open_desktop_window(root, port, server_ready)
    if sys.platform == "win32":
        webview.start(gui="edgechromium", debug=False, icon=icon_path(root))
    else:
        webview.start(debug=False, icon=icon_path(root))


if __name__ == "__main__":
    main()
