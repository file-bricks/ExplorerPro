# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

project_root = Path.cwd()
src_dir = project_root / 'src'
icon_file = project_root / 'ExplorerPro.ico'

a = Analysis(
    [str(src_dir / 'main.py')],
    # project_root: translator.py liegt neben src/ (gui/batch_rename_dialog, diff_dialog, settings_dialog)
    pathex=[str(src_dir), str(project_root)],
    binaries=[],
    datas=[
        (str(icon_file), '.'),
        (str(project_root / 'assets'), 'assets'),
        (str(project_root / 'locales'), 'locales'),
        (str(project_root / 'LICENSE'), '.'),
        (str(project_root / 'THIRD_PARTY_LICENSES.txt'), '.'),
        (str(project_root / 'PRIVACY_POLICY.md'), '.'),
        (str(project_root / 'SUPPORT.md'), '.'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'IPython',
        'black',
        'blib2to3',
        'cv2',
        'matplotlib',
        'notebook',
        'pytest',
        'scipy',
        'sklearn',
        'torch',
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ExplorerPro',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=[str(icon_file)],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='ExplorerPro',
)
