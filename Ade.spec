# -*- mode: python ; coding: utf-8 -*-


block_cipher = None


a = Analysis(
    ['Ade.py'],
    pathex=[],
    binaries=[],
    datas=[('static', 'static')],
    hiddenimports=['win32timezone'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='AdePrint',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    windowed=True,
    icon='static/icon.icns',
)

app = BUNDLE(
    exe,
    name='AdePrint.app',
    icon='static/icon.icns',
    bundle_identifier='com.integrate.AdePrint',
    info_plist={
        'LSUIElement': 'True',
        'CFBundleURLTypes': [
            {
                'CFBundleURLName': 'adeprint',
                'CFBundleURLSchemes': ['adeprint']
            }
        ]
    },
)