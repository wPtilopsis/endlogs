# 构建 Windows 发布包
# 用法（在项目根目录）:
#   powershell -ExecutionPolicy Bypass -File scripts\build_windows.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "==> 使用虚拟环境" -ForegroundColor Cyan
if (-not (Test-Path ".venv\Scripts\python.exe")) {
  python -m venv .venv
}
& .\.venv\Scripts\Activate.ps1

Write-Host "==> 安装依赖与打包工具" -ForegroundColor Cyan
python -m pip install -q --upgrade pip
python -m pip install -q -r requirements.txt
python -m pip install -q -r requirements-build.txt
python -m playwright install chromium

Write-Host "==> PyInstaller 打包" -ForegroundColor Cyan
Remove-Item -Recurse -Force dist\Endlogs, build -ErrorAction SilentlyContinue
python -m PyInstaller --noconfirm --clean endlogs.spec

$Out = Join-Path $Root "dist\Endlogs"
if (-not (Test-Path (Join-Path $Out "Endlogs.exe"))) {
  throw "打包失败：未找到 Endlogs.exe"
}

Write-Host "==> 写入小白说明" -ForegroundColor Cyan
Copy-Item -Force "USER_GUIDE.txt" (Join-Path $Out "使用说明.txt")
Copy-Item -Force "LICENSE" (Join-Path $Out "LICENSE.txt") -ErrorAction SilentlyContinue

Write-Host "==> 复制 Playwright Chromium（体积较大，便于离线登录）" -ForegroundColor Cyan
$BrowserSrc = Join-Path $env:LOCALAPPDATA "ms-playwright"
$BrowserDst = Join-Path $Out "ms-playwright"
if (Test-Path $BrowserSrc) {
  if (Test-Path $BrowserDst) { Remove-Item -Recurse -Force $BrowserDst }
  Copy-Item -Recurse -Force $BrowserSrc $BrowserDst
  @"
@echo off
set PLAYWRIGHT_BROWSERS_PATH=%~dp0ms-playwright
start "" "%~dp0Endlogs.exe"
"@ | Set-Content -Encoding ASCII (Join-Path $Out "一键启动.bat")
} else {
  Write-Host "未找到本机 Playwright 浏览器缓存，发布包需用户首次自行安装。" -ForegroundColor Yellow
  @"
@echo off
start "" "%~dp0Endlogs.exe"
"@ | Set-Content -Encoding ASCII (Join-Path $Out "一键启动.bat")
}

Write-Host ""
Write-Host "完成：$Out" -ForegroundColor Green
Write-Host "可将 dist\Endlogs 文件夹打成 zip，上传到 GitHub Release。" -ForegroundColor Green
