import pdfplumber
import gspread
import os
import sys
import json
import logging
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

APP_VERSION = "3.5"

# ==========================================
# ОПРЕДЕЛЯЕМ ПАПКИ ПРОГРАММЫ
# ==========================================
# APP_DIR — папка с .exe (в Program Files доступна только для чтения)
# DATA_DIR — %APPDATA%\PDF-bot-Aganim (для записываемых файлов:
#            errors.log, config.json, извлечённого key.json)
if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

# DATA_DIR — только %APPDATA%\PDF-bot-Aganim; путь нормализуется (realpath
# устраняет любые ../) и проверяется, что остаётся внутри APPDATA.
_appdata_root = os.path.realpath(os.environ.get("APPDATA") or os.path.expanduser("~"))
DATA_DIR = os.path.realpath(os.path.join(_appdata_root, "PDF-bot-Aganim"))
if DATA_DIR != _appdata_root and not DATA_DIR.startswith(_appdata_root + os.sep):
    DATA_DIR = APP_DIR  # не прошли проверку границ — запасной вариант
try:
    os.makedirs(DATA_DIR, exist_ok=True)
except Exception:
    DATA_DIR = APP_DIR  # запасной вариант

os.chdir(DATA_DIR)


# ==========================================
# ПОИСК key.json (поддержка всех вариантов установки)
# ==========================================
def find_key_json():
    r"""
    Возвращает путь к key.json. Ищет в порядке:
      1. %APPDATA%\PDF-bot-Aganim\key.json (извлечён ранее)
      2. рядом с .exe (ручная установка)
      3. внутри .exe (bundled, sys._MEIPASS)
    Если нигде нет и есть bundled — извлекает в DATA_DIR.
    """
    # 1. В DATA_DIR
    p_data = os.path.join(DATA_DIR, "key.json")
    if os.path.exists(p_data):
        return p_data
    # 2. Рядом с .exe
    p_app = os.path.join(APP_DIR, "key.json")
    if os.path.exists(p_app):
        return p_app
    # 3. Bundled внутри .exe
    if getattr(sys, 'frozen', False):
        p_bundled = os.path.join(sys._MEIPASS, "key.json")
        if os.path.exists(p_bundled):
            # Пытаемся извлечь в DATA_DIR (для будущего доступа)
            try:
                import shutil
                shutil.copy2(p_bundled, p_data)
                return p_data
            except Exception:
                # Не получилось извлечь — используем напрямую из _MEIPASS
                return p_bundled
    return None


KEY_PATH = find_key_json()


# ==========================================
# НАСТРОЙКА ЛОГИРОВАНИЯ
# ==========================================
logger = logging.getLogger("bot")
logger.setLevel(logging.DEBUG)

formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

# Лог-файл — в DATA_DIR (записываемое место, работает и в Program Files)
_LOG_PATH = os.path.join(DATA_DIR, "errors.log")
try:
    file_handler = logging.FileHandler(_LOG_PATH, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
except Exception as _e:
    print(f"Не удалось создать файл лога {_LOG_PATH}: {_e}")

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


# ==========================================
# АВТОЗАПУСК ПРИ СТАРТЕ WINDOWS
# ==========================================
AUTOSTART_NAME = "PDFBotAganim"


def is_autostart_enabled():
    """Проверяет, включён ли автозапуск в реестре Windows."""
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_READ
        )
        try:
            value, _ = winreg.QueryValueEx(key, AUTOSTART_NAME)
            winreg.CloseKey(key)
            return bool(value)
        except FileNotFoundError:
            winreg.CloseKey(key)
            return False
    except Exception:
        return False


def set_autostart(enable):
    """Включает/отключает автозапуск через реестр Windows."""
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_WRITE
        )
        if enable:
            if getattr(sys, 'frozen', False):
                exe_path = sys.executable
                winreg.SetValueEx(key, AUTOSTART_NAME, 0, winreg.REG_SZ, f'"{exe_path}"')
            else:
                python_path = sys.executable
                script_path = os.path.abspath(__file__)
                winreg.SetValueEx(key, AUTOSTART_NAME, 0, winreg.REG_SZ,
                                  f'"{python_path}" "{script_path}"')
            logger.info("Автозапуск ВКЛЮЧЁН")
        else:
            try:
                winreg.DeleteValue(key, AUTOSTART_NAME)
                logger.info("Автозапуск ВЫКЛЮЧЕН")
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
        return True
    except Exception as e:
        logger.error(f"Ошибка настройки автозапуска: {e}")
        return False


# ==========================================
# WIN11 ТЕМА (customtkinter + darkdetect)
# ==========================================
import customtkinter as ctk
import darkdetect

# Следуем системной теме Windows (тёмная/светлая — авто)
ctk.set_appearance_mode("system")
ctk.set_default_color_theme("blue")


def _is_dark():
    """Определяем, активна ли тёмная тема в системе."""
    try:
        return darkdetect.theme() == "Dark"
    except Exception:
        return False


# Фирменный акцент Win11-стиля (оранжевый, как фирменный цвет Аганим)
ACCENT = "#FF6B35"
ACCENT_HOVER = "#FF8A5C"

# Тексты, которые меняются в зависимости от темы — получаем динамически
def theme_colors():
    """Возвращает словарь цветов под ТЕКУЩУЮ тему системы."""
    dark = _is_dark()
    return {
        "dark": dark,
        "bg": "#1f1f1f" if dark else "#f3f3f3",         # фон окна
        "card": "#2b2b2b" if dark else "#ffffff",        # карточки
        "card_hover": "#333333" if dark else "#fafafa",
        "fg": "#ffffff" if dark else "#1f1f1f",          # основной текст
        "fg_secondary": "#cccccc" if dark else "#5b5b5b",
        "fg_dim": "#9a9a9a" if dark else "#8a8a8a",
        "accent": ACCENT,
        "border": "#3a3a3a" if dark else "#e5e5e5",
        "danger": "#f8889b" if dark else "#c4243a",
        "success": "#7ec68c" if dark else "#2e8a45",
    }


def _apply_win11_window(window):
    """Применяет Win11-стиль к окну customtkinter: без рамок по бокам, аккуратные края."""
    try:
        window._set_scaling_awareness()
    except Exception:
        pass


# ==========================================
# WINDOWS-УВЕДОМЛЕНИЯ
# ==========================================
def _show_ctk_bubble(title, message, duration=5):
    """Современное всплывающее уведомление на customtkinter."""
    import threading

    def _popup():
        try:
            t = theme_colors()
            root = ctk.CTk()
            root.title(title)
            root.overrideredirect(True)
            root.attributes("-topmost", True)
            root.resizable(False, False)
            root.configure(fg_color=t["card"])

            # Акцентная полоска слева
            bar = ctk.CTkFrame(root, fg_color=ACCENT, corner_radius=0, width=4)
            bar.pack(side="left", fill="y")

            inner = ctk.CTkFrame(root, fg_color="transparent")
            inner.pack(side="left", fill="both", expand=True, padx=14, pady=12)

            ctk.CTkLabel(inner, text=title, font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                         text_color=ACCENT, anchor="w").pack(anchor="w")
            ctk.CTkLabel(inner, text=message,
                         font=ctk.CTkFont(family="Segoe UI", size=11),
                         text_color=t["fg_secondary"], anchor="w",
                         wraplength=320, justify="left").pack(anchor="w", pady=(4, 0))

            root.after(duration * 1000, root.destroy)
            # Размещаем в правом нижнем углу
            root.update_idletasks()
            w, h = 380, 90
            sw = root.winfo_screenwidth()
            sh = root.winfo_screenheight()
            root.geometry(f"{w}x{h}+{sw - w - 20}+{sh - h - 60}")
            root.mainloop()
        except Exception as e:
            try:
                logger.warning(f"CTk bubble не сработал: {e}")
            except Exception:
                pass

    threading.Thread(target=_popup, daemon=True).start()


def show_notification(title, message, duration=5):
    """Показывает уведомление: системный toast (Win11) + ctk-балун."""
    try:
        import subprocess
        safe_title = title.replace("'", "''")
        safe_message = message.replace("'", "''")

        ps_script = (
            f"[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, "
            f"ContentType = WindowsRuntime] > $null; "
            f"[Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom, "
            f"ContentType = WindowsRuntime] > $null; "
            f"$template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent("
            f"[Windows.UI.Notifications.ToastTemplateType]::ToastText02); "
            f"$textNodes = $template.GetElementsByTagName('text'); "
            f"$textNodes.Item(0).AppendChild($template.CreateTextNode('{safe_title}')) > $null; "
            f"$textNodes.Item(1).AppendChild($template.CreateTextNode('{safe_message}')) > $null; "
            f"$toast = [Windows.UI.Notifications.ToastNotification]::new($template); "
            f"[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("
            f"'PDF Бот').Show($toast)"
        )

        subprocess.run(
            ["powershell", "-Command", ps_script],
            creationflags=subprocess.CREATE_NO_WINDOW,
            timeout=10
        )
    except Exception as e:
        logger.warning(f"PowerShell уведомление не сработало: {e}")

    try:
        _show_ctk_bubble(title, message, duration)
        logger.info(f"[УВЕДОМЛЕНИЕ] {title}: {message}")
    except Exception as e:
        logger.error(f"Не удалось показать уведомление: {e}")


# ==========================================
# ССЫЛКА НА ТАБЛИЦУ
# ==========================================
SHEET_URL = "https://docs.google.com/spreadsheets/d/1QkXocbAJu1a5rcu3XNEfpHnoF_mA5flgehjO6E7VIWM/edit?usp=sharing"
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")  # настройки развёртывания (URL таблицы)

# Встроенный URL таблицы (текущее развёртывание). На новом объекте
# мастер первичной настройки заменит его своим значением в settings.json.
DEFAULT_SHEET_URL = "https://docs.google.com/spreadsheets/d/1QkXocbAJu1a5rcu3XNEfpHnoF_mA5flgehjO6E7VIWM/edit?usp=sharing"

# Telegram-бот для уведомлений дизайнерам об оплате счетов
BOT_TOKEN = "7690342745:AAEh5i7YihlNwYzmvDPb_rBWom_IZsYnemE"
THRESHOLD_MONTHLY = 500000   # порог за месяц для ставки 10%

# ==========================================
# ИЗВЛЕЧЕНИЕ ДАТЫ / НОМЕРА / КЛИЕНТА ИЗ PDF
# ==========================================
MONTHS_RU = {
    "января": "01", "февраля": "02", "марта": "03", "апреля": "04",
    "мая": "05", "июня": "06", "июля": "07", "августа": "08",
    "сентября": "09", "октября": "10", "ноября": "11", "декабря": "12"
}


def extract_invoice_date(filename):
    """Извлекает дату из названия файла -> ДД.ММ.ГГГГ."""
    try:
        if " от " not in filename:
            return ""
        start = filename.find(" от ") + 4
        end = filename.find(" г", start)
        if end == -1:
            end = len(filename) - 4
        date_str = filename[start:end].strip()
        parts = date_str.split()
        if len(parts) == 3:
            day = parts[0].zfill(2)
            month = MONTHS_RU.get(parts[1].lower(), "")
            year = parts[2]
            if month:
                return f"{day}.{month}.{year}"
    except Exception as e:
        logger.warning(f"Не удалось извлечь дату из '{filename}': {e}")
    return ""


def parse_date_string(date_str):
    """Разбирает строку даты -> ДД.ММ.ГГГГ."""
    import re
    date_str = date_str.strip().rstrip("г.").rstrip(".").strip()
    parts = date_str.split()
    if len(parts) == 3:
        day = parts[0].zfill(2)
        month = MONTHS_RU.get(parts[1].lower(), "")
        year = parts[2]
        if month:
            return f"{day}.{month}.{year}"
    m = re.match(r"^(\d{1,2})[.\-](\d{1,2})[.\-](\d{4})$", date_str)
    if m:
        day, month, year = m.group(1), m.group(2), m.group(3)
        return f"{day.zfill(2)}.{month.zfill(2)}.{year}"
    return ""


def extract_invoice_from_pdf_text(text):
    """Ищет номер счёта и дату ВНУТРИ текста PDF."""
    import re
    invoice_number = None
    invoice_date = None
    pattern = re.compile(
        r"счет[^№]*№\s*(\d{1,6})\s*от\s*([^.]+?)г\.",
        re.IGNORECASE
    )
    matches = pattern.findall(text)
    if matches:
        num_raw, date_raw = matches[0]
        invoice_number = num_raw.strip()
        parsed_date = parse_date_string(date_raw)
        if parsed_date:
            invoice_date = parsed_date
    return invoice_number, invoice_date


def extract_invoice_amount(text):
    """
    Извлекает сумму счёта из текста PDF.
    Ищет «Всего к оплате: 7 747,20» → 7747.20
    Возвращает float или 0 если не найдено.
    """
    import re
    # Сначала пробуем «Всего к оплате», потом «Итого» (fallback)
    for marker in ["Всего к оплате", "Всего к оплате:", "Итого", "Итого:"]:
        idx = text.find(marker)
        if idx == -1:
            continue
        # берём строку после маркера до конца строки
        rest = text[idx + len(marker):]
        line_end = rest.find("\n")
        if line_end != -1:
            rest = rest[:line_end]
        # ищем число вида "7 747,20" или "7747.20"
        m = re.search(r"(\d[\d\s]*[.,]?\d*)", rest)
        if m:
            num_str = m.group(1).strip()
            # нормализуем: убираем пробелы, запятую → точка
            num_str = num_str.replace(" ", "").replace("\xa0", "")
            num_str = num_str.replace(",", ".")
            try:
                return float(num_str)
            except ValueError:
                continue
    return 0.0


def get_designer_percent(designer, gc, current_date_str=""):
    """
    Определяет ставку бонуса дизайнера.
    Правило: 5% базово. Если сумма счетов за ПОСЛЕДНИЕ 30 дней >= 500 000 ₽ — 10%.
    Читает лист «Детализация» через gspread.
    """
    if not designer:
        return 5
    try:
        from datetime import datetime, timedelta
        ss = gc.open_by_url(SHEET_URL)
        try:
            det = ss.worksheet("Детализация")
        except Exception:
            return 5
        data = det.get_all_values()
        if len(data) <= 1:
            return 5

        # Точка отсчёта
        if current_date_str:
            try:
                today = datetime.strptime(current_date_str, "%d.%m.%Y")
            except ValueError:
                today = datetime.now()
        else:
            today = datetime.now()
        month_ago = today - timedelta(days=30)

        designer_lower = designer.strip().lower()
        total = 0.0
        for row in data[1:]:
            while len(row) < 6:
                row.append("")
            name = str(row[4]).strip().lower()  # E — дизайнер
            if name != designer_lower:
                continue
            # Дата счёта
            d_str = str(row[1]).strip()
            try:
                d = datetime.strptime(d_str, "%d.%m.%Y")
            except ValueError:
                continue
            if d < month_ago or d > today:
                continue
            # Сумма
            try:
                s = float(str(row[5]).replace(" ", "").replace("\xa0", "")
                          .replace(",", ".")) if row[5] else 0
            except ValueError:
                s = 0
            total += s

        return 10 if total >= THRESHOLD_MONTHLY else 5
    except Exception as e:
        logger.warning(f"Не удалось определить % дизайнера: {e}")
        return 5


def send_designer_notification(designer, invoice, bonus, percent, client, amount, gc):
    """
    Отправляет дизайнеру уведомление в Telegram об оплате счёта.
    Ищет chat_id дизайнера во вкладке «Telegram ID».
    """
    if not designer or bonus <= 0:
        return
    try:
        # Ищем chat_id дизайнера во вкладке Telegram ID
        ss = gc.open_by_url(SHEET_URL)
        try:
            tg_sheet = ss.worksheet("Telegram ID")
        except Exception:
            return
        data = tg_sheet.get_all_values()
        designer_lower = designer.strip().lower()
        chat_id = None
        for row in data[1:]:
            if len(row) < 3:
                continue
            name = str(row[0]).strip().lower()
            tg_type = str(row[2]).strip().lower()
            if name == designer_lower and tg_type == "дизайнер" and row[1].strip():
                chat_id = str(row[1]).strip()
                break

        if not chat_id:
            logger.info(f"Дизайнер '{designer}' не привязан к Telegram — пропуск уведомления")
            return

        # Формируем сообщение
        msg = (
            f"💰 Счёт №{invoice} оплачен\n\n"
            f"👤 Клиент: {client}\n"
            f"💵 Сумма счёта: {amount:,.2f} ₽\n".replace(",", " ") +
            f"📊 Ваш бонус ({percent}%): {bonus:,.2f} ₽\n".replace(",", " ") +
            "⏰ Выплата в течение 7 дней"
        )

        # ОТПРАВКА ЧЕРЕЗ GOOGLE APPS SCRIPT (api.telegram.org заблокирован на ПК).
        # Вся сетевая часть и валидация URL — в deployment.call_apps_script.
        url_apps = _get_apps_script_url(gc)
        if url_apps:
            import deployment as _dep
            body = _dep.call_apps_script(url_apps, {
                "action": "notify",
                "chat_id": chat_id,
                "text": msg,
            })
            if body and "ok" in body.lower():
                logger.info(f"Уведомление дизайнеру {designer} отправлено через Apps Script")
            elif body:
                logger.warning(f"Apps Script ответил: {body[:100]}")
            else:
                logger.warning("Запрос к Apps Script не выполнен (валидация/сеть)")
        else:
            logger.warning("URL Apps Script не задан (Настройки!B2) — ТГ не отправлен")
    except Exception as e:
        logger.warning(f"Ошибка отправки уведомления дизайнеру: {e}")


def _get_apps_script_url(gc):
    """Читает URL веб-приложения из «Настройки»!B2.
    Возвращает только https://script.google.com/... (строгий whitelist)."""
    import deployment
    try:
        ss = gc.open_by_url(SHEET_URL)
        st = ss.worksheet("Настройки")
        val = st.get("B2")
        url = str(val[0][0] if val else "").strip()
        if deployment.is_valid_apps_script_url(url):
            return url
    except Exception:
        pass
    return ""


def parse_buyer_and_phone(text):
    """
    Извлекает ЧИСТОЕ имя клиента и телефон из текста PDF.
      - Кавычки убираются: ООО «ШЭМРОК» → ООО ШЭМРОК
      - ИНН/КПП/ОГРН/адрес — отрезаются
      - Телефон: всё что после «тел.» (включая доп.имя/комментарий)
      - Физлицо: всё после запятой в имени — отрезается
    """
    import re
    lines = text.split("\n")
    buyer_line = ""
    for line in lines:
        s = line.strip()
        if "Покупатель" in s and s.find("Покупатель") < 30:
            idx = s.find("Покупатель")
            buyer_line = s[idx + len("Покупатель"):].strip()
            break

    if not buyer_line or buyer_line.startswith("("):
        return "", ""

    phone = ""
    phone_match = re.search(r"тел\.?\s*:?\s*(.+)$", buyer_line, re.IGNORECASE)
    if phone_match:
        phone = phone_match.group(1).strip()
        phone = phone.lstrip(" :").rstrip(" ,").strip()

    name_part = buyer_line
    low = name_part.lower()
    if "тел" in low:
        idx_tel = low.find("тел")
        if idx_tel > 0:
            name_part = name_part[:idx_tel].strip()

    for kw in ["ИНН", "инн", "КПП", "кпп", "ОГРН", "огрн",
               "ОГРНИП", "огрип", "Юр. адрес", "юр. адрес"]:
        if kw in name_part:
            idx_kw = name_part.find(kw)
            name_part = name_part[:idx_kw].strip()

    name_part = name_part.rstrip(", ").strip()

    is_legal = bool(re.search(
        r"\b(ООО|ОАО|ЗАО|ПАО|АО|ИП|НКО)\b",
        name_part, re.IGNORECASE
    ))

    if not is_legal and "," in name_part:
        name_part = name_part.split(",")[0].strip()

    # Убираем кавычки всех видов
    name_part = re.sub(r'["""«»\']+', " ", name_part)
    name_part = re.sub(r"\s+", " ", name_part).strip()

    return name_part, phone


# ==========================================
# ГИБКИЙ ПАРСЕР ПОЗИЦИЙ ПОСТАВЩИКА
# ==========================================
def parse_supplier_input(input_text, remaining_positions):
    """
    Гибкий парсер строки «позиции - поставщик».
    Принимает любые разделители: 1,2-ВИА / 1.2-ВИА / 1 ,2 - виа / 1-2-3 - ВИА
    """
    import re
    text = input_text.strip()
    if not text:
        return "Пустой ввод.\nПример: 1,2,4 - ВИА"

    m = re.search(r"^(.*?)\s*[-–—−]\s*([^0-9].*)$", text)
    if not m:
        return "Формат: позиции - поставщик\nПример: 1,2,4 - ВИА"

    positions_str = m.group(1).strip()
    supplier = m.group(2).strip()

    if not supplier:
        return "Не указан поставщик.\nПример: 1,2,4 - ВИА"

    normalized = positions_str.replace(".", ",").replace("-", ",").replace("–", ",").replace("—", ",")

    parsed_positions = []
    for part in normalized.split(","):
        p = part.strip()
        if not p:
            continue
        if not p.isdigit():
            return f"Позиции должны быть числами.\nБыло: '{positions_str}'"
        parsed_positions.append(int(p))

    if not parsed_positions:
        return f"Не разобрал позиции.\nБыло: '{positions_str}'"

    for p in parsed_positions:
        if p not in remaining_positions:
            free = ", ".join(str(x) for x in remaining_positions)
            return f"Позиция {p} уже занята или не существует.\nСвободные: {free}"

    return supplier, parsed_positions


# ==========================================
# ЦЕНТРИРОВАНИЕ ОКОН
# ==========================================
def _center_window(window):
    window.update_idletasks()
    w = window._current_width if hasattr(window, '_current_width') else window.winfo_width()
    h = window._current_height if hasattr(window, '_current_height') else window.winfo_height()
    try:
        w = int(window.geometry().split('x')[0].split('+')[-1]) if 'x' in window.geometry() else w
    except Exception:
        pass
    sw = window.winfo_screenwidth()
    sh = window.winfo_screenheight()
    x = (sw // 2) - (w // 2)
    y = (sh // 2) - (h // 2)
    window.geometry(f"+{x}+{y}")


# ==========================================
# ЧТЕНИЕ СПРАВОЧНИКА "Telegram ID"
# ==========================================
def get_contacts_list():
    empty = {"менеджеры": [], "дизайнеры": [], "руководители": [], "все": []}
    try:
        gc = gspread.service_account(filename=KEY_PATH)
        spreadsheet = gc.open_by_url(SHEET_URL)
        try:
            tg_sheet = spreadsheet.worksheet("Telegram ID")
        except gspread.exceptions.WorksheetNotFound:
            logger.warning("Вкладка 'Telegram ID' не найдена")
            return empty
        data = tg_sheet.get_all_values()
        if len(data) <= 1:
            return empty
        result = {"менеджеры": [], "дизайнеры": [], "руководители": [], "все": []}
        for row in data[1:]:
            if len(row) < 3:
                continue
            name = str(row[0]).strip()
            tg_type = str(row[2]).strip().lower()
            if not name:
                continue
            if tg_type == "менеджер":
                result["менеджеры"].append(name)
            elif tg_type == "дизайнер":
                result["дизайнеры"].append(name)
            elif tg_type == "руководитель":
                result["руководители"].append(name)
            if name not in result["все"]:
                result["все"].append(name)
        logger.info(f"Справочник загружен: {len(result['менеджеры'])} менеджеров, "
                    f"{len(result['дизайнеры'])} дизайнеров, "
                    f"{len(result['руководители'])} руководителей")
        return result
    except Exception as e:
        logger.error(f"Ошибка чтения справочника: {e}")
        return empty


def add_contact_to_directory(name, contact_type):
    try:
        gc = gspread.service_account(filename=KEY_PATH)
        spreadsheet = gc.open_by_url(SHEET_URL)
        tg_sheet = spreadsheet.worksheet("Telegram ID")
        tg_sheet.append_row([name, "", contact_type])
        logger.info(f"Добавлен контакт в справочник: {name} ({contact_type})")
        return True
    except Exception as e:
        logger.error(f"Не удалось добавить контакт в справочник: {e}")
        return False


# ==========================================
# ВИДЖЕТ: АВТОДОПОЛНЕНИЕ (customtkinter)
# ==========================================
class AutocompleteEntry(ctk.CTkEntry):
    """
    Поле ввода с автодополнением на customtkinter.
    Показывает всплывающий список совпадений под полем.
    """
    def __init__(self, master, values=None, **kwargs):
        super().__init__(master, **kwargs)
        self.all_values = values or []
        self._popup = None
        self._listbox = None
        self.bind("<KeyRelease>", self._on_key_release)
        self.bind("<Down>", self._on_arrow_down)
        self.bind("<Up>", self._on_arrow_up)
        self.bind("<Return>", self._on_enter)
        self.bind("<FocusOut>", self._on_focus_out)
        # Вставка из буфера обмена (Ctrl+V) — customtkinter по умолчанию может
        # не давать, поэтому биндим явно
        self.bind("<Control-v>", self._on_paste)
        self.bind("<Control-V>", self._on_paste)

    def set_values(self, values):
        self.all_values = values or []

    def _on_paste(self, event):
        """Явная обработка Ctrl+V — вставка из буфера обмена."""
        try:
            import tkinter as tk
            clipped = self.clipboard_get()
            # Вставляем в позицию курсора, заменяя выделение
            if self.selection_present():
                self.delete("sel.first", "sel.last")
            self.insert("insert", clipped)
            self._on_key_release(event)
            return "break"
        except tk.TclError:
            # Буфер пуст
            return "break"

    def _on_key_release(self, event):
        import tkinter as tk
        if event.keysym in ("Up", "Down", "Return", "Escape", "Tab",
                            "Shift_L", "Shift_R", "Control_L", "Control_R"):
            return
        typed = self.get().strip().lower()
        if typed:
            filtered = [v for v in self.all_values if typed in v.lower()]
        else:
            filtered = self.all_values[:10]
        if len(filtered) == 0:
            self._hide_popup()
            return
        if len(filtered) == 1 and filtered[0].lower() == typed:
            self._hide_popup()
            return
        self._show_popup(filtered)

    def _show_popup(self, values):
        import tkinter as tk
        t = theme_colors()
        if self._popup and self._listbox:
            self._listbox.delete(0, tk.END)
            for v in values:
                self._listbox.insert(tk.END, v)
            return

        self._popup = tk.Toplevel(self)
        self._popup.wm_overrideredirect(True)
        self._popup.attributes("-topmost", True)
        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height()
        self._popup.wm_geometry(f"+{x}+{y}")

        border = tk.Frame(self._popup, bg=ACCENT, padx=1, pady=1)
        border.pack()

        # Ширина popup = самое длинное имя в values (в символах),
        # минимум 30 символов чтобы имена были видны полностью
        max_len = max((len(v) for v in values), default=20)
        listbox_width = max(30, max_len + 4)

        self._listbox = tk.Listbox(
            border,
            font=("Segoe UI", 11),
            bg=t["card"], fg=t["fg"],
            selectbackground=ACCENT,
            selectforeground="#ffffff",
            activestyle="none",
            relief="flat", bd=0,
            highlightthickness=0,
            selectborderwidth=0,
            width=listbox_width
        )
        self._listbox.pack()
        for v in values:
            self._listbox.insert(tk.END, v)
        self._listbox.bind("<Button-1>", self._on_listbox_click)

    def __len__(self):
        return len(self.all_values)

    def _hide_popup(self):
        import tkinter as tk
        if self._popup:
            self._popup.destroy()
            self._popup = None
            self._listbox = None

    def _on_listbox_click(self, event):
        import tkinter as tk
        if self._listbox:
            selection = self._listbox.curselection()
            if not selection:
                index = self._listbox.nearest(event.y)
            else:
                index = selection[0]
            value = self._listbox.get(index)
            self.delete(0, tk.END)
            self.insert(0, value)
            self._hide_popup()

    def _on_arrow_down(self, event):
        import tkinter as tk
        if self._listbox and self._listbox.size() > 0:
            current = self._listbox.curselection()
            if current:
                next_idx = min(current[0] + 1, self._listbox.size() - 1)
            else:
                next_idx = 0
            self._listbox.selection_clear(0, tk.END)
            self._listbox.selection_set(next_idx)
            self._listbox.see(next_idx)
            return "break"

    def _on_arrow_up(self, event):
        import tkinter as tk
        if self._listbox and self._listbox.size() > 0:
            current = self._listbox.curselection()
            if current:
                prev_idx = max(current[0] - 1, 0)
            else:
                prev_idx = 0
            self._listbox.selection_clear(0, tk.END)
            self._listbox.selection_set(prev_idx)
            self._listbox.see(prev_idx)
            return "break"

    def _on_enter(self, event):
        import tkinter as tk
        if self._listbox and self._listbox.size() > 0:
            current = self._listbox.curselection()
            if current:
                value = self._listbox.get(current[0])
                self.delete(0, tk.END)
                self.insert(0, value)
                self._hide_popup()
                return "break"

    def _on_focus_out(self, event):
        self.after(200, self._hide_popup)

    def get_value(self):
        return self.get().strip()

    def set_value(self, value):
        import tkinter as tk
        self.delete(0, tk.END)
        self.insert(0, value)


# ==========================================
# ДИАЛОГИ ВВОДА (customtkinter Win11)
# ==========================================
def check_and_offer_add(name, contact_type, known_names):
    if not name:
        return name
    name_lower = name.lower().strip()
    found = False
    for known in known_names:
        if known.lower().strip() == name_lower:
            found = True
            break
    if found:
        return name
    answer = _custom_askyesno(
        "Нет в справочнике",
        f"Имя '{name}' не найдено в справочнике.\n\n"
        f"Telegram-уведомления по этому имени работать НЕ будут.\n\n"
        f"Добавить '{name}' в справочник как {contact_type}?"
    )
    if answer:
        if add_contact_to_directory(name, contact_type):
            _custom_showinfo("Добавлено",
                f"'{name}' добавлен в справочник.\n\n"
                f"Теперь нужно, чтобы {name} написал боту /start\n"
                f"и прислал свой Telegram ID для привязки.")
            return name
        else:
            _custom_showinfo("Ошибка",
                "Не удалось добавить в справочник.\nПроверьте интернет-соединение.")
            return name
    else:
        return name


def _center_ctk(root, w, h):
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    x = (sw // 2) - (w // 2)
    y = (sh // 2) - (h // 2)
    root.geometry(f"{w}x{h}+{x}+{y}")


def _custom_askyesno(title, message):
    """Современный диалог Да/Нет на customtkinter (Win11-стиль)."""
    t = theme_colors()
    result = {"answer": False}

    def on_yes():
        result["answer"] = True
        root.destroy()

    def on_no():
        result["answer"] = False
        root.destroy()

    root = ctk.CTk()
    root.title(title)
    root.attributes("-topmost", True)
    root.resizable(False, False)
    root.configure(fg_color=t["bg"])

    body = ctk.CTkFrame(root, fg_color="transparent")
    body.pack(fill="both", expand=True, padx=28, pady=28)

    ctk.CTkLabel(body, text=title,
                 font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
                 text_color=ACCENT, anchor="w").pack(anchor="w")
    ctk.CTkLabel(body, text=message,
                 font=ctk.CTkFont(family="Segoe UI", size=13),
                 text_color=t["fg_secondary"], anchor="w",
                 wraplength=400, justify="left").pack(anchor="w", pady=(10, 22))

    btns = ctk.CTkFrame(body, fg_color="transparent")
    btns.pack(side="right", anchor="e")

    ctk.CTkButton(btns, text="Нет", width=100, command=on_no,
                  fg_color=t["card"], border_width=1, border_color=t["border"],
                  text_color=t["fg"], hover_color=t["card_hover"],
                  font=ctk.CTkFont(family="Segoe UI", size=13)).pack(side="left", padx=(0, 8))
    ctk.CTkButton(btns, text="Да", width=100, command=on_yes,
                  fg_color=ACCENT, hover_color=ACCENT_HOVER,
                  text_color="#ffffff",
                  font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold")).pack(side="left")

    root.bind("<Return>", lambda e: on_yes())
    root.bind("<Escape>", lambda e: on_no())
    _center_ctk(root, 480, 220)
    root.mainloop()
    return result["answer"]


def _custom_showinfo(title, message):
    """Современный диалог OK на customtkinter (Win11-стиль)."""
    t = theme_colors()

    def on_ok():
        root.destroy()

    root = ctk.CTk()
    root.title(title)
    root.attributes("-topmost", True)
    root.resizable(False, False)
    root.configure(fg_color=t["bg"])

    body = ctk.CTkFrame(root, fg_color="transparent")
    body.pack(fill="both", expand=True, padx=28, pady=28)

    ctk.CTkLabel(body, text=title,
                 font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
                 text_color=ACCENT, anchor="w").pack(anchor="w")
    ctk.CTkLabel(body, text=message,
                 font=ctk.CTkFont(family="Segoe UI", size=13),
                 text_color=t["fg_secondary"], anchor="w",
                 wraplength=400, justify="left").pack(anchor="w", pady=(10, 22))

    ctk.CTkButton(body, text="OK", width=120, command=on_ok,
                  fg_color=ACCENT, hover_color=ACCENT_HOVER,
                  text_color="#ffffff",
                  font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold")).pack(side="right", anchor="e")

    root.bind("<Return>", lambda e: on_ok())
    root.bind("<Escape>", lambda e: on_ok())
    _center_ctk(root, 480, 220)
    root.mainloop()


# ==========================================
# ДИАЛОГ 1: Данные по счёту
# ==========================================
def show_invoice_dialog(invoice, invoice_date, client, qty, default_manager="",
                       contacts=None, default_phone=""):
    """
    ОКОШКО 1: Данные по счёту (один раз на весь счёт).
    Win11-стиль на customtkinter.
    Возвращает (designer, manager, payment_form, phone, notify_date) или None.
    """
    if contacts is None:
        contacts = {"менеджеры": [], "дизайнеры": [], "все": []}

    result = {"designer": "", "manager": default_manager, "payment_form": "", "phone": "", "notify_date": ""}
    dialog_done = False
    t = theme_colors()

    def on_ok():
        nonlocal dialog_done
        result["designer"] = combo_designer.get_value()
        result["manager"] = combo_manager.get_value()
        result["payment_form"] = entry_payment.get().strip()
        result["phone"] = entry_phone.get().strip()
        # Дата уведомления: если галка «Сегодня» — сегодняшняя дата,
        # иначе — что вписано вручную
        if chk_today.get():
            from datetime import datetime as _dt
            result["notify_date"] = _dt.now().strftime("%d.%m.%Y")
        else:
            result["notify_date"] = entry_notify_date.get().strip()
        dialog_done = True
        root.destroy()

    def on_cancel():
        nonlocal dialog_done
        dialog_done = True
        root.destroy()

    root = ctk.CTk()
    root.title(f"Счёт №{invoice}")
    root.attributes("-topmost", True)
    root.resizable(False, False)
    root.configure(fg_color=t["bg"])

    # Заголовок
    header = ctk.CTkFrame(root, fg_color="transparent")
    header.pack(fill="x", padx=24, pady=(24, 4))
    ctk.CTkLabel(header, text=f"Счёт №{invoice}",
                 font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
                 text_color=t["fg"], anchor="w").pack(anchor="w")
    ctk.CTkLabel(header, text=f"Дата: {invoice_date if invoice_date else 'не распознана'}",
                 font=ctk.CTkFont(family="Segoe UI", size=12),
                 text_color=t["fg_dim"], anchor="w").pack(anchor="w", pady=(2, 0))

    # Карточка: Данные из PDF
    pdf_card = ctk.CTkFrame(root, fg_color=t["card"], corner_radius=10, border_width=1, border_color=t["border"])
    pdf_card.pack(fill="x", padx=24, pady=(16, 0))

    inner_pdf = ctk.CTkFrame(pdf_card, fg_color="transparent")
    inner_pdf.pack(fill="x", padx=18, pady=16)

    ctk.CTkLabel(inner_pdf, text="Данные из счёта",
                 font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                 text_color=ACCENT, anchor="w").pack(anchor="w", pady=(0, 8))

    info_grid = ctk.CTkFrame(inner_pdf, fg_color="transparent")
    info_grid.pack(fill="x")
    info_grid.columnconfigure(1, weight=1)
    rows = [("Клиент:", client), ("Позиций:", str(qty))]
    for i, (lbl, val) in enumerate(rows):
        ctk.CTkLabel(info_grid, text=lbl, width=90, anchor="w",
                     font=ctk.CTkFont(family="Segoe UI", size=12),
                     text_color=t["fg_secondary"]).grid(row=i, column=0, sticky="w", pady=1)
        ctk.CTkLabel(info_grid, text=val, anchor="w",
                     font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                     text_color=t["fg"]).grid(row=i, column=1, sticky="w", pady=1)

    # Карточка: Заполните
    input_card = ctk.CTkFrame(root, fg_color=t["card"], corner_radius=10, border_width=1, border_color=t["border"])
    input_card.pack(fill="x", padx=24, pady=(12, 0))

    inner_in = ctk.CTkFrame(input_card, fg_color="transparent")
    inner_in.pack(fill="x", padx=18, pady=16)

    ctk.CTkLabel(inner_in, text="Заполните",
                 font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                 text_color=ACCENT, anchor="w").pack(anchor="w", pady=(0, 10))

    # Телефон
    ctk.CTkLabel(inner_in, text="Телефон клиента", anchor="w",
                 font=ctk.CTkFont(family="Segoe UI", size=12),
                 text_color=t["fg_secondary"]).pack(anchor="w", pady=(6, 2))
    entry_phone = ctk.CTkEntry(inner_in, width=320, height=36,
                               fg_color=t["bg"], border_color=t["border"], border_width=1,
                               text_color=t["fg"],
                               font=ctk.CTkFont(family="Segoe UI", size=13))
    entry_phone.pack(fill="x")
    if default_phone:
        entry_phone.insert(0, default_phone)

    # Дизайнер
    ctk.CTkLabel(inner_in, text="Дизайнер", anchor="w",
                 font=ctk.CTkFont(family="Segoe UI", size=12),
                 text_color=t["fg_secondary"]).pack(anchor="w", pady=(10, 2))
    combo_designer = AutocompleteEntry(inner_in, values=contacts.get("дизайнеры", []),
                                       width=320, height=36,
                                       fg_color=t["bg"], border_color=t["border"], border_width=1,
                                       text_color=t["fg"],
                                       font=ctk.CTkFont(family="Segoe UI", size=13))
    combo_designer.pack(fill="x")

    # Менеджер
    ctk.CTkLabel(inner_in, text="Менеджер", anchor="w",
                 font=ctk.CTkFont(family="Segoe UI", size=12),
                 text_color=t["fg_secondary"]).pack(anchor="w", pady=(10, 2))
    combo_manager = AutocompleteEntry(inner_in, values=contacts.get("менеджеры", []),
                                      width=320, height=36,
                                      fg_color=t["bg"], border_color=t["border"], border_width=1,
                                      text_color=t["fg"],
                                      font=ctk.CTkFont(family="Segoe UI", size=13))
    combo_manager.pack(fill="x")
    combo_manager.set_value(default_manager)

    # Форма оплаты
    ctk.CTkLabel(inner_in, text="Форма оплаты", anchor="w",
                 font=ctk.CTkFont(family="Segoe UI", size=12),
                 text_color=t["fg_secondary"]).pack(anchor="w", pady=(10, 2))
    entry_payment = ctk.CTkEntry(inner_in, width=320, height=36,
                                 fg_color=t["bg"], border_color=t["border"], border_width=1,
                                 text_color=t["fg"],
                                 font=ctk.CTkFont(family="Segoe UI", size=13))
    entry_payment.pack(fill="x")

    # Дата уведомления клиента + галка «Сегодня»
    from datetime import datetime as _dt
    today_str = _dt.now().strftime("%d.%m.%Y")
    notify_lbl_row = ctk.CTkFrame(inner_in, fg_color="transparent")
    notify_lbl_row.pack(fill="x", pady=(10, 2))
    ctk.CTkLabel(notify_lbl_row, text="Дата уведомления клиента", anchor="w",
                 font=ctk.CTkFont(family="Segoe UI", size=12),
                 text_color=t["fg_secondary"]).pack(side="left")

    notify_row = ctk.CTkFrame(inner_in, fg_color="transparent")
    notify_row.pack(fill="x")

    chk_today = ctk.CTkCheckBox(notify_row, text=f"Сегодня ({today_str})",
                                font=ctk.CTkFont(family="Segoe UI", size=12),
                                fg_color=ACCENT, hover_color=ACCENT_HOVER,
                                checkmark_color="#ffffff",
                                text_color=t["fg"], height=36,
                                checkbox_width=22, checkbox_height=22, corner_radius=4)
    chk_today.pack(side="left", padx=(0, 10))

    def _toggle_date_entry():
        """Галка «Сегодня» блокирует ручной ввод даты."""
        if chk_today.get():
            entry_notify_date.configure(state="disabled",
                                        placeholder_text="Сегодня")
        else:
            entry_notify_date.configure(state="normal",
                                        placeholder_text="или впишите дату (ДД.ММ.ГГГГ)")
    chk_today.configure(command=_toggle_date_entry)

    entry_notify_date = ctk.CTkEntry(notify_row, width=170, height=36,
                                     fg_color=t["bg"], border_color=t["border"], border_width=1,
                                     text_color=t["fg"],
                                     placeholder_text="или впишите дату (ДД.ММ.ГГГГ)",
                                     font=ctk.CTkFont(family="Segoe UI", size=13))
    entry_notify_date.pack(side="right")

    combo_designer.focus_set()

    # Кнопки — одинаковые по ширине, выровнены по сетке
    btn_frame = ctk.CTkFrame(root, fg_color="transparent")
    btn_frame.pack(fill="x", padx=24, pady=(16, 24))
    btn_frame.columnconfigure((0, 1), weight=1, uniform="btns")
    ctk.CTkButton(btn_frame, text="Отмена", height=40, command=on_cancel,
                  fg_color=t["card"], border_width=1, border_color=t["border"],
                  text_color=t["fg"], hover_color=t["card_hover"],
                  font=ctk.CTkFont(family="Segoe UI", size=13),
                  corner_radius=8).grid(row=0, column=0, sticky="ew", padx=(0, 6))
    ctk.CTkButton(btn_frame, text="OK", height=40, command=on_ok,
                  fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color="#ffffff",
                  font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                  corner_radius=8).grid(row=0, column=1, sticky="ew", padx=(6, 0))

    root.bind("<Return>", lambda e: on_ok())
    root.bind("<Escape>", lambda e: on_cancel())
    _center_ctk(root, 440, 760)
    root.minsize(440, 760)
    root.mainloop()

    if not dialog_done or not result["manager"]:
        return None
    return (result["designer"], result["manager"], result["payment_form"],
            result["phone"], result["notify_date"])


# ==========================================
# ДИАЛОГ 2: Поставщик
# ==========================================
def show_supplier_dialog(remaining_positions, invoice, supplier_hint="", default_supplier_invoice=""):
    """
    ОКОШКО 2: Распределение позиций по поставщикам. Win11-стиль.
    """
    t = theme_colors()
    result = {
        "supplier": supplier_hint,
        "input_text": "",
        "supplier_invoice": default_supplier_invoice
    }
    dialog_done = False

    def on_ok():
        nonlocal dialog_done
        result["input_text"] = entry_positions.get().strip()
        result["supplier_invoice"] = entry_supplier_invoice.get().strip()
        dialog_done = True
        root.destroy()

    def on_cancel():
        nonlocal dialog_done
        dialog_done = True
        root.destroy()

    root = ctk.CTk()
    root.title(f"Счёт №{invoice} — Поставщик")
    root.attributes("-topmost", True)
    root.resizable(False, False)
    root.configure(fg_color=t["bg"])

    header = ctk.CTkFrame(root, fg_color="transparent")
    header.pack(fill="x", padx=24, pady=(24, 4))
    ctk.CTkLabel(header, text=f"Счёт №{invoice} — Распределение",
                 font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
                 text_color=t["fg"], anchor="w").pack(anchor="w")

    # Свободные позиции
    pos_card = ctk.CTkFrame(root, fg_color=t["card"], corner_radius=10, border_width=1, border_color=t["border"])
    pos_card.pack(fill="x", padx=24, pady=(16, 0))
    inner_pos = ctk.CTkFrame(pos_card, fg_color="transparent")
    inner_pos.pack(fill="x", padx=18, pady=16)

    remaining_str = ", ".join(str(p) for p in remaining_positions)
    ctk.CTkLabel(inner_pos, text=f"Свободные позиции ({len(remaining_positions)}):",
                 font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                 text_color=ACCENT, anchor="w").pack(anchor="w")
    ctk.CTkLabel(inner_pos, text=remaining_str,
                 font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
                 text_color=t["fg"], anchor="w").pack(anchor="w", pady=(6, 0))

    # Ввод поставщика
    input_card = ctk.CTkFrame(root, fg_color=t["card"], corner_radius=10, border_width=1, border_color=t["border"])
    input_card.pack(fill="x", padx=24, pady=(12, 0))
    inner_in = ctk.CTkFrame(input_card, fg_color="transparent")
    inner_in.pack(fill="x", padx=18, pady=16)

    ctk.CTkLabel(inner_in, text="Пример:  1,2,4 - ВИА   (разделители любые: , . - пробел)",
                 font=ctk.CTkFont(family="Segoe UI", size=11),
                 text_color=t["fg_dim"], anchor="w").pack(anchor="w", pady=(0, 8))

    ctk.CTkLabel(inner_in, text="Поз. — Поставщик", anchor="w",
                 font=ctk.CTkFont(family="Segoe UI", size=12),
                 text_color=t["fg_secondary"]).pack(anchor="w", pady=(6, 2))
    entry_positions = ctk.CTkEntry(inner_in, width=340, height=36,
                                   fg_color=t["bg"], border_color=t["border"], border_width=1,
                                   text_color=t["fg"],
                                   font=ctk.CTkFont(family="Segoe UI", size=13))
    entry_positions.pack(fill="x")

    ctk.CTkLabel(inner_in, text="№ счёта ПОСТ", anchor="w",
                 font=ctk.CTkFont(family="Segoe UI", size=12),
                 text_color=t["fg_secondary"]).pack(anchor="w", pady=(10, 2))
    entry_supplier_invoice = ctk.CTkEntry(inner_in, width=340, height=36,
                                          fg_color=t["bg"], border_color=t["border"], border_width=1,
                                          text_color=t["fg"],
                                          font=ctk.CTkFont(family="Segoe UI", size=13))
    entry_supplier_invoice.pack(fill="x")
    entry_supplier_invoice.insert(0, default_supplier_invoice)

    entry_positions.focus_set()

    # Кнопки — одинаковые по ширине, выровнены по сетке
    btn_frame = ctk.CTkFrame(root, fg_color="transparent")
    btn_frame.pack(fill="x", padx=24, pady=(16, 24))
    btn_frame.columnconfigure((0, 1), weight=1, uniform="btns")
    ctk.CTkButton(btn_frame, text="Отмена", height=40, command=on_cancel,
                  fg_color=t["card"], border_width=1, border_color=t["border"],
                  text_color=t["fg"], hover_color=t["card_hover"],
                  font=ctk.CTkFont(family="Segoe UI", size=13),
                  corner_radius=8).grid(row=0, column=0, sticky="ew", padx=(0, 6))
    ctk.CTkButton(btn_frame, text="OK", height=40, command=on_ok,
                  fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color="#ffffff",
                  font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                  corner_radius=8).grid(row=0, column=1, sticky="ew", padx=(6, 0))

    root.bind("<Return>", lambda e: on_ok())
    root.bind("<Escape>", lambda e: on_cancel())
    _center_ctk(root, 440, 480)
    root.mainloop()

    if not dialog_done or not result["input_text"]:
        return None

    parsed = parse_supplier_input(result["input_text"], remaining_positions)
    if isinstance(parsed, str):
        return parsed
    supplier, parsed_positions = parsed
    return supplier, parsed_positions, result["supplier_invoice"]


# ==========================================
# ОБРАБОТКА PDF
# ==========================================
def process_pdf(filepath):
    """
    Обрабатывает PDF-счёт: читает -> диалог -> распределение -> запись.
    """
    logger.info(f"Обнаружен новый файл: {filepath}")
    filename = os.path.basename(filepath)

    # ШАГ 1: Читаем PDF
    try:
        with pdfplumber.open(filepath) as pdf:
            text = pdf.pages[0].extract_text()
        if not text:
            raise ValueError("PDF не содержит текста. Возможно, это скан-копия.")
        text = text.replace("ё", "е").replace("Ё", "Е")
    except Exception as e:
        error_msg = f"Не удалось прочитать PDF '{filename}': {e}"
        logger.error(error_msg)
        show_notification("Ошибка чтения PDF", error_msg)
        return

    # ШАГ 2: Извлекаем номер и дату
    pdf_invoice, pdf_date = extract_invoice_from_pdf_text(text)
    file_invoice = "Неизвестно"
    if "№" in filename:
        start = filename.find("№") + 1
        end = filename.find(" от", start)
        if end == -1:
            end = len(filename) - 4
        file_invoice = filename[start:end].strip()
    file_date = extract_invoice_date(filename)

    invoice = pdf_invoice if pdf_invoice else file_invoice
    invoice_date = pdf_date if pdf_date else file_date

    if (pdf_invoice and file_invoice != "Неизвестно"
            and pdf_invoice != file_invoice):
        logger.warning(f"РАСХОЖДЕНИЕ: в PDF №{pdf_invoice}, в названии №{file_invoice}. "
                       f"Берём из PDF: №{invoice}")

    logger.info(f"Номер счёта: {invoice}, Дата: {invoice_date} "
                f"(PDF: {pdf_invoice}, файл: {file_invoice})")

    # ШАГ 3: Извлекаем данные из текста
    try:
        client, pdf_phone = parse_buyer_and_phone(text)

        if not client:
            raise ValueError("В PDF не найдено поле 'Покупатель'. Проверьте формат счёта.")

        start_qty = text.find("Всего наименований") + len("Всего наименований")
        if start_qty == len("Всего наименований") - 1:
            raise ValueError("В PDF не найдено 'Всего наименований'. Проверьте формат счёта.")
        end_qty = text.find(",", start_qty)
        qty = text[start_qty:end_qty].strip()
        qty_int = int(qty.strip())

    except ValueError as e:
        error_msg = f"Неправильный формат счёта '{filename}': {e}"
        logger.error(error_msg)
        show_notification("Неверный формат счёта", str(e))
        return
    except Exception as e:
        error_msg = f"Неожиданная ошибка при извлечении данных из '{filename}': {e}"
        logger.error(error_msg)
        show_notification("Ошибка обработки", error_msg)
        return

    logger.info(f"Клиент: {client}, Позиций: {qty_int}, Тел: {pdf_phone or 'нет'}")

    # Извлекаем сумму счёта (для расчёта бонуса дизайнера)
    invoice_amount = extract_invoice_amount(text)
    if invoice_amount:
        logger.info(f"Сумма счёта: {invoice_amount:.2f} руб.")

    # ШАГ 4: Окошко 1
    contacts = get_contacts_list()

    invoice_data = show_invoice_dialog(
        invoice, invoice_date, client, qty_int,
        default_manager="",
        contacts=contacts,
        default_phone=pdf_phone
    )
    if invoice_data is None:
        logger.info("Менеджер отменил ввод. Обработка прервана.")
        show_notification("Ввод отменён", f"Счёт №{invoice} не добавлен")
        return

    designer, manager, payment_form, phone, notify_date = invoice_data

    designer = check_and_offer_add(designer, "дизайнер", contacts.get("дизайнеры", []))
    manager = check_and_offer_add(manager, "менеджер", contacts.get("менеджеры", []))

    logger.info(f"Дизайнер: {designer}, Менеджер: {manager}, Оплата: {payment_form}, Телефон: {phone}")

    # ШАГ 5: Подключаемся к Google Sheets
    try:
        gc = gspread.service_account(filename=KEY_PATH)
        spreadsheet = gc.open_by_url(SHEET_URL)
        worksheet = spreadsheet.sheet1
    except FileNotFoundError:
        error_msg = ("Файл key.json не найден! "
                     f"Ожидался в: {DATA_DIR} или {APP_DIR}")
        logger.critical(error_msg)
        show_notification("КРИТИЧЕСКАЯ ОШИБКА", error_msg)
        return
    except gspread.exceptions.SpreadsheetNotFound:
        error_msg = "Нет доступа к Google Sheets. Проверьте ссылку и права key.json"
        logger.error(error_msg)
        show_notification("Нет доступа к таблице", error_msg)
        return
    except Exception as e:
        error_msg = f"Ошибка подключения к Google Sheets: {e}"
        logger.error(error_msg)
        show_notification("Нет связи с Google", "Проверьте интернет-подключение")
        return

    # ШАГ 6: Распределение позиций
    remaining = list(range(1, qty_int + 1))
    supplier_rows = []
    supplier_hint = ""
    remember_supplier_invoice = ""

    while remaining:
        result = show_supplier_dialog(remaining, invoice, supplier_hint, remember_supplier_invoice)

        if result is None:
            logger.info("Менеджер отменил распределение позиций.")
            show_notification("Ввод отменён", f"Счёт №{invoice} не добавлен")
            return

        if isinstance(result, str):
            show_notification("Ошибка ввода", result, duration=8)
            continue

        supplier, positions, supplier_invoice = result
        supplier_hint = supplier
        remember_supplier_invoice = supplier_invoice

        for p in positions:
            remaining.remove(p)

        positions_str = ",".join(str(p) for p in positions)
        supplier_rows.append((supplier, positions_str, supplier_invoice))
        supplier_hint = ""

        logger.info(f"Поставщик '{supplier}' - поз. {positions_str} - №{supplier_invoice or 'нет'} "
                    f"(осталось {len(remaining)})")

    # ШАГ 7: Запись в Google Sheets
    try:
        for supplier, positions_str, supplier_invoice in supplier_rows:
            # Столбцы A-Q (17 столбцов) — актуальная структура таблицы:
            # A: № счёта, B: Дата, C: Клиент, D: Телефон клиента, E: Дизайнер,
            # F: к-во поз. (тут же УВЕДОМЛЕНО после отправки ТГ),
            # G: Позиции ПОСТ, H: Поставщик, I: № счёта ПОСТ / дата,
            # J: Дата опл ПОСТ, K: Дата отгр клиенту, L: Отправка в тк,
            # M: Дата прихода ТК КЗН, N: Дата прихода СКЛАД,
            # O: Дополнительно, P: Менеджер, Q: Форма оплаты
            new_row = [
                invoice,            # A — № счёта
                invoice_date,       # B — Дата
                client,             # C — Клиент
                phone,              # D — Телефон клиента
                designer,           # E — Дизайнер
                qty_int,            # F — к-во поз.
                positions_str,      # G — Позиции ПОСТ
                supplier,           # H — Поставщик
                supplier_invoice,   # I — № счёта ПОСТ / дата
                "",                 # J — Дата опл ПОСТ
                "",                 # K — Дата отгр клиенту
                "",                 # L — Отправка в тк
                "",                 # M — Дата прихода ТК КЗН
                "",                 # N — Дата прихода СКЛАД
                (f"Клиент уведомлён: {notify_date}" if notify_date else ""),
                                   # O — Дополнительно (дата уведомления клиента)
                manager,            # P — Менеджер
                payment_form,       # Q — Форма оплаты
            ]
            worksheet.append_row(new_row)

        logger.info(f"Записано {len(supplier_rows)} строк в таблицу")

        # Объединяем ячейки (если >1 поставщика)
        if len(supplier_rows) > 1:
            all_data = worksheet.get_all_values()
            last_row = len(all_data)
            first_row = last_row - len(supplier_rows) + 1

            # Объединяем: №, дату, клиента, телефон, дизайнера, к-во, менеджера, оплату
            merge_cols = {1: "A", 2: "B", 3: "C", 4: "D", 5: "E", 6: "F", 16: "P", 17: "Q"}

            for col_num, letter in merge_cols.items():
                range_str = f"{letter}{first_row}:{letter}{last_row}"
                try:
                    worksheet.merge_cells(range_str)
                    logger.info(f"Объединены: {range_str}")
                except Exception as e:
                    logger.warning(f"Не удалось объединить {range_str}: {e}")

        # Полоса-разделитель (оранжевая) снизу всего счёта
        try:
            all_data = worksheet.get_all_values()
            last_row = len(all_data)

            border_format = {
                "borders": {
                    "bottom": {
                        "style": "SOLID",
                        "width": 2,
                        "color": {"red": 1.0, "green": 0.42, "blue": 0.21}
                    }
                }
            }

            worksheet.format(f"A{last_row}:Q{last_row}", border_format)
            logger.info(f"Полоса-разделитель добавлена на строку {last_row}")
        except Exception as e:
            logger.warning(f"Не удалось добавить полосу: {e}")

    except Exception as e:
        error_msg = f"Ошибка записи в таблицу: {e}"
        logger.error(error_msg)
        show_notification("Ошибка записи", error_msg)
        return

    # ШАГ 7.5: Запись в лист «Детализация» (бонусы дизайнеров)
    try:
        spreadsheet = gc.open_by_url(SHEET_URL)
        try:
            det_sheet = spreadsheet.worksheet("Детализация")
        except gspread.exceptions.WorksheetNotFound:
            det_sheet = None

        if det_sheet and designer and invoice_amount > 0:
            # СЧИТАЕМ САМИ (onEdit в Apps Script не сработает при записи через API)
            percent = get_designer_percent(designer, gc, invoice_date)
            bonus = round(invoice_amount * percent / 100, 2)

            # Срок выплаты = дата счёта + 7 дней
            from datetime import datetime, timedelta
            try:
                d_inv = datetime.strptime(invoice_date, "%d.%m.%Y")
                due_date = (d_inv + timedelta(days=7)).strftime("%d.%m.%Y")
            except Exception:
                due_date = ""

            det_row = [
                invoice,                 # A № счёта
                invoice_date,            # B Дата
                client,                  # C Клиент
                payment_form,            # D Форма оплаты
                designer,                # E Дизайнер
                invoice_amount,          # F Сумма счёта
                percent,                 # G % (5 или 10)
                bonus,                   # H Бонус (сумма * % / 100)
                due_date,                # I Срок выплаты
                "",                      # J Дата выплаты (вручную)
                "К выплате",             # K Статус
                "",                      # L Примечание
            ]
            det_sheet.append_row(det_row)
            logger.info(f"Детализация: №{invoice}, дизайнер {designer}, "
                        f"сумма {invoice_amount:.2f}, бонус {bonus:.2f} ({percent}%)")

            # ОТПРАВЛЯЕМ УВЕДОМЛЕНИЕ ДИЗАЙНЕРУ в Telegram
            try:
                send_designer_notification(
                    designer, invoice, bonus, percent, client, invoice_amount, gc)
            except Exception as e:
                logger.warning(f"Не удалось отправить ТГ дизайнеру: {e}")
        elif not designer:
            logger.info("Дизайнер не указан — пропуск записи в Детализацию")
        elif det_sheet and invoice_amount <= 0:
            logger.info("Сумма счёта не распознана — пропуск записи в Детализацию")
        else:
            logger.warning("Лист «Детализация» не найден — пропуск записи бонуса")
    except Exception as e:
        logger.warning(f"Не удалось записать в Детализацию: {e}")

    # ШАГ 8: Переименование файла
    try:
        base, ext = os.path.splitext(filepath)
        new_filepath = f"{base}_ОБРАБОТАНО{ext}"
        os.rename(filepath, new_filepath)
        logger.info(f"Файл переименован: {os.path.basename(new_filepath)}")
    except Exception as e:
        logger.error(f"Не удалось переименовать файл: {e}")

    show_notification(
        "Счёт обработан",
        f"Счёт №{invoice} — {client}\nДобавлено {len(supplier_rows)} поставщиков",
        duration=7
    )


# ==========================================
# СЛУШАТЕЛЬ ПАПКИ
# ==========================================
class PdfHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory or not event.src_path.endswith(".pdf"):
            return
        time.sleep(1)
        process_pdf(event.src_path)


# ==========================================
# ТРЕЙ: ЗНАЧОК В СИСТЕМНОМ ТРЕЕ (Win11-стиль)
# ==========================================
def _make_tray_image():
    """Современная иконка Win11-стиля: скруглённый квадрат с буквой А."""
    from PIL import Image, ImageDraw
    img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Win11-style squircle (скруглённый квадрат)
    draw.rounded_rectangle([4, 4, 60, 60], radius=16, fill=(255, 107, 53, 255))
    # Буква "А" белым, сегое-подобным начертанием
    draw.rounded_rectangle([22, 18, 42, 46], radius=3, fill=(255, 255, 255, 255))
    draw.rounded_rectangle([22, 18, 30, 46], radius=2, fill=(255, 107, 53, 255))
    return img


def create_tray_icon():
    """
    Значок в трее Win11-стиля с меню:
      - Открыть таблицу
      - Автозапуск [ВКЛ/ВЫКЛ]
      - Показать значок
      - Выход
    """
    import pystray

    img = _make_tray_image()
    autostart_enabled = [is_autostart_enabled()]

    def on_open_sheet(icon, item):
        import webbrowser
        webbrowser.open(SHEET_URL)

    def on_open_dashboard(icon, item):
        """Открывает окно дашборда (просмотр счетов) в отдельном потоке."""
        import threading
        def _run():
            try:
                import dashboard
                # Синхронизируем URL таблицы объекта с настройками дашборда
                dashboard.apply_deployment_settings()
                dash = dashboard.DashboardWindow(gspread, dashboard.SHEET_URL, KEY_PATH)
                dash.show()
            except Exception as e:
                logger.error(f"Ошибка дашборда: {e}")
                show_notification("Ошибка дашборда", str(e))
        # Дашборд в отдельном потоке, чтобы не блокировать трей
        threading.Thread(target=_run, daemon=True).start()

    def on_show_tooltip(icon, item):
        icon.notify(f"PDF-бот Аганим v{APP_VERSION} работает.\nКликните сюда для меню.", "Бот активен")

    def on_toggle_autostart(icon, item):
        new_state = not autostart_enabled[0]
        if set_autostart(new_state):
            autostart_enabled[0] = new_state
            icon.update_menu()
            status = "ВКЛЮЧЁН" if new_state else "ВЫКЛЮЧЕН"
            logger.info(f"Автозапуск {status}")
            show_notification("Автозапуск", f"Автозапуск при старте ПК {status.lower()}")
        else:
            show_notification("Ошибка", "Не удалось изменить автозапуск")

    def on_quit(icon, item):
        logger.info("Программа закрыта через значок в трее")
        icon.stop()
        import os
        os._exit(0)

    def get_menu():
        autostart_text = "Автозапуск  [ВКЛ]" if autostart_enabled[0] else "Автозапуск  [ВЫКЛ]"
        return pystray.Menu(
            pystray.MenuItem(f"PDF-бот Аганим v{APP_VERSION}", None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("📊  Открыть дашборд", on_open_dashboard),
            pystray.MenuItem("📋  Открыть таблицу", on_open_sheet),
            pystray.MenuItem(autostart_text, on_toggle_autostart),
            pystray.MenuItem("Показать уведомление", on_show_tooltip),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Выход", on_quit)
        )

    icon = pystray.Icon("pdf_bot", img, f"PDF-бот Аганим v{APP_VERSION}", get_menu())
    icon.visible = True  # явно показываем значок сразу
    return icon


def _tray_setup(icon):
    """
    Вызывается pystray после регистрации значка в трее.
    Гарантированно показывает значок + balloon (Windows вынуждена
    вытащить значок в видимую область при показе уведомления).
    """
    try:
        icon.visible = True
        import time as _time
        _time.sleep(0.8)
        # Двойная попытка показать balloon — иногда первая не срабатывает
        try:
            icon.notify(f"Программа запущена v{APP_VERSION}. Клик по значку — меню.",
                        f"PDF-бот Аганим v{APP_VERSION}")
        except Exception:
            pass
        # Повторно确保 видимость
        icon.visible = True
        icon.update_menu()
    except Exception as e:
        try:
            logger.warning(f"Tray setup: {e}")
        except Exception:
            pass


# ==========================================
# ПРИВЕТСТВЕННОЕ ОКНО (Win11)
# ==========================================
def show_welcome_screen():
    import webbrowser
    t = theme_colors()
    result = {"continue": False}

    def on_continue():
        result["continue"] = True
        root.destroy()

    def open_sheet():
        webbrowser.open(SHEET_URL)

    def open_instructions():
        webbrowser.open("https://docs.google.com/document/d/1dkYN-TVIqcA86mI10_yEcQwLTCitzZgHf1o6-9huCik/edit")

    root = ctk.CTk()
    root.title(f"PDF-бот Аганим v{APP_VERSION}")
    root.attributes("-topmost", True)
    root.resizable(False, False)
    root.configure(fg_color=t["bg"])

    header = ctk.CTkFrame(root, fg_color="transparent")
    header.pack(fill="x", padx=28, pady=(28, 4))
    ctk.CTkLabel(header, text="PDF-бот Аганим",
                 font=ctk.CTkFont(family="Segoe UI", size=26, weight="bold"),
                 text_color=t["fg"], anchor="w").pack(anchor="w")
    ctk.CTkLabel(header, text=f"Версия {APP_VERSION} • Автоматическое добавление счетов в таблицу",
                 font=ctk.CTkFont(family="Segoe UI", size=12),
                 text_color=t["fg_secondary"], anchor="w").pack(anchor="w", pady=(4, 0))

    # Ссылки
    links_card = ctk.CTkFrame(root, fg_color=t["card"], corner_radius=10,
                              border_width=1, border_color=t["border"])
    links_card.pack(fill="x", padx=28, pady=(20, 0))
    inner_l = ctk.CTkFrame(links_card, fg_color="transparent")
    inner_l.pack(fill="x", padx=18, pady=16)

    ctk.CTkLabel(inner_l, text="Полезные ссылки",
                 font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                 text_color=ACCENT, anchor="w").pack(anchor="w", pady=(0, 10))

    ctk.CTkButton(inner_l, text="  📊  Открыть Google Таблицу",
                  fg_color=t["card"], border_width=1, border_color=t["border"],
                  text_color=t["fg"], hover_color=t["card_hover"],
                  anchor="w", height=40,
                  font=ctk.CTkFont(family="Segoe UI", size=13),
                  command=open_sheet).pack(fill="x", pady=3)
    ctk.CTkButton(inner_l, text="  📖  Открыть инструкцию по работе",
                  fg_color=t["card"], border_width=1, border_color=t["border"],
                  text_color=t["fg"], hover_color=t["card_hover"],
                  anchor="w", height=40,
                  font=ctk.CTkFont(family="Segoe UI", size=13),
                  command=open_instructions).pack(fill="x", pady=3)

    ctk.CTkLabel(root, text="Не удаляйте и не перемещайте файл key.json — без него бот не работает!",
                 font=ctk.CTkFont(family="Segoe UI", size=11),
                 text_color=t["danger"],
                 wraplength=400, justify="center").pack(pady=(18, 14))

    ctk.CTkButton(root, text="Продолжить", width=200, height=42,
                  fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color="#ffffff",
                  font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                  command=on_continue).pack(pady=(0, 28))

    _center_ctk(root, 460, 420)
    root.mainloop()

    return result["continue"]


# ==========================================
# МАСТЕР ПЕРВИЧНОЙ НАСТРОЙКИ (новая таблица)
# ==========================================
def run_setup_wizard():
    """
    Показывается если нет settings.json. Предзаполнен встроенным URL —
    на текущем развёртывании достаточно нажать «Сохранить».
    Возвращает выбранный URL или "" (использовать встроенные).
    """
    t = theme_colors()
    result = {"url": ""}

    def on_save():
        url = entry_url.get().strip()
        if not url or "docs.google.com" not in url:
            from tkinter import messagebox
            messagebox.showwarning("Проверьте", "Нужен URL Google-таблицы\n(https://docs.google.com/...)", parent=root)
            return
        result["url"] = url
        root.destroy()

    def on_skip():
        result["url"] = ""
        root.destroy()

    root = ctk.CTk()
    root.title("Первичная настройка — PDF-бот Аганим")
    root.attributes("-topmost", True)
    root.resizable(False, False)
    root.configure(fg_color=t["bg"])

    body = ctk.CTkFrame(root, fg_color="transparent")
    body.pack(fill="both", expand=True, padx=28, pady=28)

    ctk.CTkLabel(body, text="⚙️ Первичная настройка",
                 font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
                 text_color=ACCENT, anchor="w").pack(anchor="w", pady=(0, 6))
    ctk.CTkLabel(body,
                 text="Укажите Google-таблицу, с которой работает программа.\n"
                      "key.json уже должен иметь доступ к этой таблице.",
                 font=ctk.CTkFont(family="Segoe UI", size=12),
                 text_color=t["fg_secondary"], anchor="w",
                 justify="left").pack(anchor="w", pady=(0, 14))

    ctk.CTkLabel(body, text="URL Google-таблицы", anchor="w",
                 font=ctk.CTkFont(family="Segoe UI", size=12),
                 text_color=t["fg_secondary"]).pack(anchor="w", pady=(4, 2))
    entry_url = ctk.CTkEntry(body, width=440, height=36,
                             fg_color=t["bg"], border_color=t["border"],
                             border_width=1, text_color=t["fg"],
                             font=ctk.CTkFont(family="Segoe UI", size=12))
    entry_url.pack(fill="x")
    entry_url.insert(0, DEFAULT_SHEET_URL)

    btns = ctk.CTkFrame(body, fg_color="transparent")
    btns.pack(fill="x", pady=(18, 0))
    btns.columnconfigure((0, 1), weight=1, uniform="s")
    ctk.CTkButton(btns, text="Встроенные настройки", height=38,
                  fg_color=t["card"], border_width=1, border_color=t["border"],
                  text_color=t["fg"], hover_color=t["card_hover"],
                  font=ctk.CTkFont(family="Segoe UI", size=12),
                  command=on_skip).grid(row=0, column=0, sticky="ew", padx=(0, 4))
    ctk.CTkButton(btns, text="Сохранить", height=38,
                  fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color="#ffffff",
                  font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                  command=on_save).grid(row=0, column=1, sticky="ew", padx=(4, 0))

    root.bind("<Escape>", lambda e: on_skip())
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    root.geometry(f"520x310+{(sw-520)//2}+{(sh-310)//2}")
    root.mainloop()
    return result["url"]


def apply_deployment_settings():
    """Настраивает SHEET_URL из settings.json; при первом запуске — мастер.
    Файловую логику выполняет модуль deployment (pathlib, проверка границ)."""
    global SHEET_URL
    import deployment

    if not deployment.is_configured():
        url = run_setup_wizard()
        chosen = url if url else deployment.DEFAULT_SHEET_URL
        if deployment.save_sheet_url(chosen):
            logger.info("Настройки развёртывания сохранены"
                        + ("" if url else " (встроенная таблица)"))
        else:
            logger.warning("Не удалось сохранить settings.json — "
                           "используется встроенная таблица")

    sheet_url = deployment.load_sheet_url()
    if sheet_url:
        SHEET_URL = sheet_url


# ==========================================
# MAIN
# ==========================================
def main():
    # Первичная настройка (новая таблица объекта) — до всего остального
    apply_deployment_settings()

    import deployment as _dep
    folder_path = str(_dep.load_config().get("folder_path", ""))

    if not folder_path or not os.path.exists(folder_path):
        show_welcome_screen()
        logger.info("Первый запуск! Выбор папки для счетов...")
        root = ctk.CTk()
        root.withdraw()
        from tkinter import filedialog
        folder_path = filedialog.askdirectory(title="Выберите папку для счетов")

        if not folder_path:
            logger.info("Папка не выбрана. Программа закрыта.")
            return

        if _dep.save_config({"folder_path": folder_path}):
            logger.info(f"Папка сохранена: {folder_path}")
        else:
            logger.warning("Не удалось сохранить config.json")

    # Включаем автозапуск при первом запуске
    if not is_autostart_enabled():
        set_autostart(True)

    logger.info("==================================================")
    logger.info(f"БОТ v{APP_VERSION} ЗАПУЩЕН И СЛУШАЕТ ПАПКУ...")
    logger.info(f"Папка: {folder_path}")
    logger.info("==================================================")

    event_handler = PdfHandler()
    observer = Observer()
    observer.schedule(event_handler, folder_path, recursive=False)
    observer.start()

    show_notification(f"Бот v{APP_VERSION} запущен", "Слушаю папку. Трей — для управления.")

    logger.info("Значок в трее активен. Для выхода — кликнуть по значку → Выход.")
    icon = create_tray_icon()
    icon.run(setup=_tray_setup)

    observer.stop()
    observer.join()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.critical(f"КРИТИЧЕСКАЯ ОШИБКА: {e}", exc_info=True)
        show_notification("Бот не запустился", f"Ошибка: {e}")
