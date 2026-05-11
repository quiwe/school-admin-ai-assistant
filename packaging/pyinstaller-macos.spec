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
    "sqlalchemy",
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

hiddenimports += [
    "webview",
    "webview.dom",
    "webview.guilib",
    "webview.platforms.cocoa",
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
        "webview.platforms.gtk",
        "webview.platforms.mshtml",
        "webview.platforms.qt",
        "webview.platforms.winforms",
        "webview.platforms.edgechromium",
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
    strip=False,
    upx=False,
    console=False,
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
    strip=False,
    upx=False,
    upx_exclude=[],
    name="SchoolAdminAIAssistant",
)

app = BUNDLE(
    coll,
    name="高校行政AI回复助手.app",
    icon=str(PROJECT_ROOT / "packaging" / "app-icon.icns"),
    bundle_identifier="com.quiwe.school-admin-ai-assistant",
    info_plist={
        "CFBundleDisplayName": "高校行政AI回复助手",
        "CFBundleName": "高校行政AI回复助手",
        "NSHighResolutionCapable": "True",
    },
)
