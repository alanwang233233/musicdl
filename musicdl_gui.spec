# musicdl_gui.spec
# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['src/musicdl_gui/main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'musicdl',
        'musicdl_gui',
        'flet',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

# Filter out problematic Flet binaries (Flet.app with nested frameworks)
a.binaries = [b for b in a.binaries if 'flet_desktop/app/Flet.app' not in b[0]]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='musicdl-gui',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[
        'Flet',
        'libswift_Concurrency.dylib',
        'Swresample.framework',
        'FlutterMacOS.framework',
    ],
    name='musicdl_gui',
)

app = BUNDLE(
    coll,
    name='musicdl-gui.app',
    icon='assets/icon.png',
    bundle_identifier='com.musicdl.gui',
    info_plist={
        'NSHighResolutionCapable': True,
        'CFBundleShortVersionString': '0.1.0',
        'CFBundleVersion': '0.1.0',
        'NSRequiresAquaSystemAppearance': False,
    },
    codesign_identity=None,
    entitlements_file=None,
)