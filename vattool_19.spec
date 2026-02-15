# -*- mode: python ; coding: utf-8 -*-

import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

project_dir = Path(os.getcwd())
configs_dir = project_dir / "configs"
guide_file = project_dir / "USER_GUIDE.txt"
commit_file = project_dir / "BUILD_COMMIT.txt"

hiddenimports = collect_submodules("core")

datas = [
    (str(configs_dir), "configs"),
]

if guide_file.exists():
    datas.append((str(guide_file), "."))

if commit_file.exists():
    datas.append((str(commit_file), "."))

a = Analysis(
    ["ui.py"],
    pathex=[str(project_dir)],
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
    name="VATTool_19",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    name="VATTool_19",
)
