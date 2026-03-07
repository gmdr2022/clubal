# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules


PROJECT_ROOT = Path(SPECPATH).resolve()
APP_NAME = "CLUBAL"

datas = []

graphics_dir = PROJECT_ROOT / "graphics"
if graphics_dir.exists() and graphics_dir.is_dir():
    datas.append((str(graphics_dir), "graphics"))

grade_template = PROJECT_ROOT / "grade_template.xlsx"
if grade_template.exists() and grade_template.is_file():
    datas.append((str(grade_template), "."))

hiddenimports = [
    "truststore",
    "certifi",
    "weather_service",
]

hiddenimports += collect_submodules("weather")

a = Analysis(
    ["clubal.py"],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
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
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=APP_NAME,
)