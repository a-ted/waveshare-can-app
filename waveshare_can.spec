# waveshare_can.spec
import sys
from PyInstaller.building.build_main import Analysis, PYZ, EXE, BUNDLE, COLLECT

block_cipher = None

a = Analysis(
    ['waveshare_can_app.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('waveshare_can_bus.py', '.'),
    ],
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
    a.binaries,       # fold in — was previously in COLLECT
    a.zipfiles,       # fold in
    a.datas,          # fold in
    name='WaveshareCANAnalyzer',
    debug=False,
    strip=False,
    upx=False,
    console=False,
    icon='ws_can_app_icon.ico',
)

# Remove the COLLECT() block entirely
# Keep the BUNDLE() block for macOS — it wraps the single-file exe into a .app
app = BUNDLE(
    exe,              # pass exe directly, not coll
    name='WaveshareCANAnalyzer.app',
    icon='ws_can_app_icon.icns',
    bundle_identifier='com.yourname.waveshare-can-analyzer',
    info_plist={
        'NSHighResolutionCapable': True,
        'CFBundleShortVersionString': '1.0.0',
    },
)