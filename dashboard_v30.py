# -*- coding: utf-8 -*-
"""
Дашборд PDF-бота Аганим — окно просмотра и управления счетами.
Стиль: Windows 11 (customtkinter), как в 1С, но удобнее.

Возможности:
  - Просмотр всех счетов (список + детали)
  - Редактирование данных (запись в Google Sheets)
  - Добавление счёта вручную (без PDF)
  - Экспорт в Excel
"""
import os
import threading
import datetime
import customtkinter as ctk
from tkinter import ttk, messagebox

# Структура таблицы (17 колонок) — должна совпадать с apps_script.gs
COL_INVOICE    = 0   # A — № счёта
COL_DATE       = 1   # B — Дата
COL_CLIENT     = 2   # C — Клиент
COL_PHONE      = 3   # D — Телефон
COL_DESIGNER   = 4   # E — Дизайнер
COL_QTY        = 5   # F — к-во поз. / УВЕДОМЛЕНО
COL_POSITIONS  = 6   # G — Позиции ПОСТ
COL_SUPPLIER   = 7   # H — Поставщик
COL_SUP_INV    = 8   # I — № счёта ПОСТ
COL_PAY_DATE   = 9   # J — Дата опл ПОСТ
COL_SHIP_DATE  = 10  # K — Дата отгр клиенту
COL_TK_SEND    = 11  # L — Отправка в тк
COL_TK_ARRIVAL = 12  # M — ТК КЗН
COL_WAREHOUSE  = 13  # N — СКЛАД
COL_EXTRA      = 14  # O — Доп
COL_MANAGER    = 15  # P — Менеджер
COL_PAYMENT    = 16  # Q — Форма оплаты

TOTAL_COLS = 17

ACCENT = "#FF6B35"
ACCENT_HOVER = "#FF8A5C"
DASH_VERSION = "3.5"

# Telegram-бот (для уведомлений когда все позиции счёта пришли)
BOT_TOKEN = "7690342745:AAEh5i7YihlNwYzmvDPb_rBWom_IZsYnemE"

# Человекопонятные названия колонок (для UI)
COL_LABELS = {
    COL_INVOICE: "№ счёта",
    COL_DATE: "Дата счёта",
    COL_CLIENT: "Клиент",
    COL_PHONE: "Телефон",
    COL_DESIGNER: "Дизайнер",
    COL_QTY: "Кол-во поз.",
    COL_POSITIONS: "Позиции ПОСТ",
    COL_SUPPLIER: "Поставщик",
    COL_SUP_INV: "№ счёта ПОСТ",
    COL_PAY_DATE: "Дата опл ПОСТ",
    COL_SHIP_DATE: "Дата отгрузки",
    COL_TK_SEND: "Отправка в ТК",
    COL_TK_ARRIVAL: "Приход ТК КЗН",
    COL_WAREHOUSE: "Приход СКЛАД",
    COL_EXTRA: "Дополнительно",
    COL_MANAGER: "Менеджер",
    COL_PAYMENT: "Форма оплаты",
}

# Настройки развёртывания (новая таблица объекта).
# settings.json создаёт бот при первом запуске (мастер); дашборд
# при самостоятельном запуске тоже может показать мастер.
import os as _os_mod
import json as _json_mod
import deployment as _deployment_mod

# В тестовой сборке (dev) вшита таблица владельца; в релизной — пусто
# (таблицу настраивает бот при первом запуске, см. main()).
SHEET_URL = _deployment_mod.DEFAULT_SHEET_URL
DEFAULT_SHEET_URL = _deployment_mod.DEFAULT_SHEET_URL


def _deployment_settings_path():
    """settings.json в %APPDATA%\\PDF-bot-Aganim (нормализованный путь)."""
    root = _os_mod.realpath(_os_mod.environ.get("APPDATA") or _os_mod.expanduser("~"))
    d = _os_mod.realpath(_os_mod.join(root, "PDF-bot-Aganim"))
    if d != root and not d.startswith(root + _os_mod.sep):
        d = root
    return _os_mod.join(d, "settings.json")


def load_deployment_settings():
    """Читает settings.json (URL таблицы текущего объекта)."""
    try:
        with open(_deployment_settings_path(), "r", encoding="utf-8") as f:
            data = _json_mod.load(f)
            if isinstance(data, dict) and data.get("sheet_url"):
                return str(data["sheet_url"])
    except Exception:
        pass
    return ""


def apply_deployment_settings():
    """Подменяет глобальную SHEET_URL на URL из settings.json (если задан).
    Вызывается из main() и __init__ DashboardWindow."""
    global SHEET_URL
    global DASH_VERSION
    if _deployment_mod.IS_DEV_BUILD and "(тест)" not in DASH_VERSION:
        DASH_VERSION = DASH_VERSION + " (тест)"
    url = load_deployment_settings()
    if url and "docs.google.com" in url:
        SHEET_URL = url


def _colors():
    import darkdetect
    try:
        dark = darkdetect.theme() == "Dark"
    except Exception:
        dark = False
    return {
        "dark": dark,
        "bg": "#1f1f1f" if dark else "#f3f3f3",
        "card": "#2b2b2b" if dark else "#ffffff",
        "card_alt": "#333333" if dark else "#fafafa",
        "fg": "#ffffff" if dark else "#1f1f1f",
        "fg_secondary": "#cccccc" if dark else "#5b5b5b",
        "fg_dim": "#9a9a9a" if dark else "#8a8a8a",
        "border": "#3a3a3a" if dark else "#e5e5e5",
        "success": "#7ec68c" if dark else "#2e8a45",
        "success_bg": "#1e3a26" if dark else "#dcedc8",
        "warning": "#e0af68" if dark else "#b8860b",
        "danger": "#f8889b" if dark else "#c4243a",
        # «Отгружено клиенту» — плотный серый, но не тёмный
        "shipped": "#9a9a9a" if dark else "#6b6b6b",
        "shipped_bg": "#3a3a3a" if dark else "#c8c8ce",
    }


# ==========================================
# РАБОТА С GOOGLE SHEETS
# ==========================================
def _get_sheet(gspread_module, key_file="key.json"):
    """Подключение к таблице. Возвращает объект worksheet."""
    gc = gspread_module.service_account(filename=key_file)
    ss = gc.open_by_url(SHEET_URL)
    return ss.sheet1


def load_invoices(gspread_module, key_file="key.json"):
    """
    Читает все счета из Google Sheets и группирует по № счёта.
    """
    ws = _get_sheet(gspread_module, key_file)
    data = ws.get_all_values()
    if len(data) <= 1:
        return [], ws

    invoices = []
    current = None
    for row_idx, row in enumerate(data[1:], start=2):  # start=2 т.к. 1 = заголовок
        while len(row) < TOTAL_COLS:
            row.append("")

        inv_num = str(row[COL_INVOICE]).strip()
        if inv_num:
            current = {
                "invoice": inv_num,
                "date": str(row[COL_DATE]).strip(),
                "client": str(row[COL_CLIENT]).strip(),
                "phone": str(row[COL_PHONE]).strip(),
                "designer": str(row[COL_DESIGNER]).strip(),
                "qty": str(row[COL_QTY]).strip(),
                "manager": str(row[COL_MANAGER]).strip(),
                "payment": str(row[COL_PAYMENT]).strip(),
                "positions": [],
                "row_start": row_idx,   # первая строка счёта в таблице
            }
            invoices.append(current)

        if current is None:
            continue

        current["row_end"] = row_idx  # последняя строка счёта

        pos = {
            "row": row_idx,  # номер строки для редактирования
            "positions": str(row[COL_POSITIONS]).strip(),
            "supplier": str(row[COL_SUPPLIER]).strip(),
            "sup_inv": str(row[COL_SUP_INV]).strip(),
            "pay_date": str(row[COL_PAY_DATE]).strip(),
            "ship_date": str(row[COL_SHIP_DATE]).strip(),
            "tk_send": str(row[COL_TK_SEND]).strip(),
            "tk_arrival": str(row[COL_TK_ARRIVAL]).strip(),
            "warehouse": str(row[COL_WAREHOUSE]).strip(),
            "extra": str(row[COL_EXTRA]).strip(),
        }
        if (pos["positions"] or pos["supplier"] or pos["sup_inv"] or
            pos["pay_date"] or pos["ship_date"] or pos["tk_arrival"] or
            pos["warehouse"]):
            current["positions"].append(pos)

    for inv in invoices:
        qty_raw = inv.get("qty", "")
        inv["notified"] = "УВЕДОМЛЕНО" in qty_raw.upper()
        inv["shipped"] = any(p["ship_date"] for p in inv["positions"])

    return invoices, ws


def update_cell(gspread_module, row, col, value, key_file="key.json"):
    """Записывает значение в ячейку. col = 0-indexed."""
    try:
        ws = _get_sheet(gspread_module, key_file)
        # gspread update_cell(row, col) — оба 1-indexed
        ws.update_cell(row, col + 1, value)
        return True
    except Exception as e:
        print(f"Ошибка записи в ячейку R{row}C{col}: {e}")
        return False


def color_invoice_rows(gspread_module, row_start, row_end, bg_color, key_file="key.json"):
    """Красит строки счёта (с row_start по row_end) в указанный цвет фона.
    bg_color = hex вида '#RRGGBB' или 'RRGGBB'.
    ВАЖНО: API-запрос НЕ вызывает onEdit в Apps Script, поэтому красим напрямую."""
    try:
        ws = _get_sheet(gspread_module, key_file)
        # gspread format() принимает hex без решётки
        hex_clean = bg_color.lstrip("#")
        cell_format = {"backgroundColor": {"red": 0, "green": 0, "blue": 0}}
        # Перевод hex → RGB float
        r = int(hex_clean[0:2], 16) / 255.0
        g = int(hex_clean[2:4], 16) / 255.0
        b = int(hex_clean[4:6], 16) / 255.0
        cell_format = {
            "backgroundColor": {"red": r, "green": g, "blue": b}
        }
        # Диапазон A{start}:Q{end} (17 колонок)
        from gspread.utils import rowcol_to_a1
        rng = f"{rowcol_to_a1(row_start, 1)}:{rowcol_to_a1(row_end, TOTAL_COLS)}"
        ws.format(rng, cell_format)
        return True
    except Exception as e:
        print(f"Ошибка покраски строк {row_start}-{row_end}: {e}")
        return False


def get_test_chat_id(gspread_module, key_file="key.json"):
    """Читает тестовый chat_id из вкладки «Настройки» (ячейка B1)."""
    try:
        gc = gspread_module.service_account(filename=key_file)
        ss = gc.open_by_url(SHEET_URL)
        st = ss.worksheet("Настройки")
        val = str(st.get("B1")[0][0] if st.get("B1") else "").strip()
        return val or "438544636"
    except Exception:
        return "438544636"


# URL развёрнутого веб-приложения Apps Script (для отправки ТГ через Google).
# Заполняется при первом запуске. Хранится в «Настройки»!B2.
_APPS_SCRIPT_URL_CACHE = None


def get_apps_script_url(gspread_module, key_file="key.json"):
    """Читает URL веб-приложения Apps Script из вкладки «Настройки» (B2)."""
    global _APPS_SCRIPT_URL_CACHE
    if _APPS_SCRIPT_URL_CACHE:
        return _APPS_SCRIPT_URL_CACHE
    try:
        gc = gspread_module.service_account(filename=key_file)
        ss = gc.open_by_url(SHEET_URL)
        st = ss.worksheet("Настройки")
        val = st.get("B2")
        url = str(val[0][0] if val else "").strip()
        if url and "script.google.com" in url:
            _APPS_SCRIPT_URL_CACHE = url
            return url
    except Exception:
        pass
    return ""


def notify_via_apps_script(gspread_module, invoice, message, key_file="key.json"):
    """Отправляет ТГ-уведомление ЧЕРЕЗ Google Apps Script (минуя блокировку).
    Сетевая часть и валидация URL — в deployment.call_apps_script."""
    import deployment as _dep
    url = get_apps_script_url(gspread_module, key_file)
    if not url or not _dep.is_valid_apps_script_url(url):
        print("URL Apps Script не задан/невалиден — ТГ не отправлен. "
              "Нужен https://script.google.com/... в «Настройки»!B2.")
        return False
    body = _dep.call_apps_script(url, {
        "action": "notifyArrival",
        "invoice": str(invoice),
    })
    if not body:
        print("Запрос к Apps Script не выполнен (валидация/сеть)")
        return False
    print(f"Apps Script ответ: {body[:200]}")
    return "ok" in body.lower()


def check_and_notify_arrival(gspread_module, invoice_data, key_file="key.json"):
    """
    Проверяет: если у ВСЕХ позиций счёта заполнено M (ТК КЗН) ИЛИ N (СКЛАД) —
    значит товар пришёл. Тогда:
      1. Красит все строки счёта в зелёный
      2. Ставит «N — УВЕДОМЛЕНО» в столбец F
      3. Отправляет уведомление в Telegram (рабочий чат + менеджер/дизайнер/клиент)
    Возвращает True если уведомление отправлено.
    """
    try:
        positions = invoice_data.get("positions", [])
        if not positions:
            return False

        # Проверяем: у КАЖДОЙ позиции есть хотя бы одно из M/N
        all_arrived = all(p.get("tk_arrival") or p.get("warehouse") for p in positions)
        if not all_arrived:
            return False

        # Перезагружаем данные счёта из таблицы (чтобы актуальные значения)
        gc = gspread_module.service_account(filename=key_file)
        ss = gc.open_by_url(SHEET_URL)
        ws = ss.sheet1
        row_start = invoice_data.get("row_start", 2)
        row_end = invoice_data.get("row_end", row_start)
        # Читаем весь блок строк счёта
        block = ws.get(f"M{row_start}:N{row_end}")
        # Проверяем по свежим данным
        fresh_all = all((r[0] if len(r) > 0 else "") or (r[1] if len(r) > 1 else "")
                        for r in block)
        if not fresh_all:
            return False

        # 1. Проверяем: не уведомлено ли уже (читаем F)
        f_val = str(ws.get(f"F{row_start}")[0][0] if ws.get(f"F{row_start}") else "")
        if "УВЕДОМЛЕНО" in f_val.upper():
            return False  # уже уведомлено — не дублируем

        # 2. КРАСИМ строки в зелёный
        from gspread.utils import rowcol_to_a1
        green_hex = "C8E6C9"
        cell_fmt = {
            "backgroundColor": {
                "red": int(green_hex[0:2], 16) / 255,
                "green": int(green_hex[2:4], 16) / 255,
                "blue": int(green_hex[4:6], 16) / 255,
            }
        }
        rng = f"{rowcol_to_a1(row_start, 1)}:{rowcol_to_a1(row_end, TOTAL_COLS)}"
        ws.format(rng, cell_fmt)

        # 3. СТАВИМ «N — УВЕДОМЛЕНО» в F
        qty_str = str(invoice_data.get("qty", "")).strip()
        # Вытаскиваем число из «7 — УВЕДОМЛЕНО» или просто «7»
        import re
        m = re.match(r"(\d+)", qty_str)
        qty_num = m.group(1) if m else qty_str
        new_f = f"{qty_num} — УВЕДОМЛЕНО" if qty_num else "УВЕДОМЛЕНО"
        ws.update_cell(row_start, COL_QTY + 1, new_f)

        # 4. ОТПРАВЛЯЕМ TELEGRAM
        # Собираем состав
        composition = ""
        for p in positions:
            tk = p.get("tk_arrival", "")
            wh = p.get("warehouse", "")
            if tk and wh:
                loc = "Склад + ТК"
            elif wh:
                loc = "Склад"
            elif tk:
                loc = "ТК"
            else:
                loc = "—"
            composition += (f"• поз. {p.get('positions','?')} — "
                            f"{p.get('supplier','?')} ({loc})\n")

        client = invoice_data.get("client", "—")
        designer = invoice_data.get("designer", "") or "не указан"
        manager = invoice_data.get("manager", "") or "не указан"
        invoice = invoice_data.get("invoice", "?")

        message = (
            f"📦 Счёт №{invoice} — все позиции пришли\n"
            f"👤 Клиент: {client}\n"
            f"🎨 Дизайнер: {designer}\n"
            f"👷 Менеджер: {manager}\n"
            f"📋 Состав по позициям:\n{composition}"
        )

        # ОТПРАВКА ЧЕРЕЗ GOOGLE APPS SCRIPT (т.к. api.telegram.org
        # заблокирован на ПК). Apps Script работает на серверах Google,
        # оттуда Telegram доступен.
        # Нужно вызвать URL веб-приложения: ?action=notifyArrival&invoice=NNN
        # URL веб-приложения хранится в config.json (deploy_url), если нет —
        # отправляем через "текст" напрямую (резерв).
        notify_via_apps_script(gspread_module, invoice, message, key_file)

        return True
    except Exception as e:
        print(f"Ошибка check_and_notify_arrival: {e}")
        return False


def add_invoice_row(gspread_module, row_data, key_file="key.json"):
    """Добавляет новую строку счёта в конец таблицы."""
    try:
        ws = _get_sheet(gspread_module, key_file)
        # добиваем до 17 колонок
        while len(row_data) < TOTAL_COLS:
            row_data.append("")
        ws.append_row(row_data)
        return True
    except Exception as e:
        print(f"Ошибка добавления строки: {e}")
        return False


# ==========================================
# ДИЗАЙНЕРЫ: работа с листами «Детализация»/«Сводка»
# ==========================================
def _get_detail_sheet(gspread_module, key_file="key.json"):
    """Возвращает лист «Детализация»."""
    gc = gspread_module.service_account(filename=key_file)
    ss = gc.open_by_url(SHEET_URL)
    return ss.worksheet("Детализация")


def load_designers(gspread_module, key_file="key.json"):
    """
    Читает «Детализацию» и группирует по дизайнерам.
    Возвращает (list, raw_rows):
      list = [{name, count, sum_all, bonus_all, paid, debt, percent, invoices: [...]}, ...]
      raw_rows = все строки детализации
    """
    try:
        det = _get_detail_sheet(gspread_module, key_file)
        data = det.get_all_values()
        if len(data) <= 1:
            return [], []
    except Exception as e:
        print(f"Ошибка чтения Детализации: {e}")
        return [], []

    # Колонки: A=№ B=Дата C=Клиент D=Оплата E=Дизайнер F=Сумма G=% H=Бонус
    #          I=Срок J=Дата выпл K=Статус L=Прим
    raw = []
    agg = {}
    order = []
    for row in data[1:]:
        while len(row) < 12:
            row.append("")
        rec = {
            "invoice": row[0], "date": row[1], "client": row[2],
            "payment": row[3], "designer": row[4],
            "sum_raw": row[5], "percent": row[6], "bonus": row[7],
            "due": row[8], "paid_date": row[9], "status": row[10], "note": row[11],
            "row": len(raw) + 2,  # номер строки в таблице (1=заголовок)
        }
        raw.append(rec)

        name = rec["designer"].strip()
        if not name:
            continue
        if name not in agg:
            agg[name] = {
                "name": name,
                "count": 0, "sum_all": 0.0, "bonus_all": 0.0,
                "paid": 0.0, "invoices": [],
            }
            order.append(name)
        a = agg[name]
        try:
            s = float(str(rec["sum_raw"]).replace(" ", "").replace(",", ".").replace("\xa0", "")) if rec["sum_raw"] else 0
        except ValueError:
            s = 0
        try:
            b = float(str(rec["bonus"]).replace(" ", "").replace(",", ".")) if rec["bonus"] else 0
        except ValueError:
            b = 0
        a["count"] += 1
        a["sum_all"] += s
        a["bonus_all"] += b
        if rec["paid_date"]:
            a["paid"] += b
        a["invoices"].append(rec)

    # Долг + процент (10% если сумма >= 500000, иначе 5%) + ожидаемая дата
    from datetime import datetime as _dt
    result = []
    for name in order:
        a = agg[name]
        a["debt"] = a["bonus_all"] - a["paid"]
        a["percent"] = 10 if a["sum_all"] >= 500000 else 5
        # Ожидаемая дата: ближайший срок выплаты из невыплаченных счетов
        due_dates = []
        for inv in a["invoices"]:
            try:
                bonus = float(str(inv.get("bonus", "")).replace(",", ".")) if inv.get("bonus") else 0
            except (ValueError, TypeError):
                bonus = 0
            if bonus > 0 and not inv.get("paid_date") and inv.get("due"):
                try:
                    d = _dt.strptime(str(inv["due"]).strip()[:10], "%d.%m.%Y")
                    due_dates.append(d)
                except ValueError:
                    pass
        a["next_due"] = min(due_dates).strftime("%d.%m.%Y") if due_dates else ""
        result.append(a)

    return result, raw


def update_detail_cell(gspread_module, row, col, value, key_file="key.json"):
    """Запись в ячейку листа «Детализация». col = 0-indexed (A=0)."""
    try:
        det = _get_detail_sheet(gspread_module, key_file)
        det.update_cell(row, col + 1, value)
        return True
    except Exception as e:
        print(f"Ошибка записи в Детализацию R{row}C{col}: {e}")
        return False


# ==========================================
# КАЛЕНДАРЬ: работа с листом «Календарь»
# ==========================================
def _get_calendar_sheet(gspread_module, key_file="key.json"):
    """Возвращает лист «Календарь»."""
    gc = gspread_module.service_account(filename=key_file)
    ss = gc.open_by_url(SHEET_URL)
    return ss.worksheet("Календарь")


def load_calendar_events(gspread_module, key_file="key.json"):
    """Читает все события из листа «Календарь».
    Возвращает список dict: {row, date, time, text, type, done, note}."""
    try:
        cal = _get_calendar_sheet(gspread_module, key_file)
        data = cal.get_all_values()
        if len(data) <= 1:
            return []
        events = []
        for i, row in enumerate(data[1:], start=2):
            while len(row) < 7:
                row.append("")
            if not str(row[0]).strip() and not str(row[2]).strip():
                continue
            events.append({
                "row": i,
                "date": str(row[0]).strip(),
                "time": str(row[1]).strip(),
                "text": str(row[2]).strip(),
                "type": str(row[3]).strip() or "ручное",
                "done": str(row[4]).strip(),
                "note": str(row[5]).strip(),
            })
        return events
    except Exception as e:
        print(f"Ошибка чтения Календаря: {e}")
        return []


def add_calendar_event(gspread_module, date_str, time_str, text,
                       note="", key_file="key.json"):
    """Добавляет событие в лист «Календарь»."""
    try:
        cal = _get_calendar_sheet(gspread_module, key_file)
        import datetime as _dt
        created = _dt.datetime.now().strftime("%d.%m.%Y %H:%M")
        cal.append_row([date_str, time_str, text, "ручное", "", note, created])
        return True
    except Exception as e:
        print(f"Ошибка добавления события: {e}")
        return False


def update_calendar_cell(gspread_module, row, col, value, key_file="key.json"):
    """Обновляет ячейку события. col = 0-indexed (A=0)."""
    try:
        cal = _get_calendar_sheet(gspread_module, key_file)
        cal.update_cell(row, col + 1, value)
        return True
    except Exception as e:
        print(f"Ошибка обновления события R{row}: {e}")
        return False


def delete_calendar_event(gspread_module, row, key_file="key.json"):
    """Очищает строку события (сохраняет нумерацию строк)."""
    try:
        cal = _get_calendar_sheet(gspread_module, key_file)
        cal.update(values=[["", "", "", "", "", "", ""]],
                   range_name=f"A{row}:G{row}")
        return True
    except Exception as e:
        print(f"Ошибка удаления события R{row}: {e}")
        return False


def load_calendar_settings(gspread_module, key_file="key.json"):
    """Читает настройки календаря из листа «Настройки».
    B10 = интервал проверки (мин), B11 = на сколько дней вперёд напоминать."""
    default = {"interval_min": 60, "lookahead_days": 1}
    try:
        gc = gspread_module.service_account(filename=key_file)
        ss = gc.open_by_url(SHEET_URL)
        st = ss.worksheet("Настройки")
        vals = st.get("B10:B11")
        if vals and vals[0] and vals[0][0]:
            v = int(str(vals[0][0]).strip())
            if 0 < v <= 1440:
                default["interval_min"] = v
        if len(vals) > 1 and vals[1] and vals[1][0]:
            v = int(str(vals[1][0]).strip())
            if 0 < v <= 30:
                default["lookahead_days"] = v
    except Exception:
        pass
    return default


def save_calendar_settings(gspread_module, settings, key_file="key.json"):
    """Сохраняет настройки календаря в «Настройки» (B10, B11)."""
    try:
        gc = gspread_module.service_account(filename=key_file)
        ss = gc.open_by_url(SHEET_URL)
        st = ss.worksheet("Настройки")
        st.update(values=[[int(settings["interval_min"])],
                          [int(settings["lookahead_days"])]],
                  range_name="B10:B11")
        # Подписи в A10/A11 если пусто
        labels = st.get("A10:A11")
        if not labels or not labels[0] or not str(labels[0][0]).strip():
            st.update(values=[["Календарь: интервал проверки, мин"],
                              ["Календарь: напоминать за N дней"]],
                      range_name="A10:A11")
        return True
    except Exception as e:
        print(f"Ошибка сохранения настроек календаря: {e}")
        return False


def export_to_excel(invoices, filepath):
    """Экспортирует счета в Excel файл."""
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment

        wb = Workbook()
        ws = wb.active
        ws.title = "Счета"

        # Заголовки
        headers = [COL_LABELS[i] for i in range(TOTAL_COLS)]
        ws.append(headers)
        for cell in ws[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="FF6B35")
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

        # Данные
        for inv in invoices:
            for pos in inv["positions"]:
                row = [
                    inv["invoice"], inv["date"], inv["client"], inv["phone"],
                    inv["designer"], inv["qty"],
                    pos["positions"], pos["supplier"], pos["sup_inv"],
                    pos["pay_date"], pos["ship_date"], pos["tk_send"],
                    pos["tk_arrival"], pos["warehouse"], pos["extra"],
                    inv["manager"], inv["payment"],
                ]
                ws.append(row)

        # Автоширина
        for col_idx, col_cells in enumerate(ws.iter_cols(min_row=1, max_row=ws.max_row), 1):
            max_len = max((len(str(c.value or "")) for c in col_cells), default=10)
            ws.column_dimensions[col_cells[0].column_letter].width = min(max_len + 2, 35)

        wb.save(filepath)
        return True
    except Exception as e:
        print(f"Ошибка экспорта: {e}")
        return False


# ==========================================
# ДИАЛОГ РЕДАКТИРОВАНИЯ
# ==========================================
class EditDialog(ctk.CTkToplevel):
    """Диалог редактирования одного поля."""

    def __init__(self, parent, title, current_value, field_label, t_colors):
        super().__init__(parent)
        self.t = t_colors
        self.result = None

        self.title(title)
        self.transient(parent)
        self.grab_set()
        self.configure(fg_color=self.t["bg"])
        self.resizable(False, False)
        self.attributes("-topmost", True)

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=24, pady=24)

        ctk.CTkLabel(body, text=field_label,
                     font=ctk.CTkFont(family="Segoe UI", size=12),
                     text_color=self.t["fg_secondary"], anchor="w").pack(anchor="w", pady=(0, 6))

        self.entry = ctk.CTkEntry(body, width=360, height=36,
                                  fg_color=self.t["bg"], border_color=self.t["border"],
                                  border_width=1, text_color=self.t["fg"],
                                  font=ctk.CTkFont(family="Segoe UI", size=13))
        self.entry.pack(fill="x")
        self.entry.insert(0, str(current_value))
        self.entry.focus_set()

        btns = ctk.CTkFrame(body, fg_color="transparent")
        btns.pack(fill="x", pady=(16, 0))
        btns.columnconfigure((0, 1), weight=1, uniform="b")
        ctk.CTkButton(btns, text="Отмена", height=38,
                      fg_color=self.t["card"], border_width=1, border_color=self.t["border"],
                      text_color=self.t["fg"], hover_color=self.t["card_alt"],
                      font=ctk.CTkFont(family="Segoe UI", size=13),
                      command=self._cancel).grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ctk.CTkButton(btns, text="Сохранить", height=38,
                      fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color="#ffffff",
                      font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                      command=self._save).grid(row=0, column=1, sticky="ew", padx=(4, 0))

        self.bind("<Return>", lambda e: self._save())
        self.bind("<Escape>", lambda e: self._cancel())

        self.after(100, lambda: self._center(420, 180))

    def _center(self, w, h):
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw // 2) - (w // 2)
        y = (sh // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _save(self):
        self.result = self.entry.get().strip()
        self.destroy()

    def _cancel(self):
        self.result = None
        self.destroy()


# ==========================================
# ДИАЛОГ НОВОГО СЧЁТА
# ==========================================
class NewInvoiceDialog(ctk.CTkToplevel):
    """Диалог ручного добавления счёта."""

    def __init__(self, parent, t_colors):
        super().__init__(parent)
        self.t = t_colors
        self.result = None

        self.title("Новый счёт")
        self.transient(parent)
        self.grab_set()
        self.configure(fg_color=self.t["bg"])
        self.resizable(False, False)
        self.attributes("-topmost", True)

        body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=24, pady=24)

        ctk.CTkLabel(body, text="➕ Новый счёт (ручной ввод)",
                     font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
                     text_color=ACCENT, anchor="w").pack(anchor="w", pady=(0, 16))

        # Поля шапки счёта
        self.entries = {}
        header_fields = [
            ("invoice", "№ счёта *"),
            ("date", "Дата (ДД.ММ.ГГГГ)"),
            ("client", "Клиент *"),
            ("phone", "Телефон"),
            ("designer", "Дизайнер"),
            ("manager", "Менеджер"),
            ("payment", "Форма оплаты"),
        ]
        for key, label in header_fields:
            ctk.CTkLabel(body, text=label, anchor="w",
                         font=ctk.CTkFont(family="Segoe UI", size=12),
                         text_color=self.t["fg_secondary"]).pack(anchor="w", pady=(8, 2))
            e = ctk.CTkEntry(body, width=380, height=34,
                             fg_color=self.t["bg"], border_color=self.t["border"],
                             border_width=1, text_color=self.t["fg"],
                             font=ctk.CTkFont(family="Segoe UI", size=13))
            e.pack(fill="x")
            self.entries[key] = e

        # Поля позиции поставщика
        ctk.CTkLabel(body, text="📦 Позиция поставщика",
                     font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                     text_color=ACCENT, anchor="w").pack(anchor="w", pady=(16, 4))

        pos_fields = [
            ("positions", "Позиции (1,2,3)"),
            ("supplier", "Поставщик"),
            ("sup_inv", "№ счёта ПОСТ"),
        ]
        for key, label in pos_fields:
            ctk.CTkLabel(body, text=label, anchor="w",
                         font=ctk.CTkFont(family="Segoe UI", size=12),
                         text_color=self.t["fg_secondary"]).pack(anchor="w", pady=(6, 2))
            e = ctk.CTkEntry(body, width=380, height=34,
                             fg_color=self.t["bg"], border_color=self.t["border"],
                             border_width=1, text_color=self.t["fg"],
                             font=ctk.CTkFont(family="Segoe UI", size=13))
            e.pack(fill="x")
            self.entries[key] = e

        # Кнопки
        btns = ctk.CTkFrame(body, fg_color="transparent")
        btns.pack(fill="x", pady=(20, 0))
        btns.columnconfigure((0, 1), weight=1, uniform="b")
        ctk.CTkButton(btns, text="Отмена", height=40,
                      fg_color=self.t["card"], border_width=1, border_color=self.t["border"],
                      text_color=self.t["fg"], hover_color=self.t["card_alt"],
                      font=ctk.CTkFont(family="Segoe UI", size=13),
                      command=self._cancel).grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ctk.CTkButton(btns, text="Добавить", height=40,
                      fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color="#ffffff",
                      font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                      command=self._save).grid(row=0, column=1, sticky="ew", padx=(4, 0))

        self.bind("<Escape>", lambda e: self._cancel())

        self.entries["invoice"].focus_set()
        self.after(100, lambda: self._center(460, 640))

    def _center(self, w, h):
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw // 2) - (w // 2)
        y = (sh // 2) - (h // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _save(self):
        inv = self.entries["invoice"].get().strip()
        client = self.entries["client"].get().strip()
        if not inv or not client:
            messagebox.showwarning("Проверьте данные",
                                   "Поля «№ счёта» и «Клиент» обязательны.",
                                   parent=self)
            return
        self.result = {k: e.get().strip() for k, e in self.entries.items()}
        self.destroy()

    def _cancel(self):
        self.result = None
        self.destroy()


# ==========================================
# ГЛАВНОЕ ОКНО ДАШБОРДА
# ==========================================
class DashboardWindow:
    """Главное окно дашборда."""

    def __init__(self, gspread_module, sheet_url=None, key_file="key.json", on_close=None):
        self.gspread = gspread_module
        self.key_file = key_file
        self.on_close = on_close
        self.invoices = []
        self.filtered = []
        self.designers = []
        self.designers_raw = []
        self.ws = None
        self.t = _colors()
        self.current_tab = "invoices"  # "invoices" или "designers"

        self.root = ctk.CTk()
        self.root.title(f"PDF-бот Аганим — Управление v{DASH_VERSION}")
        self.root.geometry("1280x750")
        self.root.minsize(1000, 600)
        self.root.configure(fg_color=self.t["bg"])

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(100, self.refresh_async)

    def _build_ui(self):
        t = self.t

        # ===== ПАНЕЛЬ ВКЛАДОК СВЕРХУ =====
        tab_bar = ctk.CTkFrame(self.root, fg_color=t["bg"], corner_radius=0, height=48)
        tab_bar.pack(fill="x", side="top")
        tab_bar.pack_propagate(False)

        # Вкладка «Счета»
        self.tab_invoices_btn = ctk.CTkButton(
            tab_bar, text="📊  Счета", width=140, height=36,
            fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color="#ffffff",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            command=lambda: self._switch_tab("invoices"))
        self.tab_invoices_btn.pack(side="left", padx=(16, 4), pady=6)

        # Вкладка «Дизайнеры»
        self.tab_designers_btn = ctk.CTkButton(
            tab_bar, text="🎨  Дизайнеры", width=150, height=36,
            fg_color=t["card"], border_width=1, border_color=t["border"],
            text_color=t["fg_secondary"], hover_color=t["card_alt"],
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            command=lambda: self._switch_tab("designers"))
        self.tab_designers_btn.pack(side="left", padx=4, pady=6)

        # Вкладка «Календарь»
        self.tab_calendar_btn = ctk.CTkButton(
            tab_bar, text="📅  Календарь", width=150, height=36,
            fg_color=t["card"], border_width=1, border_color=t["border"],
            text_color=t["fg_secondary"], hover_color=t["card_alt"],
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            command=lambda: self._switch_tab("calendar"))
        self.tab_calendar_btn.pack(side="left", padx=4, pady=6)

        # ===== КОНТЕЙНЕР ДЛЯ ВКЛАДОК =====
        self.tab_container = ctk.CTkFrame(self.root, fg_color="transparent")
        self.tab_container.pack(fill="both", expand=True)

        # Вкладка счетов (строим сразу, она активная)
        self.invoices_tab = ctk.CTkFrame(self.tab_container, fg_color="transparent")
        self.invoices_tab.pack(fill="both", expand=True)
        self._build_invoices_tab(self.invoices_tab)

        # Вкладка дизайнеров (создаём пустую, заполним при переключении)
        self.designers_tab = ctk.CTkFrame(self.tab_container, fg_color="transparent")

        # Вкладка календаря (создаём пустую, заполним при переключении)
        self.calendar_tab = ctk.CTkFrame(self.tab_container, fg_color="transparent")

    def _switch_tab(self, tab):
        """Переключение между вкладками."""
        t = self.t
        self.current_tab = tab
        # Прячем все
        self.invoices_tab.pack_forget()
        self.designers_tab.pack_forget()
        self.calendar_tab.pack_forget()
        # Сбрасываем стиль всех кнопок
        for btn in (self.tab_invoices_btn, self.tab_designers_btn,
                    self.tab_calendar_btn):
            btn.configure(fg_color=t["card"], text_color=t["fg_secondary"],
                          border_width=1)
        if tab == "invoices":
            self.invoices_tab.pack(fill="both", expand=True)
            self.tab_invoices_btn.configure(fg_color=ACCENT, text_color="#ffffff",
                                            border_width=0)
        elif tab == "designers":
            self.designers_tab.pack(fill="both", expand=True)
            self.tab_designers_btn.configure(fg_color=ACCENT, text_color="#ffffff",
                                             border_width=0)
            if not hasattr(self, "_designers_built"):
                self._build_designers_tab(self.designers_tab)
                self._designers_built = True
            self.refresh_designers_async()
        else:  # calendar
            self.calendar_tab.pack(fill="both", expand=True)
            self.tab_calendar_btn.configure(fg_color=ACCENT, text_color="#ffffff",
                                            border_width=0)
            if not hasattr(self, "_calendar_built"):
                self._build_calendar_tab(self.calendar_tab)
                self._calendar_built = True
            self.refresh_calendar_async()

    def _build_invoices_tab(self, parent):
        """Содержимое вкладки «Счета» (всё что было раньше)."""
        t = self.t

        # ===== ШАПКА =====
        header = ctk.CTkFrame(parent, fg_color=t["card"], corner_radius=0, height=64)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        ctk.CTkLabel(header, text="📊  Счета",
                     font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
                     text_color=t["fg"]).pack(side="left", padx=(20, 0), pady=12)

        # Кнопка Новый счёт
        ctk.CTkButton(header, text="➕ Новый счёт", width=130, height=36,
                      fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color="#ffffff",
                      font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                      command=self._new_invoice).pack(side="left", padx=20, pady=12)

        # Экспорт
        ctk.CTkButton(header, text="📄 Excel", width=90, height=36,
                      fg_color=t["card"], border_width=1, border_color=t["border"],
                      text_color=t["fg"], hover_color=t["card_alt"],
                      font=ctk.CTkFont(family="Segoe UI", size=12),
                      command=self._export_excel).pack(side="right", padx=(8, 20), pady=12)

        # Обновить
        self.btn_refresh = ctk.CTkButton(header, text="🔄 Обновить", width=110, height=36,
                                         fg_color=t["card"], border_width=1, border_color=t["border"],
                                         text_color=t["fg"], hover_color=t["card_alt"],
                                         font=ctk.CTkFont(family="Segoe UI", size=12),
                                         command=self.refresh_async)
        self.btn_refresh.pack(side="right", padx=(8, 0), pady=12)

        # Поиск
        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", lambda *a: self._apply_filter())
        search = ctk.CTkEntry(header, textvariable=self.search_var,
                              width=300, height=36,
                              placeholder_text="🔍  Поиск: №, клиент, дизайнер, менеджер...",
                              fg_color=t["bg"], border_color=t["border"], border_width=1,
                              text_color=t["fg"],
                              font=ctk.CTkFont(family="Segoe UI", size=12))
        search.pack(side="right", padx=(0, 8), pady=12)

        # ===== ТЕЛО (PanedWindow — перетаскиваемый разделитель) =====
        import tkinter as tk
        body = ctk.CTkFrame(parent, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=16, pady=16)

        self.paned = tk.PanedWindow(body, orient="horizontal",
                                    sashwidth=6, sashrelief="flat",
                                    bg=t["border"], borderwidth=0,
                                    sashpad=0)
        self.paned.pack(fill="both", expand=True)

        # --- ЛЕВАЯ ПАНЕЛЬ: список ---
        left = ctk.CTkFrame(self.paned, fg_color=t["card"], corner_radius=10)
        left.columnconfigure(0, weight=1)
        left.rowconfigure(0, weight=1)

        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("Dash.Treeview",
                        background=t["bg"], foreground=t["fg"],
                        fieldbackground=t["bg"], borderwidth=0,
                        font=("Segoe UI", 11), rowheight=44)
        style.configure("Dash.Treeview.Heading",
                        background=t["card_alt"], foreground=t["fg_secondary"],
                        font=("Segoe UI", 11, "bold"), borderwidth=0)
        style.map("Dash.Treeview",
                  background=[("selected", ACCENT)],
                  foreground=[("selected", "#ffffff")])

        tree_frame = ctk.CTkFrame(left, fg_color="transparent")
        tree_frame.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(tree_frame,
                                 columns=("invoice", "client", "date", "manager"),
                                 show="headings", selectmode="browse",
                                 style="Dash.Treeview")
        # Заголовки с сортировкой по клику (command вызывает _sort_by)
        self._sort_state = {"col": "date", "reverse": True}  # по умолчанию: дата, новые сверху
        self.tree.heading("invoice", text="№ счёта", command=lambda: self._sort_by("invoice"))
        self.tree.heading("client", text="Клиент", command=lambda: self._sort_by("client"))
        self.tree.heading("date", text="Дата", command=lambda: self._sort_by("date"))
        self.tree.heading("manager", text="Менеджер", command=lambda: self._sort_by("manager"))
        self.tree.column("invoice", width=70, anchor="center")
        self.tree.column("client", width=240, anchor="w")
        self.tree.column("date", width=90, anchor="center")
        self.tree.column("manager", width=120, anchor="w")
        self.tree.grid(row=0, column=0, sticky="nsew")

        self.tree.tag_configure("notified", background=t["success_bg"], foreground=t["success"])
        # Отгружено — плотный серый фон (не тёмный)
        self.tree.tag_configure("shipped", background=t["shipped_bg"], foreground=t["shipped"])
        self.tree.tag_configure("normal", background=t["card"])

        vsb = ctk.CTkScrollbar(tree_frame, command=self.tree.yview)
        vsb.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=vsb.set)
        # Одиночный клик — показать детали справа
        self.tree.bind("<<TreeviewSelect>>", lambda e: self._show_details())

        # --- ПРАВАЯ ПАНЕЛЬ: детали ---
        # Оборачиваем в обычный CTkFrame-контейнер (CTkScrollableFrame не любит PanedWindow)
        right_wrap = ctk.CTkFrame(self.paned, fg_color="transparent")
        right_wrap.rowconfigure(0, weight=1)
        right_wrap.columnconfigure(0, weight=1)

        self.right = ctk.CTkScrollableFrame(right_wrap, fg_color=t["card"], corner_radius=10,
                                            label_text="Выберите счёт слева")
        self.right.grid(row=0, column=0, sticky="nsew")

        # Добавляем обе панели в PanedWindow с минимальными размерами
        self.paned.add(left, minsize=300, stretch="always")
        self.paned.add(right_wrap, minsize=400, stretch="always")

        # После отрисовки — стартовая пропорция (левая ≈ 40%)
        def _set_sash():
            try:
                self.root.update_idletasks()
                total = self.paned.winfo_width()
                if total > 100:
                    self.paned.sash_place(0, int(total * 0.40), 0)
            except Exception:
                pass
        self.root.after(200, _set_sash)

    # ==========================================
    # ВКЛАДКА «ДИЗАЙНЕРЫ»
    # ==========================================
    def _build_designers_tab(self, parent):
        """Строит содержимое вкладки «Дизайнеры»."""
        t = self.t

        # Шапка
        header = ctk.CTkFrame(parent, fg_color=t["card"], corner_radius=0, height=64)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        ctk.CTkLabel(header, text="🎨  Дизайнеры",
                     font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
                     text_color=t["fg"]).pack(side="left", padx=(20, 0), pady=12)

        # Обновить дизайнеров
        self.btn_refresh_d = ctk.CTkButton(
            header, text="🔄 Обновить", width=110, height=36,
            fg_color=t["card"], border_width=1, border_color=t["border"],
            text_color=t["fg"], hover_color=t["card_alt"],
            font=ctk.CTkFont(family="Segoe UI", size=12),
            command=self.refresh_designers_async)
        self.btn_refresh_d.pack(side="right", padx=(8, 20), pady=12)

        # Экспорт дизайнеров
        ctk.CTkButton(
            header, text="📄 Excel", width=90, height=36,
            fg_color=t["card"], border_width=1, border_color=t["border"],
            text_color=t["fg"], hover_color=t["card_alt"],
            font=ctk.CTkFont(family="Segoe UI", size=12),
            command=self._export_designers_excel).pack(side="right", padx=(8, 0), pady=12)

        # Поиск по имени дизайнера
        self.search_d_var = ctk.StringVar()
        self.search_d_var.trace_add("write", lambda *a: self._apply_designers_filter())
        search_d = ctk.CTkEntry(header, textvariable=self.search_d_var,
                                width=240, height=36,
                                placeholder_text="🔍  Поиск по имени...",
                                fg_color=t["bg"], border_color=t["border"], border_width=1,
                                text_color=t["fg"],
                                font=ctk.CTkFont(family="Segoe UI", size=12))
        search_d.pack(side="right", padx=(0, 8), pady=12)

        # Тело: PanedWindow (список дизайнеров + детали)
        import tkinter as tk
        body = ctk.CTkFrame(parent, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=16, pady=16)

        self.paned_d = tk.PanedWindow(body, orient="horizontal",
                                      sashwidth=6, sashrelief="flat",
                                      bg=t["border"], borderwidth=0, sashpad=0)
        self.paned_d.pack(fill="both", expand=True)

        # --- ЛЕВАЯ ПАНЕЛЬ: список дизайнеров ---
        left = ctk.CTkFrame(self.paned_d, fg_color=t["card"], corner_radius=10)
        left.columnconfigure(0, weight=1)
        left.rowconfigure(0, weight=1)

        style = ttk.Style()
        style.configure("Des.Treeview",
                        background=t["bg"], foreground=t["fg"],
                        fieldbackground=t["bg"], borderwidth=0,
                        font=("Segoe UI", 11), rowheight=52)
        style.configure("Des.Treeview.Heading",
                        background=t["card_alt"], foreground=t["fg_secondary"],
                        font=("Segoe UI", 11, "bold"), borderwidth=0)
        style.map("Des.Treeview",
                  background=[("selected", ACCENT)],
                  foreground=[("selected", "#ffffff")])

        tree_frame = ctk.CTkFrame(left, fg_color="transparent")
        tree_frame.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        self.tree_d = ttk.Treeview(tree_frame,
                                   columns=("name", "count", "sum_all", "debt"),
                                   show="headings", selectmode="browse",
                                   style="Des.Treeview")
        self.tree_d.heading("name", text="Дизайнер")
        self.tree_d.heading("count", text="Счетов")
        self.tree_d.heading("sum_all", text="Сумма, ₽")
        self.tree_d.heading("debt", text="Бонус, ₽")
        self.tree_d.column("name", width=220, anchor="w")
        self.tree_d.column("count", width=70, anchor="center")
        self.tree_d.column("sum_all", width=120, anchor="e")
        self.tree_d.column("debt", width=120, anchor="e")
        self.tree_d.grid(row=0, column=0, sticky="nsew")

        self.tree_d.tag_configure("high", background=t["success_bg"], foreground=t["success"])
        self.tree_d.tag_configure("normal", background=t["card"])
        self.tree_d.tag_configure("debt", background=t["shipped_bg"], foreground=t["shipped"])

        vsb_d = ctk.CTkScrollbar(tree_frame, command=self.tree_d.yview)
        vsb_d.grid(row=0, column=1, sticky="ns")
        self.tree_d.configure(yscrollcommand=vsb_d.set)
        self.tree_d.bind("<<TreeviewSelect>>", lambda e: self._show_designer_details())

        # --- ПРАВАЯ ПАНЕЛЬ: детали дизайнера ---
        self.right_d_wrap = ctk.CTkFrame(self.paned_d, fg_color="transparent")
        self.right_d_wrap.rowconfigure(0, weight=1)
        self.right_d_wrap.columnconfigure(0, weight=1)
        self.right_d = ctk.CTkScrollableFrame(self.right_d_wrap, fg_color=t["card"],
                                              corner_radius=10,
                                              label_text="Выберите дизайнера")
        self.right_d.grid(row=0, column=0, sticky="nsew")

        self.paned_d.add(left, minsize=350, stretch="always")
        self.paned_d.add(self.right_d_wrap, minsize=400, stretch="always")

        def _set_sash_d():
            try:
                self.root.update_idletasks()
                total = self.paned_d.winfo_width()
                if total > 100:
                    self.paned_d.sash_place(0, int(total * 0.42), 0)
            except Exception:
                pass
        self.root.after(200, _set_sash_d)

    def refresh_designers_async(self):
        """Загрузка данных дизайнеров в фоне."""
        if hasattr(self, "btn_refresh_d"):
            self.btn_refresh_d.configure(state="disabled", text="🔄 Загрузка...")
        threading.Thread(target=self._load_designers_thread, daemon=True).start()

    def _load_designers_thread(self):
        try:
            designers, raw = load_designers(self.gspread, self.key_file)
            self.designers = designers
            self.designers_raw = raw
            self.root.after(0, lambda: self._after_designers_load(True, None))
        except Exception as e:
            err = str(e)
            self.root.after(0, lambda: self._after_designers_load(False, err))

    def _after_designers_load(self, ok, error):
        if hasattr(self, "btn_refresh_d"):
            self.btn_refresh_d.configure(state="normal", text="🔄 Обновить")
        if not ok:
            self._toast("❌ Ошибка", f"Не удалось загрузить дизайнеров: {error}")
            return
        self._populate_designers_tree()

    def _populate_designers_tree(self):
        """Заполняет список дизайнеров (с учётом фильтра поиска)."""
        for item in self.tree_d.get_children():
            self.tree_d.delete(item)

        # Фильтр по поиску
        q = self.search_d_var.get().strip().lower() if hasattr(self, "search_d_var") else ""
        if q:
            filtered = [d for d in self.designers if q in d["name"].lower()]
        else:
            filtered = list(self.designers)

        # Сортировка: больше долга — выше
        sorted_d = sorted(filtered, key=lambda d: d["debt"], reverse=True)

        for d in sorted_d:
            if d["percent"] == 10:
                tag = "high"
            elif d["debt"] > 0:
                tag = "debt"
            else:
                tag = "normal"
            # iid = имя (для выбора)
            safe_iid = f"d_{abs(hash(d['name']))}"
            d["_iid"] = safe_iid
            self.tree_d.insert("", "end", iid=safe_iid,
                               values=(d["name"], d["count"],
                                       f"{d['sum_all']:,.0f}".replace(",", " "),
                                       f"{d['debt']:,.0f}".replace(",", " ")),
                               tags=(tag,))
        self.right_d.configure(label_text=f"Дизайнеров: {len(sorted_d)}")
        if sorted_d:
            try:
                self.tree_d.selection_set(sorted_d[0]["_iid"])
                self.tree_d.focus(sorted_d[0]["_iid"])
            except Exception:
                pass
            self._show_designer_details()
        else:
            # Очищаем правую панель
            for w in self.right_d.winfo_children():
                w.destroy()

    def _apply_designers_filter(self):
        """Применяет фильтр поиска по дизайнерам (без перезагрузки данных)."""
        if hasattr(self, "tree_d"):
            self._populate_designers_tree()

    def _show_designer_details(self):
        """Показывает детали выбранного дизайнера."""
        sel = self.tree_d.selection()
        if not sel:
            return
        iid = sel[0]
        designer = None
        for d in self.designers:
            if d.get("_iid") == iid:
                designer = d
                break
        if not designer:
            return

        t = self.t
        # Очищаем правую панель
        for w in self.right_d.winfo_children():
            w.destroy()

        # Шапка дизайнера
        header_card = ctk.CTkFrame(self.right_d, fg_color=t["card_alt"], corner_radius=8)
        header_card.pack(fill="x", pady=(0, 12))
        inner = ctk.CTkFrame(header_card, fg_color="transparent")
        inner.pack(fill="x", padx=14, pady=12)

        title_row = ctk.CTkFrame(inner, fg_color="transparent")
        title_row.pack(fill="x")
        ctk.CTkLabel(title_row, text=designer["name"],
                     font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
                     text_color=t["fg"]).pack(side="left")

        # Таблетка процента
        pct_color = t["success"] if designer["percent"] == 10 else t["shipped"]
        pill = ctk.CTkFrame(title_row, fg_color=pct_color, corner_radius=14, height=28)
        pill.pack(side="right", padx=(8, 0), pady=4)
        ctk.CTkLabel(pill, text=f"{designer['percent']}% бонус",
                     font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                     text_color="#ffffff").pack(padx=12, pady=3)

        # Сводка
        grid = ctk.CTkFrame(inner, fg_color="transparent")
        grid.pack(fill="x", pady=(8, 0))
        grid.columnconfigure(1, weight=1)
        rows = [
            ("Всего счетов", str(designer["count"])),
            ("Сумма счетов", f"{designer['sum_all']:,.2f} ₽".replace(",", " ")),
            ("Бонус начислено", f"{designer['bonus_all']:,.2f} ₽".replace(",", " ")),
            ("Выплачено", f"{designer['paid']:,.2f} ₽".replace(",", " ")),
            ("Бонус к выплате", f"{designer['debt']:,.2f} ₽".replace(",", " ")),
            ("Ожидаемая дата", designer.get("next_due", "") or "—"),
        ]
        for i, (lbl, val) in enumerate(rows):
            if lbl == "Бонус к выплате" and designer["debt"] > 0:
                color = t["warning"]
            elif lbl == "Ожидаемая дата" and designer.get("next_due"):
                color = t["fg"]
            else:
                color = t["fg_secondary"]
            ctk.CTkLabel(grid, text=lbl, width=140, anchor="w",
                         font=ctk.CTkFont(family="Segoe UI", size=12),
                         text_color=t["fg_secondary"]).grid(row=i, column=0, sticky="w", pady=1)
            ctk.CTkLabel(grid, text=val, anchor="w",
                         font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                         text_color=color).grid(row=i, column=1, sticky="w", pady=1)

        # Правило прогресса к 10%
        remaining = max(0, 500000 - designer["sum_all"])
        progress = min(100, designer["sum_all"] / 500000 * 100)
        ctk.CTkLabel(inner, text=f"Прогресс к ставке 10%: {progress:.0f}% "
                     f"(осталось {remaining:,.0f} ₽)".replace(",", " "),
                     font=ctk.CTkFont(family="Segoe UI", size=11),
                     text_color=t["fg_dim"], anchor="w").pack(anchor="w", pady=(8, 0))
        progress_bar = ctk.CTkProgressBar(inner, progress_color=ACCENT, height=12)
        progress_bar.pack(fill="x", pady=(4, 0))
        progress_bar.set(progress / 100)

        # Кнопка «Отправить дизайнеру» — генерирует текст для копирования
        ctk.CTkButton(inner, text="📨 Отправить дизайнеру", height=40,
                      fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color="#ffffff",
                      font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                      corner_radius=8,
                      command=lambda _d=designer: self._show_designer_message(_d)
                      ).pack(fill="x", pady=(12, 0))

        # Список счетов дизайнера
        ctk.CTkLabel(self.right_d, text="📋 Счета дизайнера",
                     font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                     text_color=ACCENT, anchor="w").pack(anchor="w", pady=(8, 6))

        for inv in designer["invoices"]:
            self._make_designer_invoice_card(inv)

    def _build_designer_message(self, designer):
        """Формирует грамотный текст сообщения дизайнеру о бонусах."""
        # Собираем невыплаченные счета с бонусом
        pending = []
        for inv in designer.get("invoices", []):
            try:
                bonus = float(str(inv.get("bonus", "")).replace(",", ".")) if inv.get("bonus") else 0
            except (ValueError, TypeError):
                bonus = 0
            if bonus > 0 and not inv.get("paid_date"):
                pending.append(inv)

        name = designer["name"]
        greeting = f"Добрый день, {name}!"

        if not pending:
            return (f"{greeting}\n\n"
                    f"На текущий момент невыплаченных бонусов нет — всё получено. "
                    f"Спасибо за сотрудничество!\n\nС уважением, Аганим")

        if len(pending) == 1:
            inv = pending[0]
            try:
                bonus = float(str(inv.get("bonus", "0")).replace(",", "."))
            except (ValueError, TypeError):
                bonus = 0.0
            bonus_str = f"{bonus:,.2f}".replace(",", " ").rstrip("0").rstrip(".")
            client = inv.get("client", "") or "клиента"
            invoice_num = inv.get("invoice", "")
            due = inv.get("due", "") or ""
            lines = [
                greeting,
                "",
                f"По заказу клиента {client} (счёт №{invoice_num}) "
                f"начислен бонус в размере {bonus_str} ₽.",
            ]
            if due:
                lines.append(f"Вы можете забрать его в нашем салоне после {due}.")
            else:
                lines.append("Вы можете забрать его в нашем салоне.")
            lines += ["", "Спасибо за сотрудничество!", "", "С уважением, Аганим"]
            return "\n".join(lines)

        # Несколько счетов — сводное сообщение
        total_bonus = 0.0
        details = []
        for inv in pending:
            try:
                bonus = float(str(inv.get("bonus", "0")).replace(",", "."))
            except (ValueError, TypeError):
                bonus = 0.0
            total_bonus += bonus
            bonus_s = f"{bonus:,.2f}".replace(",", " ").rstrip("0").rstrip(".")
            details.append(f"• счёт №{inv.get('invoice', '?')} "
                           f"(клиент {inv.get('client', '') or '—'}) — {bonus_s} ₽")
        total_str = f"{total_bonus:,.2f}".replace(",", " ").rstrip("0").rstrip(".")
        due = designer.get("next_due", "")
        lines = [
            greeting,
            "",
            "По вашим заказам начислены бонусы:",
            *details,
            "",
            f"Итого к выплате: {total_str} ₽.",
        ]
        if due:
            lines.append(f"Вы можете забрать их в нашем салоне после {due}.")
        else:
            lines.append("Вы можете забрать их в нашем салоне.")
        lines += ["", "Спасибо за сотрудничество!", "", "С уважением, Аганим"]
        return "\n".join(lines)

    def _show_designer_message(self, designer):
        """Показывает внизу панели текст сообщения + кнопку «Копировать»."""
        t = self.t
        # Удаляем предыдущее сообщение если было
        if hasattr(self, "_msg_frame") and self._msg_frame.winfo_exists():
            self._msg_frame.destroy()

        text = self._build_designer_message(designer)

        self._msg_frame = ctk.CTkFrame(self.right_d, fg_color=t["card_alt"],
                                       corner_radius=8, border_width=2,
                                       border_color=ACCENT)
        inner = ctk.CTkFrame(self._msg_frame, fg_color="transparent")
        inner.pack(fill="x", padx=12, pady=10)

        # Заголовок + кнопка копировать
        head = ctk.CTkFrame(inner, fg_color="transparent")
        head.pack(fill="x")
        ctk.CTkLabel(head, text="📨 Сообщение дизайнеру (скопируйте и отправьте)",
                     font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                     text_color=ACCENT, anchor="w").pack(side="left")

        def copy_msg():
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self._toast("📋 Скопировано", "Текст в буфере обмена")

        ctk.CTkButton(head, text="📋 Копировать", width=110, height=30,
                      fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color="#ffffff",
                      font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                      command=copy_msg).pack(side="right")

        # Текст сообщения
        txt = ctk.CTkTextbox(inner, height=170,
                             fg_color=t["bg"], border_width=1,
                             border_color=t["border"],
                             text_color=t["fg"], wrap="word",
                             font=ctk.CTkFont(family="Segoe UI", size=12))
        txt.pack(fill="x", pady=(8, 0))
        txt.insert("1.0", text)
        txt.configure(state="disabled")

        # Скроллим к сообщению
        self._msg_frame.pack(fill="x", pady=(12, 0))
        self.right_d.after(200, lambda: self._msg_frame.update_idletasks())

    def _make_designer_invoice_card(self, inv):
        """Карточка одного счёта в списке дизайнера.
        Полностью защищена от любых типов данных (число/строка/None/Date)."""
        t = self.t
        # БЕЗОПАСНОЕ извлечение всех полей — приводим к строке
        def s(v):
            """Безопасно в строку."""
            if v is None:
                return ""
            if isinstance(v, float):
                # 7747.0 → "7747", 7747.5 → "7747.5"
                return f"{v:g}"
            return str(v).strip()

        try:
            invoice_num = s(inv.get("invoice"))
            client_str = s(inv.get("client"))[:25]
            date_str = s(inv.get("date"))
            sum_str = s(inv.get("sum_raw"))
            due_str = s(inv.get("due"))
            paid_str = s(inv.get("paid_date"))

            # Бонус — безопасно в число
            try:
                bonus_val = float(s(inv.get("bonus")).replace(",", ".")) if inv.get("bonus") else 0
            except (ValueError, TypeError):
                bonus_val = 0
        except Exception as e:
            # Если что-то совсем сломалось — рисуем простую карточку с кнопкой
            print(f"Ошибка данных счёта: {e}")
            invoice_num = "?"
            client_str = "Ошибка данных"
            date_str = sum_str = due_str = paid_str = ""
            bonus_val = 0

        card = ctk.CTkFrame(self.right_d, fg_color=t["card_alt"], corner_radius=6,
                            border_width=1, border_color=t["border"])
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=12, pady=8)

        # Верх: № + клиент + бонус
        top = ctk.CTkFrame(inner, fg_color="transparent")
        top.pack(fill="x")
        ctk.CTkLabel(top, text=f"№{invoice_num}",
                     font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                     text_color=t["fg"], width=80, anchor="w").pack(side="left")
        if client_str:
            ctk.CTkLabel(top, text=client_str,
                         font=ctk.CTkFont(family="Segoe UI", size=12),
                         text_color=t["fg_secondary"], anchor="w").pack(side="left", padx=(4, 0))

        # Бонус справа
        bonus_color = t["success"] if paid_str else (t["warning"] if bonus_val > 0 else t["fg_dim"])
        bonus_text = f"+{bonus_val:g} ₽" if bonus_val > 0 else "—"
        ctk.CTkLabel(top, text=bonus_text,
                     font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                     text_color=bonus_color, anchor="e").pack(side="right")

        # Детали
        det = ctk.CTkFrame(inner, fg_color="transparent")
        det.pack(fill="x", pady=(4, 0))
        det.columnconfigure(1, weight=1)
        info = [
            ("Дата", date_str),
            ("Сумма", (sum_str + " ₽") if sum_str else ""),
            ("Срок выплаты", due_str),
            ("Выплачено", paid_str),
        ]
        for i, (lbl, val) in enumerate(info):
            if not val:
                continue
            ctk.CTkLabel(det, text=lbl, width=100, anchor="w",
                         font=ctk.CTkFont(family="Segoe UI", size=11),
                         text_color=t["fg_dim"]).grid(row=i, column=0, sticky="w")
            ctk.CTkLabel(det, text=val, anchor="w",
                         font=ctk.CTkFont(family="Segoe UI", size=11),
                         text_color=t["fg_secondary"]).grid(row=i, column=1, sticky="w")

        # Кнопки действий — ВСЕГДА видимы (кнопка Редактировать рисуется безусловно)
        btns = ctk.CTkFrame(inner, fg_color="transparent")
        btns.pack(fill="x", pady=(10, 0))

        ctk.CTkButton(btns, text="✏️ Редактировать", width=160, height=40,
                      fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color="#ffffff",
                      font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                      corner_radius=8,
                      command=lambda _inv=inv: self._edit_designer_invoice(_inv)
                      ).pack(side="left", padx=(0, 6))

        # Кнопка «Отметить выплаченным» — только если есть бонус и не выплачено
        if bonus_val > 0 and not paid_str:
            def mark_paid(_inv=inv):
                self._mark_designer_paid(_inv)
            ctk.CTkButton(btns, text="✓ Выплачено", width=140, height=40,
                          fg_color=t["success"], hover_color=t["fg_dim"], text_color="#ffffff",
                          font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                          corner_radius=8,
                          command=mark_paid).pack(side="left")

        return card

    def _mark_designer_paid(self, inv):
        """Отмечает счёт дизайнера как выплаченный."""
        from tkinter import messagebox
        answer = messagebox.askyesno(
            "Подтверждение",
            f"Отметить счёт №{inv['invoice']} ({inv['bonus']} ₽) как выплаченный дизайнеру?",
            parent=self.root)
        if not answer:
            return
        today = datetime.datetime.now().strftime("%d.%m.%Y")
        threading.Thread(
            target=self._mark_paid_thread,
            args=(inv, today), daemon=True).start()

    def _edit_designer_invoice(self, inv):
        """Редактирование любого поля счёта в Детализации.
        Колонки (0-indexed): A=0 №, B=1 Дата, C=2 Клиент, D=3 Оплата,
        E=4 Дизайнер, F=5 Сумма, G=6 %, H=7 Бонус, I=8 Срок, J=9 Выплата,
        K=10 Статус, L=11 Примечание.
        """
        from tkinter import messagebox
        t = self.t

        # Список редактируемых полей: (key, col_0idx, label)
        fields = [
            ("invoice",   0,  "№ счёта"),
            ("date",      1,  "Дата счёта"),
            ("client",    2,  "Клиент"),
            ("payment",   3,  "Форма оплаты"),
            ("designer",  4,  "Дизайнер"),
            ("sum_raw",   5,  "Сумма счёта"),
            ("percent",   6,  "% (5 или 10)"),
            ("bonus",     7,  "Бонус, ₽"),
            ("due",       8,  "Срок выплаты"),
            ("paid_date", 9,  "Дата выплаты"),
            ("status",   10,  "Статус"),
            ("note",     11,  "Примечание"),
        ]

        menu = ctk.CTkToplevel(self.root)
        menu.title(f"Счёт №{inv['invoice']} — редактирование")
        menu.transient(self.root)
        menu.grab_set()
        menu.configure(fg_color=t["bg"])
        menu.resizable(False, False)
        menu.attributes("-topmost", True)

        body = ctk.CTkScrollableFrame(menu, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=24, pady=24)

        ctk.CTkLabel(body, text=f"Счёт №{inv['invoice']} — что изменить?",
                     font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
                     text_color=ACCENT, anchor="w").pack(anchor="w", pady=(0, 12))

        for key, col, label in fields:
            current = str(inv.get(key, "") or "—")
            row = ctk.CTkFrame(body, fg_color="transparent")
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=f"{label}:", width=130, anchor="w",
                         font=ctk.CTkFont(family="Segoe UI", size=12),
                         text_color=t["fg_secondary"]).pack(side="left")
            ctk.CTkLabel(row, text=current[:30], anchor="w",
                         font=ctk.CTkFont(family="Segoe UI", size=12),
                         text_color=t["fg_dim"]).pack(side="left", padx=(0, 12))

            def make_edit(k=key, c=col, lbl=label):
                dlg = EditDialog(menu, f"Изменить: {lbl}", inv.get(k, ""), lbl, t)
                self.root.wait_window(dlg)
                if dlg.result is not None:
                    new_val = dlg.result
                    # Для колонок суммы/бонуса/% — нормализуем числа
                    if c in (5, 7, 6):
                        try:
                            # сумма/бонус: приводим к float
                            if c in (5, 7):
                                cleaned = new_val.replace(" ", "").replace("\xa0", "").replace(",", ".")
                                new_val = round(float(cleaned), 2) if cleaned else 0
                            elif c == 6:
                                new_val = int(float(new_val)) if new_val else 0
                        except (ValueError, TypeError):
                            pass
                    threading.Thread(
                        target=self._save_detail_cell_thread,
                        args=(inv, c, new_val, k),
                        daemon=True
                    ).start()

            btn = ctk.CTkButton(row, text="✏️", width=36, height=30,
                                fg_color=t["card"], border_width=1, border_color=t["border"],
                                text_color=t["fg"], hover_color=t["card_alt"],
                                font=ctk.CTkFont(family="Segoe UI", size=12),
                                command=make_edit)
            btn.pack(side="right")

        ctk.CTkButton(body, text="Закрыть", height=38,
                      fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color="#ffffff",
                      font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                      command=menu.destroy).pack(anchor="e", pady=(16, 0))

        menu.after(100, lambda: self._center_toplevel(menu, 520, 560))

    def _save_detail_cell_thread(self, inv, col, value, key):
        """Фоновая запись ячейки в «Детализация»."""
        ok = update_detail_cell(self.gspread, inv["row"], col, value, self.key_file)
        if ok:
            inv[key] = value
            self.root.after(0, lambda: self._toast("✅ Сохранено",
                "Поле обновлено в Детализации"))
            # Перерисовываем детали (счёт мог изменить сумму/бонус)
            self.root.after(0, self._show_designer_details)
            # Если меняли сумму/бонус/% — обновляем агрегаты (через перезагрузку)
            if col in (5, 7, 6):
                self.root.after(500, self.refresh_designers_async)
        else:
            self.root.after(0, lambda: self._toast("❌ Ошибка", "Не удалось сохранить"))

    def _mark_paid_thread(self, inv, date_str):
        # J = дата выплаты = колонка 9 (0-indexed)
        ok = update_detail_cell(self.gspread, inv["row"], 9, date_str, self.key_file)
        if ok:
            inv["paid_date"] = date_str
            self.root.after(0, lambda: self._toast("✓ Выплачено",
                f"Счёт №{inv['invoice']} отмечен"))
            self.root.after(0, self.refresh_designers_async)
        else:
            self.root.after(0, lambda: self._toast("❌ Ошибка", "Не удалось записать"))

    def _export_designers_excel(self):
        from tkinter import filedialog, messagebox
        if not self.designers:
            messagebox.showinfo("Экспорт", "Нет данных для экспорта", parent=self.root)
            return
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = filedialog.asksaveasfilename(
            title="Сохранить дизайнеров в Excel",
            defaultextension=".xlsx",
            initialfile=f"Дизайнеры_{ts}.xlsx",
            filetypes=[("Excel", "*.xlsx")])
        if not filepath:
            return
        threading.Thread(target=self._export_d_thread, args=(filepath,), daemon=True).start()

    def _export_d_thread(self, filepath):
        try:
            from openpyxl import Workbook
            from openpyxl.styles import Font, PatternFill, Alignment
            wb = Workbook()
            ws = wb.active
            ws.title = "Дизайнеры"
            headers = ["Дизайнер", "Счетов", "Сумма счетов", "Бонус начислено",
                       "Выплачено", "Бонус к выплате", "Ожидаемая дата", "Ставка %"]
            ws.append(headers)
            for c in ws[1]:
                c.font = Font(bold=True, color="FFFFFF")
                c.fill = PatternFill("solid", fgColor="FF6B35")
                c.alignment = Alignment(horizontal="center")
            for d in self.designers:
                ws.append([d["name"], d["count"], d["sum_all"], d["bonus_all"],
                           d["paid"], d["debt"], d.get("next_due", ""), d["percent"]])
            for col_cells in ws.iter_cols(min_row=1, max_row=ws.max_row):
                max_len = max((len(str(c.value or "")) for c in col_cells), default=10)
                ws.column_dimensions[col_cells[0].column_letter].width = min(max_len + 2, 30)
            wb.save(filepath)
            self.root.after(0, lambda: self._toast("📄 Готово", f"Сохранено: {os.path.basename(filepath)}"))
        except Exception as err:
            self.root.after(0, lambda: self._toast("❌ Ошибка", str(err)))

    # ==========================================
    # ВКЛАДКА «КАЛЕНДАРЬ»
    # ==========================================
    _MONTHS_RU = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
                  "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]
    _WEEKDAYS_RU = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]

    def _build_calendar_tab(self, parent):
        """Строит содержимое вкладки «Календарь»:
        слева месячная сетка, справа события выбранного дня."""
        import calendar as _cal
        import datetime as _dt
        t = self.t
        self._cal = _cal

        # Состояние
        today = _dt.date.today()
        self._cal_year = today.year
        self._cal_month = today.month
        self._cal_selected = today
        self.calendar_events = []
        self._cal_settings = {"interval_min": 60, "lookahead_days": 1}

        # Шапка
        header = ctk.CTkFrame(parent, fg_color=t["card"], corner_radius=0, height=64)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        ctk.CTkLabel(header, text="📅  Календарь",
                     font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
                     text_color=t["fg"]).pack(side="left", padx=(20, 0), pady=12)

        # Настройки напоминаний
        ctk.CTkButton(header, text="⚙️ Напоминания", width=140, height=36,
                      fg_color=t["card"], border_width=1, border_color=t["border"],
                      text_color=t["fg"], hover_color=t["card_alt"],
                      font=ctk.CTkFont(family="Segoe UI", size=12),
                      command=self._calendar_settings_dialog).pack(side="right", padx=(8, 20), pady=12)

        self.btn_refresh_cal = ctk.CTkButton(
            header, text="🔄 Обновить", width=110, height=36,
            fg_color=t["card"], border_width=1, border_color=t["border"],
            text_color=t["fg"], hover_color=t["card_alt"],
            font=ctk.CTkFont(family="Segoe UI", size=12),
            command=self.refresh_calendar_async)
        self.btn_refresh_cal.pack(side="right", padx=8, pady=12)

        # Тело: слева сетка, справа события дня
        import tkinter as tk
        body = ctk.CTkFrame(parent, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=16, pady=16)

        self.paned_cal = tk.PanedWindow(body, orient="horizontal",
                                        sashwidth=6, sashrelief="flat",
                                        bg=t["border"], borderwidth=0, sashpad=0)
        self.paned_cal.pack(fill="both", expand=True)

        # --- ЛЕВАЯ ПАНЕЛЬ: сетка месяца ---
        left = ctk.CTkFrame(self.paned_cal, fg_color=t["card"], corner_radius=10)
        left.pack_propagate(False)

        # Навигация месяца
        nav = ctk.CTkFrame(left, fg_color="transparent")
        nav.pack(fill="x", padx=12, pady=(12, 4))
        ctk.CTkButton(nav, text="‹", width=40, height=32,
                      fg_color=t["card_alt"], text_color=t["fg"],
                      hover_color=t["border"],
                      font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
                      command=lambda: self._cal_shift_month(-1)).pack(side="left")
        self.lbl_cal_title = ctk.CTkLabel(
            nav, text="", width=200,
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color=t["fg"])
        self.lbl_cal_title.pack(side="left", expand=True)
        ctk.CTkButton(nav, text="›", width=40, height=32,
                      fg_color=t["card_alt"], text_color=t["fg"],
                      hover_color=t["border"],
                      font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
                      command=lambda: self._cal_shift_month(1)).pack(side="left")
        ctk.CTkButton(nav, text="Сегодня", width=80, height=32,
                      fg_color=t["card_alt"], text_color=t["fg_secondary"],
                      hover_color=t["border"],
                      font=ctk.CTkFont(family="Segoe UI", size=12),
                      command=self._cal_go_today).pack(side="right")

        # Заголовки дней недели
        wd_frame = ctk.CTkFrame(left, fg_color="transparent")
        wd_frame.pack(fill="x", padx=12)
        for i, wd in enumerate(self._WEEKDAYS_RU):
            color = t["fg_dim"] if i < 5 else t["danger"]
            ctk.CTkLabel(wd_frame, text=wd, width=52,
                         font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                         text_color=color).grid(row=0, column=i, padx=1)

        # Сетка дней (7×6)
        self._cal_grid = ctk.CTkFrame(left, fg_color="transparent")
        self._cal_grid.pack(fill="both", expand=True, padx=12, pady=(2, 12))

        # --- ПРАВАЯ ПАНЕЛЬ: события дня ---
        right_wrap = ctk.CTkFrame(self.paned_cal, fg_color="transparent")
        right_wrap.rowconfigure(0, weight=1)
        right_wrap.columnconfigure(0, weight=1)
        self.right_cal = ctk.CTkScrollableFrame(right_wrap, fg_color=t["card"],
                                                corner_radius=10,
                                                label_text="События")
        self.right_cal.grid(row=0, column=0, sticky="nsew")

        self.paned_cal.add(left, minsize=430, stretch="always")
        self.paned_cal.add(right_wrap, minsize=380, stretch="always")

        def _set_sash():
            try:
                self.root.update_idletasks()
                total = self.paned_cal.winfo_width()
                if total > 100:
                    self.paned_cal.sash_place(0, int(total * 0.55), 0)
            except Exception:
                pass
        self.root.after(200, _set_sash)

        # Первая отрисовка
        self._render_calendar()

    # ----- Навигация -----
    def _cal_shift_month(self, delta):
        import datetime as _dt
        m = self._cal_month + delta
        y = self._cal_year
        if m < 1:
            m, y = 12, y - 1
        elif m > 12:
            m, y = 1, y + 1
        self._cal_month, self._cal_year = m, y
        # Сбрасываем выбранный день на 1-е число нового месяца
        self._cal_selected = _dt.date(y, m, 1)
        self._render_calendar()

    def _cal_go_today(self):
        import datetime as _dt
        today = _dt.date.today()
        self._cal_year, self._cal_month = today.year, today.month
        self._cal_selected = today
        self._render_calendar()

    # ----- Сбор событий -----
    def _get_events_for_date(self, d):
        """Все события (ручные + авто) на дату d (datetime.date)."""
        import datetime as _dt
        d_str = d.strftime("%d.%m.%Y")
        result = []
        # Ручные из листа
        for ev in self.calendar_events:
            if ev["date"] == d_str:
                result.append(ev)
        # Авто: сроки бонусов дизайнеров (невыплаченные)
        for des in getattr(self, "designers", []) or []:
            for inv in des.get("invoices", []):
                try:
                    bonus = float(str(inv.get("bonus", "")).replace(",", ".")) if inv.get("bonus") else 0
                except (ValueError, TypeError):
                    bonus = 0
                if bonus > 0 and not inv.get("paid_date") and inv.get("due"):
                    try:
                        due_d = _dt.datetime.strptime(
                            str(inv["due"]).strip()[:10], "%d.%m.%Y").date()
                    except ValueError:
                        continue
                    if due_d == d:
                        result.append({
                            "row": None, "date": d_str, "time": "",
                            "text": (f"💰 Бонус {des['name']}: {bonus:g} ₽ "
                                     f"(счёт №{inv.get('invoice', '?')})"),
                            "type": "авто", "done": "", "note": "",
                            "client": inv.get("client", ""),
                        })
        # Сортировка: по времени
        result.sort(key=lambda e: e.get("time", ""))
        return result

    def _render_calendar(self):
        """Перерисовывает сетку месяца."""
        import datetime as _dt
        t = self.t
        # Заголовок
        self.lbl_cal_title.configure(
            text=f"{self._MONTHS_RU[self._cal_month - 1]} {self._cal_year}")

        # Очищаем сетку
        for w in self._cal_grid.winfo_children():
            w.destroy()

        today = _dt.date.today()
        # Матрица недель (понедельник первый)
        weeks = self._cal.monthcalendar(self._cal_year, self._cal_month)

        for row_i, week in enumerate(weeks):
            for col_i, day in enumerate(week):
                if day == 0:
                    # Пустая ячейка
                    ctk.CTkLabel(self._cal_grid, text="").grid(
                        row=row_i, column=col_i, padx=1, pady=1)
                    continue
                d = _dt.date(self._cal_year, self._cal_month, day)
                events = self._get_events_for_date(d)
                has_events = len(events) > 0
                is_today = (d == today)
                is_selected = (d == self._cal_selected)
                is_weekend = col_i >= 5

                # Стили ячейки
                if is_selected:
                    fg, bg, border = "#ffffff", ACCENT, 0
                elif is_today:
                    fg, bg, border = ACCENT, t["card_alt"], 1
                elif is_weekend:
                    fg, bg, border = t["danger"], t["card"], 0
                else:
                    fg, bg, border = t["fg"], t["card"], 0

                day_text = str(day)
                if has_events:
                    day_text += " •"  # маркер событий

                btn = ctk.CTkButton(
                    self._cal_grid, text=day_text,
                    width=52, height=38, corner_radius=6,
                    fg_color=bg, text_color=fg,
                    hover_color=t["card_alt"],
                    border_width=border, border_color=ACCENT,
                    font=ctk.CTkFont(family="Segoe UI", size=12,
                                     weight="bold" if is_today else "normal"),
                    command=lambda _d=d: self._cal_select_day(_d))
                btn.grid(row=row_i, column=col_i, padx=1, pady=1)

    def _cal_select_day(self, d):
        """Выбор дня — показать события справа."""
        self._cal_selected = d
        self._render_calendar()
        self._show_day_events()

    def _show_day_events(self):
        """Показывает события выбранного дня + кнопки действий."""
        t = self.t
        import datetime as _dt
        d = self._cal_selected
        d_str = d.strftime("%d.%m.%Y")
        is_today = (d == _dt.date.today())

        # Очищаем панель
        for w in self.right_cal.winfo_children():
            w.destroy()

        weekday = self._WEEKDAYS_RU[d.weekday()]
        title = f"{d.strftime('%d.%m.%Y')} ({weekday})"
        if is_today:
            title += " — сегодня"

        ctk.CTkLabel(self.right_cal, text=title,
                     font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
                     text_color=t["fg"], anchor="w").pack(anchor="w", pady=(4, 2))

        events = self._get_events_for_date(d)

        # Кнопка добавления
        ctk.CTkButton(self.right_cal, text="➕ Добавить событие", height=38,
                      fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color="#ffffff",
                      font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                      command=lambda: self._add_event_dialog(d)).pack(fill="x", pady=(8, 10))

        if not events:
            ctk.CTkLabel(self.right_cal, text="Событий нет",
                         font=ctk.CTkFont(family="Segoe UI", size=13),
                         text_color=t["fg_dim"]).pack(pady=20)
            return

        for ev in events:
            card = ctk.CTkFrame(self.right_cal, fg_color=t["card_alt"],
                                corner_radius=6, border_width=1,
                                border_color=t["border"])
            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(fill="x", padx=10, pady=8)

            # Верх: время + тип
            top = ctk.CTkFrame(inner, fg_color="transparent")
            top.pack(fill="x")
            time_txt = ev.get("time", "") or ""
            type_color = t["warning"] if ev.get("type") == "авто" else t["fg_dim"]
            ctk.CTkLabel(top, text=time_txt, width=50,
                         font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                         text_color=ACCENT, anchor="w").pack(side="left")
            ctk.CTkLabel(top, text=ev.get("type", ""),
                         font=ctk.CTkFont(family="Segoe UI", size=10),
                         text_color=type_color).pack(side="right")

            # Текст события (выполненные — зачёркнутые)
            done = bool(ev.get("done"))
            txt_color = t["fg_dim"] if done else t["fg"]
            ctk.CTkLabel(inner, text=ev.get("text", ""),
                         font=ctk.CTkFont(family="Segoe UI", size=12,
                                          overstrike=done),
                         text_color=txt_color, anchor="w",
                         wraplength=340, justify="left").pack(anchor="w", pady=(2, 0))

            # Кнопки: готово / удалить (только для ручных)
            btns = ctk.CTkFrame(inner, fg_color="transparent")
            btns.pack(fill="x", pady=(6, 0))
            if ev.get("row"):
                # Ручное событие — можно отметить/удалить
                def mark_done(_ev=ev):
                    new_val = "да" if not _ev["done"] else ""
                    threading.Thread(
                        target=self._cal_mark_done_thread,
                        args=(_ev, new_val), daemon=True).start()
                ctk.CTkButton(btns, text="✓ Готово" if not done else "↩ Вернуть",
                              width=90, height=28,
                              fg_color=t["success"] if not done else t["card_alt"],
                              text_color="#ffffff" if not done else t["fg"],
                              hover_color=t["fg_dim"],
                              font=ctk.CTkFont(family="Segoe UI", size=11),
                              command=mark_done).pack(side="left", padx=(0, 4))
                def del_ev(_ev=ev):
                    from tkinter import messagebox
                    if messagebox.askyesno("Удалить",
                                           f"Удалить событие:\n{_ev['text'][:60]}?",
                                           parent=self.root):
                        threading.Thread(
                            target=self._cal_delete_thread,
                            args=(_ev,), daemon=True).start()
                ctk.CTkButton(btns, text="🗑", width=40, height=28,
                              fg_color=t["card"], border_width=1,
                              border_color=t["border"], text_color=t["danger"],
                              hover_color=t["border"],
                              font=ctk.CTkFont(family="Segoe UI", size=12),
                              command=del_ev).pack(side="left")
            else:
                ctk.CTkLabel(btns, text="(автоматическое — из таблицы бонусов)",
                             font=ctk.CTkFont(family="Segoe UI", size=10),
                             text_color=t["fg_dim"]).pack(side="left")

            card.pack(fill="x", pady=3)

    # ----- Диалог добавления события -----
    def _add_event_dialog(self, date_obj):
        """Диалог добавления события на дату."""
        import datetime as _dt
        t = self.t
        dlg = ctk.CTkToplevel(self.root)
        dlg.title("Новое событие")
        dlg.transient(self.root)
        dlg.grab_set()
        dlg.configure(fg_color=t["bg"])
        dlg.resizable(False, False)
        dlg.attributes("-topmost", True)

        body = ctk.CTkFrame(dlg, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=24, pady=24)

        ctk.CTkLabel(body, text=f"📅 Событие на {date_obj.strftime('%d.%m.%Y')}",
                     font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
                     text_color=ACCENT, anchor="w").pack(anchor="w", pady=(0, 12))

        ctk.CTkLabel(body, text="Время (ЧЧ:ММ, необязательно)", anchor="w",
                     font=ctk.CTkFont(family="Segoe UI", size=12),
                     text_color=t["fg_secondary"]).pack(anchor="w", pady=(6, 2))
        entry_time = ctk.CTkEntry(body, width=340, height=34,
                                  fg_color=t["bg"], border_color=t["border"],
                                  border_width=1, text_color=t["fg"],
                                  placeholder_text="напр. 15:00",
                                  font=ctk.CTkFont(family="Segoe UI", size=13))
        entry_time.pack(fill="x")

        ctk.CTkLabel(body, text="Событие *", anchor="w",
                     font=ctk.CTkFont(family="Segoe UI", size=12),
                     text_color=t["fg_secondary"]).pack(anchor="w", pady=(8, 2))
        entry_text = ctk.CTkEntry(body, width=340, height=34,
                                  fg_color=t["bg"], border_color=t["border"],
                                  border_width=1, text_color=t["fg"],
                                  placeholder_text="напр. Позвонить Иванову",
                                  font=ctk.CTkFont(family="Segoe UI", size=13))
        entry_text.pack(fill="x")

        ctk.CTkLabel(body, text="Примечание", anchor="w",
                     font=ctk.CTkFont(family="Segoe UI", size=12),
                     text_color=t["fg_secondary"]).pack(anchor="w", pady=(8, 2))
        entry_note = ctk.CTkEntry(body, width=340, height=34,
                                  fg_color=t["bg"], border_color=t["border"],
                                  border_width=1, text_color=t["fg"],
                                  font=ctk.CTkFont(family="Segoe UI", size=13))
        entry_note.pack(fill="x")

        def save():
            text = entry_text.get().strip()
            if not text:
                from tkinter import messagebox
                messagebox.showwarning("Проверьте", "Поле «Событие» обязательно",
                                       parent=dlg)
                return
            time_v = entry_time.get().strip()
            # Простая валидация времени
            if time_v:
                import re as _re
                if not _re.match(r"^\d{1,2}:\d{2}$", time_v):
                    from tkinter import messagebox
                    messagebox.showwarning("Время", "Формат времени: ЧЧ:ММ (напр. 15:00)",
                                           parent=dlg)
                    return
                hh, mm = time_v.split(":")
                if not (0 <= int(hh) <= 23 and 0 <= int(mm) <= 59):
                    from tkinter import messagebox
                    messagebox.showwarning("Время", "Некорректное время",
                                           parent=dlg)
                    return
            date_str = date_obj.strftime("%d.%m.%Y")
            threading.Thread(
                target=self._cal_add_thread,
                args=(date_str, time_v, text, entry_note.get().strip()),
                daemon=True).start()
            dlg.destroy()

        btns = ctk.CTkFrame(body, fg_color="transparent")
        btns.pack(fill="x", pady=(18, 0))
        btns.columnconfigure((0, 1), weight=1, uniform="ev")
        ctk.CTkButton(btns, text="Отмена", height=38,
                      fg_color=t["card"], border_width=1, border_color=t["border"],
                      text_color=t["fg"], hover_color=t["card_alt"],
                      font=ctk.CTkFont(family="Segoe UI", size=13),
                      command=dlg.destroy).grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ctk.CTkButton(btns, text="Добавить", height=38,
                      fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color="#ffffff",
                      font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                      command=save).grid(row=0, column=1, sticky="ew", padx=(4, 0))

        dlg.bind("<Escape>", lambda e: dlg.destroy())
        entry_text.focus_set()
        dlg.after(100, lambda: self._center_toplevel(dlg, 420, 420))

    # ----- Фоновые операции -----
    def refresh_calendar_async(self):
        """Загрузка событий календаря в фоне."""
        if hasattr(self, "btn_refresh_cal"):
            self.btn_refresh_cal.configure(state="disabled", text="🔄 ...")
        threading.Thread(target=self._cal_load_thread, daemon=True).start()

    def _cal_load_thread(self):
        try:
            events = load_calendar_events(self.gspread, self.key_file)
            settings = load_calendar_settings(self.gspread, self.key_file)
            self.calendar_events = events
            self._cal_settings = settings
            self.root.after(0, self._after_cal_load)
        except Exception as e:
            err = str(e)
            self.root.after(0, lambda: self._toast("❌ Ошибка", f"Календарь: {err}"))

    def _after_cal_load(self):
        if hasattr(self, "btn_refresh_cal"):
            self.btn_refresh_cal.configure(state="normal", text="🔄 Обновить")
        if hasattr(self, "_cal_grid"):
            self._render_calendar()
            self._show_day_events()
        # Планируем напоминания по настройкам
        self._schedule_cal_reminder()

    def _cal_add_thread(self, date_str, time_v, text, note):
        ok = add_calendar_event(self.gspread, date_str, time_v, text, note,
                                self.key_file)
        if ok:
            self.root.after(0, lambda: self._toast("✅ Добавлено", text[:40]))
            self.root.after(300, self.refresh_calendar_async)
        else:
            self.root.after(0, lambda: self._toast("❌ Ошибка", "Не удалось добавить"))

    def _cal_mark_done_thread(self, ev, new_val):
        ok = update_calendar_cell(self.gspread, ev["row"], 4, new_val, self.key_file)
        if ok:
            ev["done"] = new_val
            self.root.after(0, self._show_day_events)
            self.root.after(0, self._render_calendar)
        else:
            self.root.after(0, lambda: self._toast("❌ Ошибка", "Не удалось обновить"))

    def _cal_delete_thread(self, ev):
        ok = delete_calendar_event(self.gspread, ev["row"], self.key_file)
        if ok:
            self.root.after(0, lambda: self._toast("🗑 Удалено", ev["text"][:40]))
            self.root.after(300, self.refresh_calendar_async)
        else:
            self.root.after(0, lambda: self._toast("❌ Ошибка", "Не удалось удалить"))

    # ----- Настройки напоминаний -----
    def _calendar_settings_dialog(self):
        """Диалог настроек напоминаний."""
        t = self.t
        dlg = ctk.CTkToplevel(self.root)
        dlg.title("Настройки напоминаний")
        dlg.transient(self.root)
        dlg.grab_set()
        dlg.configure(fg_color=t["bg"])
        dlg.resizable(False, False)
        dlg.attributes("-topmost", True)

        body = ctk.CTkFrame(dlg, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=24, pady=24)

        ctk.CTkLabel(body, text="⚙️ Напоминания календаря",
                     font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
                     text_color=ACCENT, anchor="w").pack(anchor="w", pady=(0, 12))

        ctk.CTkLabel(body, text="Проверять события каждые (минут):", anchor="w",
                     font=ctk.CTkFont(family="Segoe UI", size=12),
                     text_color=t["fg_secondary"]).pack(anchor="w", pady=(6, 2))
        entry_interval = ctk.CTkEntry(body, width=300, height=34,
                                      fg_color=t["bg"], border_color=t["border"],
                                      border_width=1, text_color=t["fg"],
                                      font=ctk.CTkFont(family="Segoe UI", size=13))
        entry_interval.pack(fill="x")
        entry_interval.insert(0, str(self._cal_settings.get("interval_min", 60)))

        ctk.CTkLabel(body, text="Напоминать за сколько дней:", anchor="w",
                     font=ctk.CTkFont(family="Segoe UI", size=12),
                     text_color=t["fg_secondary"]).pack(anchor="w", pady=(8, 2))
        entry_days = ctk.CTkEntry(body, width=300, height=34,
                                  fg_color=t["bg"], border_color=t["border"],
                                  border_width=1, text_color=t["fg"],
                                  font=ctk.CTkFont(family="Segoe UI", size=13))
        entry_days.pack(fill="x")
        entry_days.insert(0, str(self._cal_settings.get("lookahead_days", 1)))

        def save():
            try:
                interval = max(1, min(1440, int(entry_interval.get().strip())))
            except ValueError:
                interval = 60
            try:
                days = max(1, min(30, int(entry_days.get().strip())))
            except ValueError:
                days = 1
            self._cal_settings = {"interval_min": interval, "lookahead_days": days}
            threading.Thread(
                target=self._cal_save_settings_thread,
                args=(dict(self._cal_settings),), daemon=True).start()
            dlg.destroy()

        btns = ctk.CTkFrame(body, fg_color="transparent")
        btns.pack(fill="x", pady=(18, 0))
        btns.columnconfigure((0, 1), weight=1, uniform="s")
        ctk.CTkButton(btns, text="Отмена", height=38,
                      fg_color=t["card"], border_width=1, border_color=t["border"],
                      text_color=t["fg"], hover_color=t["card_alt"],
                      font=ctk.CTkFont(family="Segoe UI", size=13),
                      command=dlg.destroy).grid(row=0, column=0, sticky="ew", padx=(0, 4))
        ctk.CTkButton(btns, text="Сохранить", height=38,
                      fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color="#ffffff",
                      font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                      command=save).grid(row=0, column=1, sticky="ew", padx=(4, 0))

        dlg.after(100, lambda: self._center_toplevel(dlg, 400, 360))

    def _cal_save_settings_thread(self, settings):
        ok = save_calendar_settings(self.gspread, settings, self.key_file)
        if ok:
            self.root.after(0, lambda: self._toast("✅ Сохранено",
                f"Каждые {settings['interval_min']} мин, за {settings['lookahead_days']} дн."))
            self.root.after(200, self._schedule_cal_reminder)
        else:
            self.root.after(0, lambda: self._toast("❌ Ошибка", "Не удалось сохранить"))

    # ----- Уведомления -----
    def _schedule_cal_reminder(self):
        """Планирует следующую проверку напоминаний по интервалу из настроек."""
        if hasattr(self, "_cal_reminder_id"):
            try:
                self.root.after_cancel(self._cal_reminder_id)
            except Exception:
                pass
        interval_ms = self._cal_settings.get("interval_min", 60) * 60 * 1000
        self._cal_reminder_id = self.root.after(interval_ms, self._cal_check_reminders)

    def _cal_check_reminders(self):
        """Проверяет события на сегодня/завтра и показывает окно-напоминание."""
        import datetime as _dt
        t = self.t
        try:
            days = self._cal_settings.get("lookahead_days", 1)
            today = _dt.date.today()
            lines = []
            for offset in range(days + 1):
                d = today + _dt.timedelta(days=offset)
                events = self._get_events_for_date(d)
                todo = [e for e in events if not e.get("done")]
                if not todo:
                    continue
                when = "Сегодня" if offset == 0 else (
                    "Завтра" if offset == 1 else d.strftime("%d.%m.%Y"))
                lines.append(f"📅 {when}:")
                for e in todo:
                    time_v = f" {e['time']}" if e.get("time") else ""
                    lines.append(f"   •{time_v} {e['text']}")
            if lines:
                self._cal_show_reminder("\n".join(lines))
        except Exception as e:
            print(f"Ошибка напоминания: {e}")
        # Следующая проверка
        self._schedule_cal_reminder()

    def _cal_show_reminder(self, text):
        """Всплывающее окно-напоминание (поверх всех окон)."""
        t = self.t
        win = ctk.CTkToplevel(self.root)
        win.title("📅 Напоминание")
        win.attributes("-topmost", True)
        win.resizable(False, False)
        win.configure(fg_color=t["bg"])

        body = ctk.CTkFrame(win, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=24, pady=24)

        ctk.CTkLabel(body, text="📅 Напоминания",
                     font=ctk.CTkFont(family="Segoe UI", size=17, weight="bold"),
                     text_color=ACCENT, anchor="w").pack(anchor="w", pady=(0, 10))
        ctk.CTkLabel(body, text=text,
                     font=ctk.CTkFont(family="Segoe UI", size=13),
                     text_color=t["fg"], anchor="w",
                     justify="left", wraplength=420).pack(anchor="w")

        ctk.CTkButton(body, text="Понятно", height=38,
                      fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color="#ffffff",
                      font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                      command=win.destroy).pack(anchor="e", pady=(16, 0))

        win.after(100, lambda: self._center_toplevel(win, 500, 400))

    # ===== ЗАГРУЗКА СЧЕТОВ =====
    def refresh_async(self):
        self.btn_refresh.configure(state="disabled", text="🔄 Загрузка...")
        threading.Thread(target=self._load_thread, daemon=True).start()
        # Параллельно грузим и дизайнеров (если вкладка уже строилась)
        if hasattr(self, "_designers_built"):
            self.refresh_designers_async()

    def _load_thread(self):
        try:
            data, ws = load_invoices(self.gspread, self.key_file)
            self.invoices = data
            self.ws = ws
            # Запоминаем количество строк — для автообновления
            try:
                self._last_row_count = ws.row_count
            except Exception:
                pass
            self.root.after(0, lambda: self._after_load(True, None))
        except Exception as e:
            err = str(e)
            self.root.after(0, lambda: self._after_load(False, err))

    def _after_load(self, ok, error):
        self.btn_refresh.configure(state="normal", text="🔄 Обновить")
        if not ok:
            self._show_error_in_details(f"Не удалось загрузить данные:\n{error}")
            return
        self._apply_filter()
        # Планируем следующий автозапуск проверки
        self._schedule_auto_refresh()
        # При запуске: грузим календарь (события + настройки) и сразу
        # показываем напоминания о делах на сегодня/завтра
        if not hasattr(self, "_calendar_loaded_once"):
            self._calendar_loaded_once = True
            threading.Thread(target=self._cal_startup_thread, daemon=True).start()

    def _cal_startup_thread(self):
        """Стартовая загрузка календаря + дизайнеров (для авто-событий бонусов)
        + напоминание при открытии."""
        try:
            events = load_calendar_events(self.gspread, self.key_file)
            settings = load_calendar_settings(self.gspread, self.key_file)
            self.calendar_events = events
            self._cal_settings = settings
            # Дизайнеры — для авто-событий (сроки бонусов) в напоминаниях
            try:
                designers, raw = load_designers(self.gspread, self.key_file)
                self.designers = designers
                self.designers_raw = raw
            except Exception:
                pass
            self.root.after(0, self._cal_check_reminders)
        except Exception as e:
            print(f"Стартовый календарь: {e}")

    # ===== АВТООБНОВЛЕНИЕ (проверка каждые 45 сек) =====
    def _schedule_auto_refresh(self, interval_ms=45000):
        """Планирует фоновую проверку таблицы на изменения."""
        # Отменяем предыдущий таймер если был
        if hasattr(self, "_auto_refresh_id"):
            try:
                self.root.after_cancel(self._auto_refresh_id)
            except Exception:
                pass
        self._auto_refresh_id = self.root.after(interval_ms, self._auto_check_changes)

    def _auto_check_changes(self):
        """Фоновая проверка: изменилось ли кол-во строк в таблице.
        Если да — автоматически перезагружаем данные (новый счёт добавлен)."""
        if not hasattr(self, "_auto_refresh_paused"):
            self._auto_refresh_paused = False
        if self._auto_refresh_paused:
            self._schedule_auto_refresh()
            return
        # Если открыт любой диалог (Toplevel) — откладываем проверку
        try:
            for child in self.root.winfo_children():
                if isinstance(child, ctk.CTkToplevel):
                    self._schedule_auto_refresh()
                    return
        except Exception:
            pass

        def _check():
            try:
                ws = _get_sheet(self.gspread, self.key_file)
                current = ws.row_count
                def _apply():
                    last = getattr(self, "_last_row_count", None)
                    if last is not None and current != last:
                        # Таблица изменилась — автообновление!
                        self._toast("🔄 Данные обновлены", "Обнаружен новый счёт в таблице")
                        self.refresh_async()
                    else:
                        # Ничего не изменилось — продолжаем опрос
                        self._schedule_auto_refresh()
                self.root.after(0, _apply)
            except Exception:
                # Ошибка сети — просто продолжаем опрос
                self.root.after(0, self._schedule_auto_refresh)

        threading.Thread(target=_check, daemon=True).start()

    def _apply_filter(self):
        q = self.search_var.get().strip().lower()
        if q:
            self.filtered = []
            for inv in self.invoices:
                hay = " ".join([
                    inv.get("invoice", ""), inv.get("client", ""),
                    inv.get("designer", ""), inv.get("manager", ""),
                    inv.get("phone", ""),
                ]).lower()
                if q in hay:
                    self.filtered.append(inv)
        else:
            self.filtered = list(self.invoices)

        # Сортируем по текущему состоянию (колонка + направление)
        self._do_sort()
        self._populate_tree()

    def _sort_by(self, col):
        """Сортировка по клику на заголовок колонки.
        Если та же колонка — меняем направление, иначе новая колонка (по убыванию)."""
        if self._sort_state["col"] == col:
            self._sort_state["reverse"] = not self._sort_state["reverse"]
        else:
            self._sort_state["col"] = col
            self._sort_state["reverse"] = True
        self._do_sort()
        self._populate_tree(reselect=True)
        # Обновляем стрелочки в заголовках
        self._update_heading_arrows()

    def _do_sort(self):
        """Физическая сортировка self.filtered по self._sort_state."""
        col = self._sort_state["col"]
        reverse = self._sort_state["reverse"]

        def sort_key(inv):
            if col == "invoice":
                # № счёта — числовой (если возможно), иначе строка
                try:
                    return (0, int(inv.get("invoice", "0")))
                except (ValueError, TypeError):
                    return (1, str(inv.get("invoice", "")))
            elif col == "date":
                # Дата ДД.ММ.ГГГГ → YYYYMMDD для правильной сортировки
                d = str(inv.get("date", ""))
                try:
                    dd, mm, yyyy = d.split(".")
                    return f"{yyyy}{mm}{dd}"
                except Exception:
                    return "0"
            elif col == "client":
                return str(inv.get("client", "")).lower()
            elif col == "manager":
                return str(inv.get("manager", "")).lower()
            return ""

        try:
            self.filtered.sort(key=sort_key, reverse=reverse)
        except Exception:
            # если смешанные типы — сортируем как строки
            self.filtered.sort(key=lambda inv: str(inv.get(col, "")), reverse=reverse)

    def _update_heading_arrows(self):
        """Показывает стрелку ▲▼ на активной колонке."""
        col = self._sort_state["col"]
        arrow = "▼" if self._sort_state["reverse"] else "▲"
        titles = {
            "invoice": "№ счёта",
            "client": "Клиент",
            "date": "Дата",
            "manager": "Менеджер",
        }
        for c, base in titles.items():
            text = f"{base} {arrow}" if c == col else base
            try:
                self.tree.heading(c, text=text)
            except Exception:
                pass

    def _populate_tree(self, reselect=False):
        # Запоминаем текущий выбор (чтобы не сбивать при сортировке)
        current_sel = None
        if reselect:
            try:
                sel = self.tree.selection()
                if sel:
                    current_sel = sel[0]
            except Exception:
                pass

        for item in self.tree.get_children():
            self.tree.delete(item)
        for inv in self.filtered:
            # Приоритет тегов: Отгружено > Уведомлено > Обычный
            if inv.get("shipped"):
                tag = "shipped"
            elif inv.get("notified"):
                tag = "notified"
            else:
                tag = "normal"
            client = inv.get("client", "")
            if len(client) > 32:
                client = client[:30] + "…"
            self.tree.insert("", "end", iid=inv["invoice"],
                             values=(inv.get("invoice", ""), client,
                                     inv.get("date", ""), inv.get("manager", "")),
                             tags=(tag,))
        self.right.configure(label_text=f"Всего счетов: {len(self.filtered)}")

        if not self.filtered:
            self._show_empty()
            return

        # Восстанавливаем выбор, иначе выбираем первый
        target_id = current_sel if (current_sel and any(i["invoice"] == current_sel for i in self.filtered)) else self.filtered[0]["invoice"]
        try:
            self.tree.selection_set(target_id)
            self.tree.focus(target_id)
            self.tree.see(target_id)
        except Exception:
            pass
        self._show_details()

    # ===== ДЕТАЛИ =====
    def _clear_right(self):
        for w in self.right.winfo_children():
            w.destroy()

    def _show_empty(self):
        self._clear_right()
        ctk.CTkLabel(self.right, text="Нет данных",
                     font=ctk.CTkFont(family="Segoe UI", size=14),
                     text_color=self.t["fg_dim"]).pack(pady=40)

    def _show_error_in_details(self, msg):
        self._clear_right()
        ctk.CTkLabel(self.right, text="⚠️ Ошибка",
                     font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
                     text_color=self.t["danger"]).pack(pady=(0, 8))
        ctk.CTkLabel(self.right, text=msg,
                     font=ctk.CTkFont(family="Segoe UI", size=12),
                     text_color=self.t["fg_secondary"], wraplength=500,
                     justify="left").pack()

    def _show_details(self):
        sel = self.tree.selection()
        if not sel:
            return
        invoice_num = sel[0]
        inv = None
        for i in self.filtered:
            if i["invoice"] == invoice_num:
                inv = i
                break
        if not inv:
            return

        t = self.t
        self._clear_right()

        # === ШАПКА ===
        header_card = ctk.CTkFrame(self.right,
                                   fg_color=t["card_alt"], corner_radius=8)
        header_card.pack(fill="x", pady=(0, 12))
        inner = ctk.CTkFrame(header_card, fg_color="transparent")
        inner.pack(fill="x", padx=14, pady=12)

        # Приоритет статусов (выше — важнее):
        #   Отгружено > Уведомлено > В работе
        if inv.get("shipped"):
            status_text, status_color = "🚚 Отгружено клиенту", t["shipped"]
        elif inv.get("notified"):
            status_text, status_color = "✓ Уведомлено", t["success"]
        else:
            status_text, status_color = "⏳ В работе", t["fg_dim"]

        title_row = ctk.CTkFrame(inner, fg_color="transparent")
        title_row.pack(fill="x")
        ctk.CTkLabel(title_row, text=f"Счёт №{inv.get('invoice', '')}",
                     font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
                     text_color=t["fg"]).pack(side="left")

        # Статус — в «таблетке» с фоном
        pill = ctk.CTkFrame(title_row, fg_color=status_color, corner_radius=14, height=28)
        pill.pack(side="right", padx=(8, 0), pady=4)
        ctk.CTkLabel(pill, text=status_text,
                     font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                     text_color="#ffffff").pack(padx=12, pady=3)

        # Кнопки действий: Редактировать + Отгружено + В таблице
        actions_row = ctk.CTkFrame(inner, fg_color="transparent")
        actions_row.pack(fill="x", pady=(10, 8))

        def open_in_sheet(_inv=inv):
            import webbrowser
            row = _inv.get("row_start", 2)
            url = f"{SHEET_URL}#gid=0&range=A{row}:Q{row}"
            try:
                webbrowser.open(url)
                self._toast("🔗 Открыто", f"Счёт №{_inv['invoice']} в Google Sheets")
            except Exception as e:
                self._toast("❌ Ошибка", str(e))

        ctk.CTkButton(actions_row, text="✏️ Редактировать", width=150, height=36,
                      fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color="#ffffff",
                      font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                      command=lambda: self._edit_invoice_header(inv)).pack(side="left", padx=(0, 8))

        # Кнопка «Отгружено» — серая. Если уже отгружено — отключена.
        ship_state = "normal" if not inv.get("shipped") else "disabled"
        ctk.CTkButton(actions_row, text="🚚 Отгружено", width=130, height=36,
                      fg_color=t["shipped"], hover_color=t["fg_dim"], text_color="#ffffff",
                      font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                      state=ship_state,
                      command=lambda: self._mark_shipped(inv)).pack(side="left", padx=(0, 8))

        ctk.CTkButton(actions_row, text="🔗 В таблице", width=120, height=36,
                      fg_color=t["card"], border_width=1, border_color=t["border"],
                      text_color=t["fg"], hover_color=t["card_alt"],
                      font=ctk.CTkFont(family="Segoe UI", size=12),
                      command=open_in_sheet).pack(side="left")

        # Данные
        info_grid = ctk.CTkFrame(inner, fg_color="transparent")
        info_grid.pack(fill="x")
        info_grid.columnconfigure(1, weight=1)
        rows = [
            ("client", COL_CLIENT, "Клиент", inv.get("client", "—")),
            ("phone", COL_PHONE, "Телефон", inv.get("phone", "—") or "—"),
            ("date", COL_DATE, "Дата", inv.get("date", "—")),
            ("designer", COL_DESIGNER, "Дизайнер", inv.get("designer", "—") or "—"),
            ("manager", COL_MANAGER, "Менеджер", inv.get("manager", "—") or "—"),
            ("payment", COL_PAYMENT, "Форма оплаты", inv.get("payment", "—") or "—"),
            ("qty", COL_QTY, "Позиций", inv.get("qty", "—") or "—"),
        ]
        for i, (key, col, lbl, val) in enumerate(rows):
            ctk.CTkLabel(info_grid, text=lbl, width=120, anchor="w",
                         font=ctk.CTkFont(family="Segoe UI", size=12),
                         text_color=t["fg_secondary"]).grid(row=i, column=0, sticky="w", pady=1)
            val_lbl = ctk.CTkLabel(info_grid, text=val, anchor="w",
                                   font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                                   text_color=t["fg"])
            val_lbl.grid(row=i, column=1, sticky="w", pady=1)

        # === ПОЗИЦИИ ===
        positions = inv.get("positions", [])
        if positions:
            ctk.CTkLabel(self.right, text="📦 Позиции и поставщики",
                         font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                         text_color=ACCENT, anchor="w").pack(anchor="w", pady=(8, 6))
            for idx, pos in enumerate(positions):
                card = self._make_position_card(pos, idx + 1, inv)
                card.pack(fill="x", pady=3)
        else:
            ctk.CTkLabel(self.right, text="Нет данных по позициям",
                         font=ctk.CTkFont(family="Segoe UI", size=12),
                         text_color=t["fg_dim"]).pack(anchor="w", pady=(8, 0))

    def _make_position_card(self, pos, num, inv):
        t = self.t
        card = ctk.CTkFrame(self.right,
                            fg_color=t["card_alt"], corner_radius=6,
                            border_width=1, border_color=t["border"])
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=12, pady=8)

        top = ctk.CTkFrame(inner, fg_color="transparent")
        top.pack(fill="x")
        ctk.CTkLabel(top, text=f"Поз. {pos.get('positions', '—')}",
                     font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                     text_color=t["fg"], width=80, anchor="w").pack(side="left")
        ctk.CTkLabel(top, text=pos.get("supplier", "—") or "—",
                     font=ctk.CTkFont(family="Segoe UI", size=13),
                     text_color=ACCENT, anchor="w").pack(side="left", padx=(4, 0))

        tk = pos.get("tk_arrival", "")
        wh = pos.get("warehouse", "")
        if tk and wh:
            loc, loc_color = "📍 Склад + ТК", t["success"]
        elif wh:
            loc, loc_color = "📍 На складе", t["success"]
        elif tk:
            loc, loc_color = "🚛 В ТК", t["warning"]
        else:
            loc, loc_color = "⏳ Ожидает", t["fg_dim"]
        ctk.CTkLabel(top, text=loc,
                     font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                     text_color=loc_color, anchor="e").pack(side="right")

        # Редактировать позицию
        ctk.CTkButton(top, text="✏️", width=32, height=28,
                      fg_color=t["card"], border_width=1, border_color=t["border"],
                      text_color=t["fg"], hover_color=t["bg"],
                      font=ctk.CTkFont(family="Segoe UI", size=12),
                      command=lambda: self._edit_position(pos, inv)).pack(side="right", padx=(0, 8))

        # Детали
        grid = ctk.CTkFrame(inner, fg_color="transparent")
        grid.pack(fill="x", pady=(4, 0))
        grid.columnconfigure(1, weight=1)
        detail_rows = [
            ("sup_inv", COL_SUP_INV, "№ счёта ПОСТ", pos.get("sup_inv", "")),
            ("pay_date", COL_PAY_DATE, "Дата опл ПОСТ", pos.get("pay_date", "")),
            ("ship_date", COL_SHIP_DATE, "Отгр клиенту", pos.get("ship_date", "")),
            ("tk_send", COL_TK_SEND, "Отправка в ТК", pos.get("tk_send", "")),
            ("tk_arrival", COL_TK_ARRIVAL, "Приход ТК КЗН", pos.get("tk_arrival", "")),
            ("warehouse", COL_WAREHOUSE, "Приход СКЛАД", pos.get("warehouse", "")),
        ]
        for i, (key, col, lbl, val) in enumerate(detail_rows):
            if not val:
                continue
            ctk.CTkLabel(grid, text=lbl, width=130, anchor="w",
                         font=ctk.CTkFont(family="Segoe UI", size=11),
                         text_color=t["fg_dim"]).grid(row=i, column=0, sticky="w")
            ctk.CTkLabel(grid, text=val, anchor="w",
                         font=ctk.CTkFont(family="Segoe UI", size=11),
                         text_color=t["fg_secondary"]).grid(row=i, column=1, sticky="w")

        extra = pos.get("extra", "")
        if extra:
            ctk.CTkLabel(inner, text=f"📝 {extra}",
                         font=ctk.CTkFont(family="Segoe UI", size=11),
                         text_color=t["fg_dim"], anchor="w", wraplength=500,
                         justify="left").pack(anchor="w", pady=(4, 0))

        return card

    # ===== РЕДАКТИРОВАНИЕ =====
    def _edit_invoice_header(self, inv):
        """Редактирование полей шапки счёта (клиент, телефон, менеджер и т.д.)."""
        t = self.t
        # Список редактируемых полей: (key, col, label)
        fields = [
            ("client", COL_CLIENT, "Клиент"),
            ("phone", COL_PHONE, "Телефон"),
            ("date", COL_DATE, "Дата"),
            ("designer", COL_DESIGNER, "Дизайнер"),
            ("manager", COL_MANAGER, "Менеджер"),
            ("payment", COL_PAYMENT, "Форма оплаты"),
        ]

        # Простое меню: спрашиваем какое поле редактировать
        menu = ctk.CTkToplevel(self.root)
        menu.title("Редактировать счёт")
        menu.transient(self.root)
        menu.grab_set()
        menu.configure(fg_color=t["bg"])
        menu.resizable(False, False)
        menu.attributes("-topmost", True)

        body = ctk.CTkFrame(menu, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=24, pady=24)
        ctk.CTkLabel(body, text=f"Счёт №{inv['invoice']} — что изменить?",
                     font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
                     text_color=ACCENT, anchor="w").pack(anchor="w", pady=(0, 12))

        for key, col, label in fields:
            current = inv.get(key, "") or "—"
            row = ctk.CTkFrame(body, fg_color="transparent")
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=f"{label}:", width=120, anchor="w",
                         font=ctk.CTkFont(family="Segoe UI", size=12),
                         text_color=t["fg_secondary"]).pack(side="left")
            ctk.CTkLabel(row, text=current, anchor="w",
                         font=ctk.CTkFont(family="Segoe UI", size=12),
                         text_color=t["fg_dim"]).pack(side="left", padx=(0, 12))

            def make_edit(k=KeyError, c=col, lbl=label):
                # открываем диалог ввода
                dlg = EditDialog(menu, f"Изменить: {lbl}", inv.get(k, ""), lbl, t)
                self.root.wait_window(dlg)
                if dlg.result is not None:
                    # Записываем в фоновом потоке
                    threading.Thread(
                        target=self._save_cell_thread,
                        args=(inv["row_start"], c, dlg.result, inv, k),
                        daemon=True
                    ).start()

            btn = ctk.CTkButton(row, text="✏️", width=36, height=30,
                                fg_color=t["card"], border_width=1, border_color=t["border"],
                                text_color=t["fg"], hover_color=t["card_alt"],
                                font=ctk.CTkFont(family="Segoe UI", size=12),
                                command=make_edit)
            btn.pack(side="right")

        ctk.CTkButton(body, text="Закрыть", height=38,
                      fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color="#ffffff",
                      font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                      command=menu.destroy).pack(anchor="e", pady=(16, 0))

        menu.after(100, lambda: self._center_toplevel(menu, 480, 420))

    def _center_toplevel(self, win, w, h):
        win.update_idletasks()
        sw = win.winfo_screenwidth()
        sh = win.winfo_screenheight()
        x = (sw // 2) - (w // 2)
        y = (sh // 2) - (h // 2)
        win.geometry(f"{w}x{h}+{x}+{y}")

    def _edit_position(self, pos, inv):
        """Редактирование полей позиции поставщика."""
        t = self.t
        fields = [
            ("positions", COL_POSITIONS, "Позиции"),
            ("supplier", COL_SUPPLIER, "Поставщик"),
            ("sup_inv", COL_SUP_INV, "№ счёта ПОСТ"),
            ("pay_date", COL_PAY_DATE, "Дата опл ПОСТ"),
            ("ship_date", COL_SHIP_DATE, "Дата отгрузки"),
            ("tk_send", COL_TK_SEND, "Отправка в ТК"),
            ("tk_arrival", COL_TK_ARRIVAL, "Приход ТК КЗН"),
            ("warehouse", COL_WAREHOUSE, "Приход СКЛАД"),
            ("extra", COL_EXTRA, "Дополнительно"),
        ]

        menu = ctk.CTkToplevel(self.root)
        menu.title(f"Позиция {pos.get('positions','')} — {pos.get('supplier','')}")
        menu.transient(self.root)
        menu.grab_set()
        menu.configure(fg_color=t["bg"])
        menu.resizable(False, False)
        menu.attributes("-topmost", True)

        body = ctk.CTkScrollableFrame(menu, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=24, pady=24)
        ctk.CTkLabel(body, text="Что изменить?",
                     font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
                     text_color=ACCENT, anchor="w").pack(anchor="w", pady=(0, 12))

        for key, col, label in fields:
            current = pos.get(key, "") or "—"
            row = ctk.CTkFrame(body, fg_color="transparent")
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=f"{label}:", width=140, anchor="w",
                         font=ctk.CTkFont(family="Segoe UI", size=12),
                         text_color=t["fg_secondary"]).pack(side="left")
            ctk.CTkLabel(row, text=current, anchor="w",
                         font=ctk.CTkFont(family="Segoe UI", size=12),
                         text_color=t["fg_dim"]).pack(side="left", padx=(0, 12))

            def make_edit(k=key, c=col, lbl=label):
                dlg = EditDialog(menu, f"Изменить: {lbl}", pos.get(k, ""), lbl, t)
                self.root.wait_window(dlg)
                if dlg.result is not None:
                    threading.Thread(
                        target=self._save_pos_thread,
                        args=(pos["row"], c, dlg.result, pos, k),
                        daemon=True
                    ).start()

            ctk.CTkButton(row, text="✏️", width=36, height=30,
                          fg_color=t["card"], border_width=1, border_color=t["border"],
                          text_color=t["fg"], hover_color=t["card_alt"],
                          font=ctk.CTkFont(family="Segoe UI", size=12),
                          command=make_edit).pack(side="right")

        ctk.CTkButton(body, text="Закрыть", height=38,
                      fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color="#ffffff",
                      font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                      command=menu.destroy).pack(anchor="e", pady=(16, 0))

        menu.after(100, lambda: self._center_toplevel(menu, 500, 500))

    def _save_cell_thread(self, row, col, value, inv, key):
        """Фоновая запись ячейки шапки счёта."""
        ok = update_cell(self.gspread, row, col, value, self.key_file)
        if ok:
            inv[key] = value
            self.root.after(0, lambda: self._toast("✅ Сохранено", f"{COL_LABELS[col]} обновлён"))
            self.root.after(0, self._show_details)
        else:
            self.root.after(0, lambda: self._toast("❌ Ошибка", "Не удалось сохранить"))

    def _save_pos_thread(self, row, col, value, pos, key):
        """Фоновая запись ячейки позиции + проверка прихода всего счёта."""
        ok = update_cell(self.gspread, row, col, value, self.key_file)
        if not ok:
            self.root.after(0, lambda: self._toast("❌ Ошибка", "Не удалось сохранить"))
            return

        # Обновляем локальную копию
        pos[key] = value
        self.root.after(0, lambda: self._toast("✅ Сохранено", f"{COL_LABELS.get(col, 'Поле')} обновлён"))

        # Проверяем: не пришли ли ВСЕ позиции счёта?
        # Находим родительский счёт
        parent_inv = None
        for inv in self.invoices:
            for p in inv.get("positions", []):
                if p is pos:
                    parent_inv = inv
                    break
            if parent_inv:
                break

        if parent_inv:
            # Небольшая пауза чтобы Google Sheets успел зафиксировать запись
            import time
            time.sleep(1.0)
            notified = check_and_notify_arrival(self.gspread, parent_inv, self.key_file)
            if notified:
                parent_inv["notified"] = True
                # Обновляем qty с пометкой
                import re
                m = re.match(r"(\d+)", str(parent_inv.get("qty", "")))
                qty_num = m.group(1) if m else ""
                parent_inv["qty"] = f"{qty_num} — УВЕДОМЛЕНО" if qty_num else "УВЕДОМЛЕНО"
                self.root.after(0, lambda: self._toast("📦 Все позиции пришли!",
                    f"Счёт №{parent_inv['invoice']} — уведомление отправлено, покрашено в зелёный"))
                # Перерисовываем список чтобы отразить зелёный
                self.root.after(0, self._populate_tree_with_reselect)

        self.root.after(0, self._show_details)

    def _mark_shipped(self, inv):
        """Кнопка «🚚 Отгружено» — ставит сегодняшнюю дату в K (Дата отгрузки)
        для ВСЕХ строк счёта и перекрашивает счёт в серый."""
        # Подтверждение
        from tkinter import messagebox
        today = datetime.datetime.now().strftime("%d.%m.%Y")
        answer = messagebox.askyesno(
            "Отметить отгруженным?",
            f"Счёт №{inv['invoice']} — отметить отгруженным клиенту?\n\n"
            f"Во всех строках счёта будет проставлена дата отгрузки: {today}\n"
            f"Счёт перекрасится в серый.",
            parent=self.root,
        )
        if not answer:
            return
        # Запускаем запись в фоне
        threading.Thread(target=self._mark_shipped_thread,
                         args=(inv, today), daemon=True).start()

    def _mark_shipped_thread(self, inv, date_str):
        """Фоновая запись даты отгрузки во все строки счёта + покраска в серый."""
        positions = inv.get("positions", [])
        if not positions:
            rows_to_update = [inv.get("row_start", 2)]
        else:
            rows_to_update = [p["row"] for p in positions]

        ok_count = 0
        for row in rows_to_update:
            if update_cell(self.gspread, row, COL_SHIP_DATE, date_str, self.key_file):
                ok_count += 1

        if ok_count == len(rows_to_update):
            # Красим строки счёта в серый напрямую через API
            # (onEdit в Apps Script не срабатывает при записи через API)
            row_start = inv.get("row_start", rows_to_update[0])
            row_end = inv.get("row_end", rows_to_update[-1])
            # Цвет берём под ТЕКУЩУЮ тему (плотный серый, не тёмный)
            bg = self.t["shipped_bg"]
            color_invoice_rows(self.gspread, row_start, row_end, bg, self.key_file)

            # Обновляем локальные данные
            inv["shipped"] = True
            for p in positions:
                p["ship_date"] = date_str
            self.root.after(0, lambda: self._toast("🚚 Отгружено",
                f"Счёт №{inv['invoice']} — дата {date_str} ({ok_count} стр., покрашено)"))
            # Перерисовываем список + детали
            self.root.after(0, self._populate_tree_with_reselect)
        else:
            self.root.after(0, lambda: self._toast("❌ Ошибка",
                f"Записано {ok_count}/{len(rows_to_update)} строк"))

    def _populate_tree_with_reselect(self):
        """Перерисовать список с сохранением выбора (обёртка для after)."""
        self._populate_tree(reselect=True)

    def _toast(self, title, msg):
        """Маленькое всплывающее уведомление."""
        toast = ctk.CTkFrame(self.root, fg_color=self.t["success"], corner_radius=8)
        toast.place(relx=0.5, rely=0.95, anchor="center")
        ctk.CTkLabel(toast, text=f"{title}  {msg}",
                     font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                     text_color="#ffffff").pack(padx=20, pady=10)
        self.root.after(2500, toast.destroy)

    # ===== НОВЫЙ СЧЁТ =====
    def _new_invoice(self):
        dlg = NewInvoiceDialog(self.root, self.t)
        self.root.wait_window(dlg)
        if not dlg.result:
            return

        r = dlg.result
        # Формируем строку для таблицы (17 колонок)
        row_data = [
            r.get("invoice", ""),       # A
            r.get("date", ""),          # B
            r.get("client", ""),        # C
            r.get("phone", ""),         # D
            r.get("designer", ""),      # E
            r.get("positions", "1"),    # F — к-во поз. (ставим позиции, если нет — 1)
            r.get("positions", "1"),    # G — Позиции ПОСТ
            r.get("supplier", ""),      # H
            r.get("sup_inv", ""),       # I
            "", "", "", "", "", "",     # J-O пустые
            r.get("manager", ""),       # P
            r.get("payment", ""),       # Q
        ]

        threading.Thread(target=self._add_invoice_thread,
                         args=(row_data,), daemon=True).start()

    def _add_invoice_thread(self, row_data):
        ok = add_invoice_row(self.gspread, row_data, self.key_file)
        if ok:
            self.root.after(0, lambda: self._toast("✅ Добавлено", f"Счёт №{row_data[0]} создан"))
            self.root.after(500, self.refresh_async)  # обновляем список
        else:
            self.root.after(0, lambda: self._toast("❌ Ошибка", "Не удалось добавить счёт"))

    # ===== ЭКСПОРТ =====
    def _export_excel(self):
        from tkinter import filedialog
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"Счета_Аганим_{ts}.xlsx"
        filepath = filedialog.asksaveasfilename(
            title="Сохранить в Excel",
            defaultextension=".xlsx",
            initialfile=default_name,
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")]
        )
        if not filepath:
            return

        threading.Thread(target=self._export_thread, args=(filepath,), daemon=True).start()

    def _export_thread(self, filepath):
        ok = export_to_excel(self.invoices, filepath)
        if ok:
            self.root.after(0, lambda: self._toast("📄 Готово", f"Сохранено: {os.path.basename(filepath)}"))
        else:
            self.root.after(0, lambda: self._toast("❌ Ошибка", "Не удалось сохранить Excel"))

    # ===== ЗАКРЫТИЕ =====
    def _on_close(self):
        try:
            if self.on_close:
                self.on_close()
        finally:
            self.root.destroy()

    def show(self):
        self.root.mainloop()


# ==========================================
# ТОЧКА ВХОДА (для отдельного dashboard.exe)
# ==========================================
def main():
    """Запуск дашборда как отдельной программы."""
    import gspread
    import os
    import sys

    # Определяем папки: APP_DIR (.exe) и DATA_DIR (%APPDATA%, записываемая)
    if getattr(sys, 'frozen', False):
        app_dir = os.path.dirname(sys.executable)
    else:
        app_dir = os.path.dirname(os.path.abspath(__file__))

    appdata_root = os.path.realpath(os.environ.get("APPDATA") or os.path.expanduser("~"))
    data_dir = os.path.realpath(os.path.join(appdata_root, "PDF-bot-Aganim"))
    if data_dir != appdata_root and not data_dir.startswith(appdata_root + os.sep):
        data_dir = app_dir
    try:
        os.makedirs(data_dir, exist_ok=True)
    except Exception:
        data_dir = app_dir
    os.chdir(data_dir)

    # Поиск key.json: 1) DATA_DIR 2) рядом с .exe 3) bundled внутри .exe
    def find_key():
        p_data = os.path.join(data_dir, "key.json")
        if os.path.exists(p_data):
            return p_data
        p_app = os.path.join(app_dir, "key.json")
        if os.path.exists(p_app):
            return p_app
        if getattr(sys, 'frozen', False):
            bundled = os.path.join(sys._MEIPASS, "key.json")
            if os.path.exists(bundled):
                try:
                    import shutil
                    shutil.copy2(bundled, p_data)
                    return p_data
                except Exception:
                    return bundled
        return None

    key_path = find_key()
    if not key_path:
        from tkinter import messagebox
        messagebox.showerror("PDF-бот Аганим",
                             "Файл key.json не найден!\n"
                             "Положите key.json рядом с dashboard.exe\n"
                             "или в " + data_dir)
        return

    # Настройки развёртывания (URL таблицы объекта)
    apply_deployment_settings()
    if not SHEET_URL:
        from tkinter import messagebox
        messagebox.showerror(
            "PDF-бот Аганим",
            "Таблица не настроена.\n\n"
            "Запустите «PDF-бот Аганим» (pdf_bot.exe) и пройдите "
            "первичную настройку — вставьте ссылку на вашу таблицу.\n"
            "После этого дашборд откроется.")
        return

    ctk.set_appearance_mode("system")
    ctk.set_default_color_theme("blue")

    app = DashboardWindow(gspread, SHEET_URL, key_path)
    app.show()


if __name__ == "__main__":
    main()
