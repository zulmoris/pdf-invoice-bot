# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec для Дашборд v3.0 (с вкладкой Дизайнеры)
a = Analysis(
    ['dashboard_v30.py'],
    pathex=['C:\\Users\\user\\ZCodeProject'],
    binaries=[],
    datas=[
        ('key.json', '.'),
        (r'C:\Users\user\ZCodeProject\.venv\Lib\site-packages\customtkinter', 'customtkinter'),
    ],
    hiddenimports=[
        'gspread', 'customtkinter', 'darkdetect', 'openpyxl', 'tkinter.ttk',
    ],
    hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[],
    noarchive=False, optimize=0,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name='dashboard', debug=False, bootloader_ignore_signals=False,
    strip=False, upx=True, upx_exclude=[], runtime_tmpdir=None,
    console=False, disable_windowed_traceback=False, argv_emulation=False,
    target_arch=None, codesign_identity=None, entitlements_file=None,
)
