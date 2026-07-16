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

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import DATA_DIR, HOST, PORT, app_base_dir  # noqa: E402


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
    parser = argparse.ArgumentParser(description="终末地资源日志助手启动器")
    parser.add_argument("--no-browser", action="store_true", help="不自动打开浏览器")
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--port", type=int, default=PORT)
    args = parser.parse_args()

    _setup_playwright_browsers()
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    host = args.host
    port = args.port
    url = f"http://{host}:{port}"

    print("=" * 48)
    print("  终末地资源日志助手  ENDLOGS")
    print("=" * 48)
    print(f"本地地址: {url}")
    print("请保持本窗口开启；关闭窗口即停止服务。")
    print()

    already = _port_open(host, port)
    if already:
        print(f"检测到 {port} 端口已有服务在运行，直接打开页面。")
        if not args.no_browser:
            webbrowser.open(url)
        print("若页面异常，请先关闭旧进程后重新启动。")
        input("按回车键退出本启动器（不会关闭已有服务）...")
        return 0

    thread = threading.Thread(target=_run_server, daemon=True)
    thread.start()

    if not _wait_ready(host, port):
        print("启动超时：服务未能在限定时间内就绪。")
        return 1

    print("服务已启动。")
    if not args.no_browser:
        webbrowser.open(url)
        print("已尝试打开浏览器。若未打开，请手动访问上面的地址。")

    try:
        while thread.is_alive():
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n正在退出…")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
