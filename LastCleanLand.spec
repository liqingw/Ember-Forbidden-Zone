# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['C:/Users/ASUS/WorkBuddy/2026-09-23-20-23-24/src/main.py'],
    pathex=['C:/Users/ASUS/WorkBuddy/2026-09-23-20-23-24/src'],
    binaries=[],
    datas=[('assets', 'assets')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['numpy', 'scipy', 'matplotlib', 'PIL', 'Pillow', 'tkinter', 'unittest', 'pydoc', 'fontTools', 'pandas', 'setuptools'],
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
    name='LastCleanLand',
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
    icon=['C:/Users/ASUS/WorkBuddy/2026-09-23-20-23-24/assets/icon.ico'],
)
