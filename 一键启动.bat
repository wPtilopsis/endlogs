@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ================================================
echo   终末地资源日志助手 - 一键启动
echo ================================================
echo.

where python >nul 2>nul
if errorlevel 1 (
  echo [错误] 未找到 Python。请先安装 Python 3.11+ 并勾选 Add to PATH。
  echo 下载: https://www.python.org/downloads/
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo [首次运行] 正在创建虚拟环境…
  python -m venv .venv
  if errorlevel 1 (
    echo [错误] 创建虚拟环境失败。
    pause
    exit /b 1
  )
)

call ".venv\Scripts\Activate.bat"

echo [检查] 安装依赖…
python -m pip install -q --upgrade pip
python -m pip install -q -r requirements.txt
if errorlevel 1 (
  echo [错误] 依赖安装失败，请检查网络后重试。
  pause
  exit /b 1
)

echo [检查] Playwright Chromium（首次可能较久）…
python -m playwright install chromium
if errorlevel 1 (
  echo [警告] Chromium 安装失败，浏览器登录可能不可用；仍可尝试手动粘贴 token。
)

echo.
echo 正在启动…
python launcher.py
echo.
pause
