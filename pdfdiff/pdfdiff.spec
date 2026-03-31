# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for pdfdiff sidecar binary.

Build:
    cd pdfdiff && pyinstaller pdfdiff.spec

Output:
    dist/pdfdiff  (single-file executable)
"""

import sys
from pathlib import Path

block_cipher = None

a = Analysis(
    ['__main__.py'],
    pathex=[str(Path('.').resolve())],
    binaries=[],
    datas=[],
    hiddenimports=[
        'pdfdiff.cli',
        'pdfdiff.models',
        'pdfdiff.extractor',
        'pdfdiff.differ',
        'pdfdiff.analyzer',
        'pdfdiff.annotator',
        'pdfdiff.detector',
        'pdfdiff.visual_differ',
        'typer',
        'click',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'PIL',
        'numpy',
        'scipy',
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='pdfdiff',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
