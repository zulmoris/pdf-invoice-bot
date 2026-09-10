# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec — Дашборд PDF-бот Аганим v3.5
# Вкус сборки: PDFBOT_FLAVOR=release (по умолчанию) | dev (см. bot_v30.spec).
import os
import json

_flavor = os.environ.get('PDFBOT_FLAVOR', 'release').lower()
if _flavor not in ('release', 'dev'):
    _flavor = 'release'

_stage = os.path.abspath(os.path.join('build', '_spec_stage_dash'))
os.makedirs(_stage, exist_ok=True)
with open(os.path.join(_stage, '_build_flavor.json'), 'w', encoding='utf-8') as f:
    json.dump({'flavor': _flavor}, f)

datas = [
    (os.path.join(_stage, '_build_flavor.json'), '.'),
]
if _flavor == 'dev' and os.path.exists('key.json'):
    datas.append(('key.json', '.'))

a = Analysis(
    ['dashboard_v30.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'gspread', 'customtkinter', 'darkdetect', 'tkinter.ttk',
    ],
    hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[],
    noarchive=False, optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name='dashboard', debug=False, bootloader_ignore_signals=False,
    strip=False, upx=False, upx_exclude=[], runtime_tmpdir=None,
    console=False, disable_windowed_traceback=False, argv_emulation=False,
    target_arch=None, codesign_identity=None, entitlements_file=None,
)
