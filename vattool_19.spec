# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules
from pathlib import Path

project_dir = Path(__file__).resolve().parent
configs_dir = project_dir / "configs"
guide_file = project_dir / "USER_GUIDE.txt"

hiddenimports = collect_submodules("core")

a = Analysis(
    ["ui.py"],
    pathex=[str(project_dir)],
    binaries=[],
    datas=[
        (str(configs_dir), "configs"),
        (str(guide_file), "."),
    ] if guide_file.exists() else [
        (str(configs_dir), "configs"),
    ],
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
    name="VATTool_19",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,   # GUI app
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    name="VATTool_19",
)
