"""一键启动：拉起本地服务并打开浏览器。"""

from __future__ import annotations

import argparse
import os
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path


def _configure_stdio() -> None:
    """避免 Windows 控制台默认编码无法打印中文而崩溃。"""
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    if sys.platform == "win32":
        try:
            import ctypes

            ctypes.windll.kernel32.SetConsoleOutputCP(65001)
            ctypes.windll.kernel32.SetConsoleCP(65001)
        except Exception:
            pass
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is None:
            continue
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


_configure_stdio()

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import DATA_DIR, HOST, PORT, app_base_dir  # noqa: E402


def say(message: str = "") -> None:
    try:
        print(message)
    except UnicodeEncodeError:
        encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
        print(message.encode(encoding, errors="replace").decode(encoding, errors="replace"))


def _setup_playwright_browsers() -> None:
    bundled = app_base_dir() / "ms-playwright"
    if bundled.is_dir():
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(bundled)


def _port_open(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.4)
        return sock.connect_ex((host, port)) == 0


def _wait_ready(host: str, port: int, timeout_s: float = 30.0) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if _port_open(host, port):
            return True
        time.sleep(0.2)
    return False


def _run_server() -> None:
    import uvicorn

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    # 打包后用 app 对象；开发时字符串导入也可
    if getattr(sys, "frozen", False):
        from app.main import app

        uvicorn.run(app, host=HOST, port=PORT, log_level="info")
    else:
        uvicorn.run("app.main:app", host=HOST, port=PORT, reload=False, log_level="info")


def main() -> int:
    parser = argparse.ArgumentParser(description="ENDLOGS launcher")
    parser.add_argument("--no-browser", action="store_true", help="Do not open browser")
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--port", type=int, default=PORT)
    args = parser.parse_args()

    _setup_playwright_browsers()
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    host = args.host
    port = args.port
    url = f"http://{host}:{port}"

    say("=" * 48)
    say("  ENDLOGS  (Endfield Resource Logs)")
    say("=" * 48)
    say(f"URL: {url}")
    say("Keep this window open. Closing it stops the server.")
    say("")

    already = _port_open(host, port)
    if already:
        say(f"Port {port} is already in use. Opening the page...")
        if not args.no_browser:
            webbrowser.open(url)
        say("If the page looks wrong, close the old Endlogs window and retry.")
        try:
            input("Press Enter to exit this launcher (existing server keeps running)...")
        except EOFError:
            pass
        return 0

    thread = threading.Thread(target=_run_server, daemon=True)
    thread.start()

    if not _wait_ready(host, port):
        say("Startup timeout: server did not become ready.")
        return 1

    say("Server started.")
    if not args.no_browser:
        webbrowser.open(url)
        say("Browser open attempted. If not, visit the URL above.")

    try:
        while thread.is_alive():
            time.sleep(0.5)
    except KeyboardInterrupt:
        say("")
        say("Exiting...")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
