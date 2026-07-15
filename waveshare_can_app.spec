# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['waveshare_can_app.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
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
    name='WaveshareCANAnalyser',
    icon='ws_can_app_icon.ico',
    console=False,
)
app = BUNDLE(
    exe,
    name='WaveshareCANAnalyser.app',
    icon='ws_can_app_icon.icns',
)