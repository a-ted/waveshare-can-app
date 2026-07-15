import sys

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

if sys.platform == 'win32':
    # Windows: single-file exe
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        name='WaveshareCANAnalyzer',
        debug=False,
        strip=False,
        upx=False,
        console=False,
        icon='ws_can_app_icon.ico',
    )
else:
    # macOS: multi-file collected into a .app bundle
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name='WaveshareCANAnalyzer',
        debug=False,
        strip=False,
        upx=False,
        console=False,
        icon='ws_can_app_icon.icns',
    )

    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=False,
        name='WaveshareCANAnalyzer',
    )

    app = BUNDLE(
        coll,
        name='WaveshareCANAnalyzer.app',
        icon='ws_can_app_icon.icns',
        bundle_identifier='com.yourname.waveshare-can-analyzer',
        info_plist={
            'NSHighResolutionCapable': True,
            'CFBundleShortVersionString': '1.0.0',
        },
    )