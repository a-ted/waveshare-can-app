# waveshare_can.spec
import sys
from PyInstaller.building.build_main import Analysis, PYZ, EXE, BUNDLE, COLLECT

block_cipher = None

a = Analysis(
    ['waveshare_can_app.py'],
    pathex=['.'],
    binaries=[],
    hiddenimports=[
        'serial.tools.list_ports',
        'serial.tools.list_ports_posix',   # macOS/Linux
        'serial.tools.list_ports_windows', # Windows
        'can.interfaces',
        'can.interfaces.serial',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='waveshare_can_app',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
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
    upx=True,
    upx_exclude=[],
    name='waveshare_can_app',
)

# macOS .app bundle (ignored on Windows)
app = BUNDLE(
    coll,
    name='WaveshareCANAnalyzer.app',
    icon='ws_can_app_icon.icns',
    bundle_identifier='com.aaronteo.waveshare-can-analyzer',
    info_plist={
        'NSHighResolutionCapable': True,
        'CFBundleShortVersionString': '1.0.0',
    },
)