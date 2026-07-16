# Build Windows release package
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts\build_windows.ps1

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
python -m playwright install chromium

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

Write-Host "==> Bundle Playwright browsers if available" -ForegroundColor Cyan
if (Test-Path $BrowserSrc) {
  if (Test-Path $BrowserDst) {
    Remove-Item -Recurse -Force $BrowserDst
  }
  Copy-Item -Recurse -Force $BrowserSrc $BrowserDst
  @(
    "@echo off"
    "set PLAYWRIGHT_BROWSERS_PATH=%~dp0ms-playwright"
    "start `"`" `"%~dp0Endlogs.exe`""
  ) | Set-Content -Encoding ASCII $StartBat
} else {
  Write-Host "Playwright cache not found; package will not include browsers." -ForegroundColor Yellow
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
Write-Host "Zip dist\Endlogs and upload to GitHub Release." -ForegroundColor Green
