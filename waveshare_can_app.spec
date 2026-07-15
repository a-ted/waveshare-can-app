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
    [],
    exclude_binaries=True,
    name='WaveshareCANAnalyser',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon='ws_can_app_icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name='WaveshareCANAnalyser',
)

# macOS .app bundle (ignored on Windows)
app = BUNDLE(
    coll,
    name='WaveshareCANAnalyser.app',
    icon='ws_can_app_icon.icns',
    bundle_identifier='com.aaronteo.waveshare-can-analyser',
    info_plist={
        'NSHighResolutionCapable': True,
        'CFBundleShortVersionString': '1.0.0',
    },
)