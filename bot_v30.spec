# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec — PDF-бот Аганим v3.5
# Вкус сборки задаётся переменной окружения PDFBOT_FLAVOR:
#   release (по умолчанию) — для клиентов: без встроенной таблицы,
#                            key.json в exe НЕ вшивается;
#   dev                    — тестовая сборка владельца: встроенная
#                            таблица + key.json из корня проекта (если есть).
import os
import json
import shutil

_flavor = os.environ.get('PDFBOT_FLAVOR', 'release').lower()
if _flavor not in ('release', 'dev'):
    _flavor = 'release'

# Меню трея делает `import dashboard`, а исходник называется
# dashboard_v30.py — кладём копию внутрь exe как dashboard.py.
_stage = os.path.abspath(os.path.join('build', '_spec_stage'))
os.makedirs(_stage, exist_ok=True)
shutil.copyfile('dashboard_v30.py', os.path.join(_stage, 'dashboard.py'))
with open(os.path.join(_stage, '_build_flavor.json'), 'w', encoding='utf-8') as f:
    json.dump({'flavor': _flavor}, f)

datas = [
    (os.path.join(_stage, 'dashboard.py'), '.'),
    (os.path.join(_stage, '_build_flavor.json'), '.'),
    ('deployment.py', '.'),
]
if _flavor == 'dev' and os.path.exists('key.json'):
    datas.append(('key.json', '.'))

a = Analysis(
    ['bot_v30.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'pystray._win32', 'watchdog.observers', 'watchdog.events',
        'pdfplumber', 'gspread', 'PIL.Image', 'PIL.ImageDraw',
        'customtkinter', 'darkdetect', 'tkinter.ttk', 'deployment',
    ],
    hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[],
    noarchive=False, optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name='pdf_bot', debug=False, bootloader_ignore_signals=False,
    strip=False, upx=False, upx_exclude=[], runtime_tmpdir=None,
    console=False, disable_windowed_traceback=False, argv_emulation=False,
    target_arch=None, codesign_identity=None, entitlements_file=None,
)
