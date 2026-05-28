# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules


PROJECT_ROOT = Path(SPECPATH).parent


hiddenimports = []
for package in [
    "uvicorn",
    "fastapi",
    "starlette",
    "pydantic",
    "pydantic_settings",
    "openai",
    "httpx",
    "docx",
    "pptx",
    "pypdf",
    "openpyxl",
    "xlrd",
    "olefile",
]:
    hiddenimports += collect_submodules(package)

# sqlalchemy — only keep the sqlite dialect, drop mysql/pg/oracle/mssql
_hidden_sqlalchemy = collect_submodules("sqlalchemy")
hiddenimports += [
    m for m in _hidden_sqlalchemy
    if not m.startswith("sqlalchemy.dialects.") or "sqlite" in m
]

# pythonnet / clr_loader — targeted imports for WinForms WebView2, not full collect
hiddenimports += [
    "clr",
    "clr_loader",
    "pythonnet",
    "pythonnet.runtime",
]

hiddenimports += [
    "webview",
    "webview.dom",
    "webview.guilib",
    "webview.platforms.edgechromium",
    "webview.platforms.winforms",
]

datas = [
    (str(PROJECT_ROOT / "backend" / "app" / "prompts"), "app/prompts"),
    (str(PROJECT_ROOT / "backend" / "app" / "static"), "app/static"),
    (str(PROJECT_ROOT / "assets"), "assets"),
    (str(PROJECT_ROOT / "VERSION"), "."),
    (str(PROJECT_ROOT / "DEVELOPER"), "."),
    (str(PROJECT_ROOT / "CHANGELOG.md"), "."),
    (str(PROJECT_ROOT / "version-policy.json"), "."),
]

a = Analysis(
    [str(PROJECT_ROOT / "backend" / "desktop_launcher.py")],
    pathex=[str(PROJECT_ROOT / "backend")],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "cefpython3",
        "gi",
        "kivy",
        "pygame",
        "PyQt5",
        "PyQt6",
        "PySide2",
        "PySide6",
        "webview.platforms.android",
        "webview.platforms.cef",
        "webview.platforms.cocoa",
        "webview.platforms.gtk",
        "webview.platforms.mshtml",
        "webview.platforms.qt",
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="SchoolAdminAIAssistant",
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=True,
    console=False,
    icon=str(PROJECT_ROOT / "assets" / "app-icon.ico"),
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=True,
    upx=True,
    upx_exclude=[],
    name="SchoolAdminAIAssistant",
)
