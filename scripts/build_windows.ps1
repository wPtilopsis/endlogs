# Build Windows release package
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts\build_windows.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\build_windows.ps1 -BundleBrowser
#
# 默认不附带 Playwright Chromium（约省 400MB+），登录优先使用本机 Edge/Chrome。
# 需要离线自带浏览器时再加 -BundleBrowser。

param(
  [switch]$BundleBrowser
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "==> Using venv" -ForegroundColor Cyan
if (-not (Test-Path ".venv\Scripts\python.exe")) {
  python -m venv .venv
}
& .\.venv\Scripts\Activate.ps1

Write-Host "==> Install deps and build tools" -ForegroundColor Cyan
python -m pip install -q --upgrade pip
python -m pip install -q -r requirements.txt
python -m pip install -q -r requirements-build.txt

if ($BundleBrowser) {
  Write-Host "==> Install Playwright Chromium (no headless shell)" -ForegroundColor Cyan
  python -m playwright install chromium --no-shell
}

Write-Host "==> PyInstaller" -ForegroundColor Cyan
Remove-Item -Recurse -Force dist\Endlogs, build -ErrorAction SilentlyContinue
python -m PyInstaller --noconfirm --clean endlogs.spec

$Out = Join-Path $Root "dist\Endlogs"
$Exe = Join-Path $Out "Endlogs.exe"
if (-not (Test-Path $Exe)) {
  throw "Build failed: Endlogs.exe not found"
}

Write-Host "==> Copy docs" -ForegroundColor Cyan
Copy-Item -Force "USER_GUIDE.txt" (Join-Path $Out "USER_GUIDE.txt")
if (Test-Path "LICENSE") {
  Copy-Item -Force "LICENSE" (Join-Path $Out "LICENSE.txt")
}

$StartBat = Join-Path $Out "start.bat"
$BrowserSrc = Join-Path $env:LOCALAPPDATA "ms-playwright"
$BrowserDst = Join-Path $Out "ms-playwright"

if ($BundleBrowser) {
  Write-Host "==> Bundle Chromium only (exclude headless_shell / ffmpeg)" -ForegroundColor Cyan
  if (-not (Test-Path $BrowserSrc)) {
    throw "Playwright cache not found at $BrowserSrc"
  }
  if (Test-Path $BrowserDst) {
    Remove-Item -Recurse -Force $BrowserDst
  }
  New-Item -ItemType Directory -Path $BrowserDst | Out-Null
  Get-ChildItem $BrowserSrc -Directory | Where-Object {
    $_.Name -like "chromium-*" -and $_.Name -notlike "chromium_headless*"
  } | ForEach-Object {
    Copy-Item -Recurse -Force $_.FullName (Join-Path $BrowserDst $_.Name)
  }
  @(
    "@echo off"
    "set PLAYWRIGHT_BROWSERS_PATH=%~dp0ms-playwright"
    "start `"`" `"%~dp0Endlogs.exe`""
  ) | Set-Content -Encoding ASCII $StartBat
} else {
  Write-Host "==> Slim package (no bundled browser; uses system Edge/Chrome)" -ForegroundColor Cyan
  @(
    "@echo off"
    "start `"`" `"%~dp0Endlogs.exe`""
  ) | Set-Content -Encoding ASCII $StartBat
}

# Also provide a Chinese-named launcher copy for end users
$ZhBat = Join-Path $Out ([string]::Concat([char]0x4E00, [char]0x952E, [char]0x542F, [char]0x52A8, ".bat"))
Copy-Item -Force $StartBat $ZhBat

Write-Host ""
Write-Host ("Done: " + $Out) -ForegroundColor Green
if ($BundleBrowser) {
  Write-Host "Bundled Chromium included. Zip dist\Endlogs for Release." -ForegroundColor Green
} else {
  Write-Host "Slim build (no browser). Zip dist\Endlogs for Release." -ForegroundColor Green
  Write-Host "Tip: add -BundleBrowser if users may lack Edge/Chrome." -ForegroundColor Yellow
}
