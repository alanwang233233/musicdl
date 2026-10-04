# musicdl_cli.spec — CLI 单文件可执行 (PyInstaller)
# 构建: pyinstaller musicdl_cli.spec --noconfirm --clean
# 产物: dist/musicdl-cli(.exe)
# 注意: PyInstaller 不支持交叉编译, 须在目标系统上构建。
# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['src/musicdl_cli/main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # CLI 只依赖核心库, 排除 GUI 相关包以减小体积
    excludes=['flet', 'flet_audio', 'musicdl_gui'],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='musicdl-cli',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
