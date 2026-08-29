# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec для PDF-бот Аганим v3.0 (с учётом бонусов дизайнеров)
a = Analysis(
    ['bot_v30.py'],
    pathex=['C:\\Users\\user\\ZCodeProject'],
    binaries=[],
    datas=[
        ('key.json', '.'),
        (r'C:\Users\user\ZCodeProject\.venv\Lib\site-packages\customtkinter', 'customtkinter'),
        ('dashboard_v30.py', '.'),
        ('deployment.py', '.'),
    ],
    hiddenimports=[
        'pystray._win32', 'watchdog.observers', 'watchdog.events',
        'pdfplumber', 'gspread', 'PIL.Image', 'PIL.ImageDraw',
        'customtkinter', 'darkdetect', 'dashboard_v30', 'tkinter.ttk',
        'requests', 'deployment',
    ],
    hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[],
    noarchive=False, optimize=0,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name='pdf_bot', debug=False, bootloader_ignore_signals=False,
    strip=False, upx=True, upx_exclude=[], runtime_tmpdir=None,
    console=False, disable_windowed_traceback=False, argv_emulation=False,
    target_arch=None, codesign_identity=None, entitlements_file=None,
)
