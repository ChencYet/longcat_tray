# -*- mode: python ; coding: utf-8 -*-


import os, sys

_python_dir = os.path.dirname(sys.executable)
_tcl_dir = os.path.join(_python_dir, 'tcl', 'tcl8.6')
_tk_dir = os.path.join(_python_dir, 'tcl', 'tk8.6')

a = Analysis(
    ['tray_app.py'],
    pathex=[],
    binaries=[],
    datas=[
        (_tcl_dir, 'tcl/tcl8.6'),
        (_tk_dir, 'tcl/tk8.6'),
    ],
    hiddenimports=['pystray._win32', 'PIL._tkinter_finder', 'browser_cookie3', 'lz4', 'Cryptodome', 'wmi', 'shadowcopy', 'win32crypt', 'win32con', 'win32api'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='LongCatUsage',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
