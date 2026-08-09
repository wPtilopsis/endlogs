# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec：生成 Endlogs.exe 一键启动包。"""

from pathlib import Path

block_cipher = None
root = Path(SPECPATH)

a = Analysis(
    ["launcher.py"],
    pathex=[str(root)],
    binaries=[],
    datas=[
        (str(root / "web"), "web"),
        (str(root / "change_reasons.json"), "."),
    ],
    hiddenimports=[
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.auto",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        "app.main",
        "auth",
        "auth.browser_login",
        "auth.tokens",
        "auth.profile",
        "client",
        "client.currency",
        "client.binding",
        "stats",
        "stats.aggregate",
        "playwright",
        "playwright.sync_api",
        "playwright.async_api",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Endlogs",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Endlogs",
)