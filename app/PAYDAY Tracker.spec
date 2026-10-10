# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = ['webview.platforms.edgechromium', 'webview.platforms.winforms', 'clr']
hiddenimports += collect_submodules('webview')


a = Analysis(
    ['tracker_app.py'],
    pathex=[],
    binaries=[],
    datas=[('ui.html', '.'), ('data', 'data')],
    hiddenimports=hiddenimports,
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
    name='PAYDAY Tracker',
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
    icon=['D:/MOEEE/LLM/ZCode/.zcode/workspace/Мои чаты/payday/app/app.ico'],
)
