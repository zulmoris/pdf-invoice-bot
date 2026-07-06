import pdfplumber
import gspread
import os
import sys
import json
import logging
from datetime import datetime
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# ==========================================
# ОПРЕДЕЛЯЕМ ПАПКУ ПРОГРАММЫ И РАБОТАЕМ В НЕЙ
# ==========================================
# При запуске .exe (PyInstaller) sys.frozen = True
# При запуске .py — обычный режим
if getattr(sys, 'frozen', False):
    # .exe режим: папка где лежит .exe
    APP_DIR = os.path.dirname(sys.executable)
else:
    # .py режим: папка где лежит скрипт
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

os.chdir(APP_DIR)


# ==========================================
# АВТО-ДОСТАВАНИЕ key.json ИЗ .exe
# ==========================================
def extract_key_json():
    """
    Если программа запущена как .exe и рядом нет key.json —
    достаём его из bundled-ресурсов.

    В .py режиме ничего не делает (ключ уже лежит рядом).
    """
    key_path = os.path.join(APP_DIR, "key.json")

    # Если ключ уже есть — ничего не делаем
    if os.path.exists(key_path):
        return

    # Если .exe режим — пытаемся достать из _MEIPASS (временная папка PyInstaller)
    if getattr(sys, 'frozen', False):
        bundled_key = os.path.join(sys._MEIPASS, "key.json")
        if os.path.exists(bundled_key):
            try:
                import shutil
                shutil.copy2(bundled_key, key_path)
                print(f"key.json извлечён в: {key_path}")
            except Exception as e:
                print(f"Не удалось извлечь key.json: {e}")


# Достаём ключ (если нужно)
extract_key_json()

# ==========================================
# НАСТРОЙКА ЛОГИРОВАНИЯ
# ==========================================
# logging — это встроенный модуль Python для записи событий в файл.
# Представь: как дневник, куда программа сама пишет что произошло.
#
# ЗАЧЕМ: Менеджер видит только скрытое окно бота. Если что-то сломается —
# он не скопирует ошибку. А в лог-файле всё сохранится, и ты посмотришь потом.
#
# Формат лога будет таким:
# 2026-07-06 18:00:00 - ERROR - ОШИБКА при подключении к Google Sheets: нет интернета

# Создаём "настройщик" логов
logger = logging.getLogger("bot")                         # даём имя нашему логгеру
logger.setLevel(logging.DEBUG)                            # записываем ВСЁ (от ошибок до инфо)

# Куда писать — в файл errors.log
file_handler = logging.FileHandler("errors.log", encoding="utf-8")
file_handler.setLevel(logging.DEBUG)                      # в файл — всё

# Как оформлять каждую строку
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
file_handler.setFormatter(formatter)

# Привязываем настройку к логгеру
logger.addHandler(file_handler)

# Также выводим в консоль (на случай, если запускаешь вручную для дебага)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)                    # в консоль — только важное
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# ==========================================
# WINDOWS-УВЕДОМЛЕНИЯ
# ==========================================
# Используем ДВУХУРОВНЕВУЮ систему уведомлений:
#
# Уровень 1: PowerShell (всплывающее уведомление Windows)
#   - Красиво, как уведомления от Telegram
#   - НЕ работает, если уведомления Windows выключены
#
# Уровень 2: tkinter (маленькое окошко-пузырь)
#   - Всегда работает, независимо от настроек Windows
#   - Показывается как маленькое окошко в углу, исчезает через duration секунд
#   - Встроено в Python, pip install не нужен
#
# ЛОГИКА: Сначала пробуем PowerShell. Если не сработало — показываем tkinter.


def _show_tkinter_bubble(title, message, duration=5):
    """
    Маленькое окошко-уведомление через tkinter.

    tkinter — встроенная в Python библиотека для создания окон.
    Здесь мы используем её не для полноценного окна, а для
    маленького "пузыря" в углу экрана.

    after(duration * 1000, root.destroy) — автоматически
    закрывает окошко через duration секунд.
    """
    import tkinter as tk
    import threading

    # Запускаем в отдельном потоке, чтобы не блокировать бота
    def _popup():
        root = tk.Tk()
        root.title(title)
        root.attributes("-topmost", True)  # Поверх всех окон
        root.resizable(False, False)

        # Заголовок
        tk.Label(root, text=title, font=("Segoe UI", 10, "bold")).pack(padx=15, pady=(10, 0))

        # Сообщение
        tk.Label(root, text=message, font=("Segoe UI", 9), wraplength=300, justify="left").pack(padx=15, pady=(5, 10))

        # Автозакрытие через duration секунд
        root.after(duration * 1000, root.destroy)
        root.mainloop()

    threading.Thread(target=_popup, daemon=True).start()


def show_notification(title, message, duration=5):
    """
    Показывает уведомление — ВСЕГДА.

    Сначала пробует PowerShell (красивое системное уведомление).
    Затем ВСЕГДА показывает tkinter-окошко как гарантию.

    title    — заголовок (например "✅ Счёт обработан")
    message  — подробности
    duration — сколько секунд показывать
    """
    # PowerShell — как бонус, если уведомления Windows включены
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

    # tkinter — ВСЕГДА показываем (гарантия, что менеджер увидит)
    try:
        _show_tkinter_bubble(title, message, duration)
        logger.info(f"[УВЕДОМЛЕНИЕ-tkinter] {title}: {message}")
    except Exception as e:
        logger.error(f"Не удалось показать уведомление (ни PowerShell, ни tkinter): {e}")
# ВАША ССЫЛКА НА ТАБЛИЦУ (НОВАЯ — для логистики)
SHEET_URL = "https://docs.google.com/spreadsheets/d/1QkXocbAJu1a5rcu3XNEfpHnoF_mA5flgehjO6E7VIWM/edit?usp=sharing"

# Файл, где будет храниться путь к папке
CONFIG_FILE = "config.json"

# ==========================================
# ИЗВЛЕЧЕНИЕ ДАТЫ ИЗ НАЗВАНИЯ ФАЙЛА
# ==========================================
# Словарь для перевода русских месяцев в числа.
# "мая" → 5, "января" → 1, и т.д.
MONTHS_RU = {
    "января": "01", "февраля": "02", "марта": "03", "апреля": "04",
    "мая": "05", "июня": "06", "июля": "07", "августа": "08",
    "сентября": "09", "октября": "10", "ноября": "11", "декабря": "12"
}


def extract_invoice_date(filename):
    """
    Извлекает дату из названия файла и возвращает в формате ДД.ММ.ГГГГ.

    Пример: "Счет на оплату № 921 от 30 мая 2026 г.pdf"
    Результат: "30.05.2026"

    Если дату найти не удалось — возвращает пустую строку.
    """
    try:
        # Ищем фразу "от ... г" в названии файла
        if " от " not in filename:
            return ""

        start = filename.find(" от ") + 4  # Прыгаем за слово "от "
        end = filename.find(" г", start)   # Ищем букву "г" (год)
        if end == -1:
            end = len(filename) - 4  # обрезаем .pdf, если " г" не нашли

        date_str = filename[start:end].strip()  # "30 мая 2026"

        # Разбиваем на части: ["30", "мая", "2026"]
        parts = date_str.split()
        if len(parts) == 3:
            day = parts[0].zfill(2)  # "30" → "30", "5" → "05" (добавляем ноль)
            month = MONTHS_RU.get(parts[1].lower(), "")  # "мая" → "05"
            year = parts[2]
            if month:
                return f"{day}.{month}.{year}"

    except Exception as e:
        logger.warning(f"Не удалось извлечь дату из '{filename}': {e}")

    return ""


# ==========================================
# ДИАЛОГИ ВВОДА (ОКОШКИ ДЛЯ МЕНЕДЖЕРА)
# ==========================================

def _center_window(root):
    """Центрирует окно на экране."""
    root.update_idletasks()
    w = root.winfo_width()
    h = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (w // 2)
    y = (root.winfo_screenheight() // 2) - (h // 2)
    root.geometry(f"+{x}+{y}")


# ==========================================
# ЧТЕНИЕ СПРАВОЧНИКА "Telegram ID"
# ==========================================
def get_contacts_list():
    """
    Читает вкладку 'Telegram ID' и возвращает имена по типам.

    Возвращает dict:
      {
        "менеджеры": ["Гадя", "Виталина", ...],
        "дизайнеры": ["Татьяна Колочкова", ...],
        "руководители": ["Дамир", ...],
        "все": ["Гадя", "Виталина", "Татьяна Колочкова", ...]  # без дубликатов
      }

    Если прочитать не удалось — возвращает пустые списки.
    """
    empty = {"менеджеры": [], "дизайнеры": [], "руководители": [], "все": []}

    try:
        gc = gspread.service_account(filename="key.json")
        spreadsheet = gc.open_by_url(SHEET_URL)

        # Ищем вкладку "Telegram ID" по имени
        try:
            tg_sheet = spreadsheet.worksheet("Telegram ID")
        except gspread.exceptions.WorksheetNotFound:
            logger.warning("Вкладка 'Telegram ID' не найдена")
            return empty

        data = tg_sheet.get_all_values()
        if len(data) <= 1:
            return empty  # только заголовки

        result = {"менеджеры": [], "дизайнеры": [], "руководители": [], "все": []}

        for row in data[1:]:  # пропускаем заголовок
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

            # "все" — без дубликатов
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
    """
    Добавляет новое имя во вкладку 'Telegram ID' (без Telegram ID).

    name         — имя для добавления (например "Татьяна Колочкова")
    contact_type — тип: "менеджер" или "дизайнер"

    Возвращает True при успехе, False при ошибке.
    """
    try:
        gc = gspread.service_account(filename="key.json")
        spreadsheet = gc.open_by_url(SHEET_URL)
        tg_sheet = spreadsheet.worksheet("Telegram ID")
        tg_sheet.append_row([name, "", contact_type])
        logger.info(f"Добавлен контакт в справочник: {name} ({contact_type})")
        return True
    except Exception as e:
        logger.error(f"Не удалось добавить контакт в справочник: {e}")
        return False


# ==========================================
# ВИДЖЕТ: АВТОДОПОЛНЕНИЕ (Entry + Listbox)
# ==========================================
class AutocompleteEntry:
    """
    Поле ввода с настоящим автодополнением (как в Google Search).

    Менеджер начинает печатать "Тат..." → снизу появляется список вариантов.
    Клик по варианту → подставляется в поле.
    Стрелки вниз/вверх → выбор в списке. Enter → выбрать.

    Как работает:
    - Entry: поле ввода
    - Toplevel + Listbox: всплывающий список (поверх всех окон)

    Использование:
        entry = AutocompleteEntry(parent, values=["Гадя", "Виталина"])
        entry.grid(...)
        ...
        selected = entry.get()
    """

    def __init__(self, parent, values=None, width=35, font=("Segoe UI", 9)):
        import tkinter as tk

        self.parent = parent
        self.all_values = values or []
        self._popup = None
        self._listbox = None

        # Поле ввода
        self.entry = tk.Entry(parent, width=width, font=font)

        # События:
        # <KeyRelease> — после нажатия клавиши (фильтрация)
        # <Down> — стрелка вниз (выбор в списке)
        # <Up> — стрелка вверх
        # <Return> — Enter (выбрать или закрыть)
        # <FocusOut> — клик вне поля (закрыть список)
        self.entry.bind("<KeyRelease>", self._on_key_release)
        self.entry.bind("<Down>", self._on_arrow_down)
        self.entry.bind("<Up>", self._on_arrow_up)
        self.entry.bind("<Return>", self._on_enter)
        self.entry.bind("<FocusOut>", self._on_focus_out)

    def _on_key_release(self, event):
        """Вызывается при каждом нажатии — фильтрует и показывает список."""
        import tkinter as tk

        # Игнорируем служебные клавиши
        if event.keysym in ("Up", "Down", "Return", "Escape", "Tab",
                            "Shift_L", "Shift_R", "Control_L", "Control_R"):
            return

        typed = self.entry.get().strip().lower()

        # Фильтруем: оставляем те, что содержат введённый текст
        if typed:
            filtered = [v for v in self.all_values if typed in v.lower()]
        else:
            filtered = self.all_values[:10]  # если пусто — первые 10

        # Показываем список только если есть что показать
        if len(filtered) == 0:
            self._hide_popup()
            return

        # Если всего 1 вариант и он полностью совпал — не показываем список
        if len(filtered) == 1 and filtered[0].lower() == typed:
            self._hide_popup()
            return

        self._show_popup(filtered)

    def _show_popup(self, values):
        """Показывает всплывающий список под полем ввода."""
        import tkinter as tk

        # Если список уже открыт — обновляем значения
        if self._popup and self._listbox:
            self._listbox.delete(0, tk.END)
            for v in values:
                self._listbox.insert(tk.END, v)
            return

        # Создаём всплывающее окно
        self._popup = tk.Toplevel(self.parent)
        self._popup.wm_overrideredirect(True)  # убираем рамку окна

        # Размещаем ПОД полем ввода
        x = self.entry.winfo_rootx()
        y = self.entry.winfo_rooty() + self.entry.winfo_height()
        self._popup.wm_geometry(f"+{x}+{y}")

        # Список вариантов
        self._listbox = tk.Listbox(
            self._popup,
            font=("Segoe UI", 9),
            selectbackground="#4472C4",
            selectforeground="white",
            activestyle="none"
        )
        self._listbox.pack()

        # Заполняем список
        for v in values:
            self._listbox.insert(tk.END, v)

        # Клик по варианту → выбираем
        self._listbox.bind("<Button-1>", self._on_listbox_click)

    def _hide_popup(self):
        """Скрывает всплывающий список."""
        import tkinter as tk
        if self._popup:
            self._popup.destroy()
            self._popup = None
            self._listbox = None

    def _on_listbox_click(self, event):
        """Клик по варианту в списке → подставляем в поле."""
        import tkinter as tk
        if self._listbox:
            selection = self._listbox.curselection()
            if not selection:
                # Если кликнули без выделения — берём под курсором
                index = self._listbox.nearest(event.y)
            else:
                index = selection[0]

            value = self._listbox.get(index)
            self.entry.delete(0, tk.END)
            self.entry.insert(0, value)
            self._hide_popup()

    def _on_arrow_down(self, event):
        """Стрелка вниз — выделить следующий вариант в списке."""
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
            return "break"  # предотвращаем перемещение курсора в Entry

    def _on_arrow_up(self, event):
        """Стрелка вверх — выделить предыдущий вариант."""
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
        """Enter — выбираем выделенный вариант."""
        import tkinter as tk
        if self._listbox and self._listbox.size() > 0:
            current = self._listbox.curselection()
            if current:
                value = self._listbox.get(current[0])
                self.entry.delete(0, tk.END)
                self.entry.insert(0, value)
                self._hide_popup()
                return "break"

    def _on_focus_out(self, event):
        """Клик вне поля — скрываем список (с небольшой задержкой)."""
        self.parent.after(200, self._hide_popup)

    # ==========================================
    # Методы совместимости (как у Combobox)
    # ==========================================
    def grid(self, **kwargs):
        """Передаёт grid() во внутренний Entry."""
        self.entry.grid(**kwargs)

    def get(self):
        """Возвращает введённое/выбранное значение."""
        return self.entry.get().strip()

    def set(self, value):
        """Устанавливает значение."""
        import tkinter as tk
        self.entry.delete(0, tk.END)
        self.entry.insert(0, value)

    def focus_set(self):
        """Устанавливает фокус."""
        self.entry.focus_set()


def check_and_offer_add(name, contact_type, known_names):
    """
    Проверяет, есть ли имя в справочнике. Если нет — предлагает добавить.

    name         — введённое имя (например "Татьяна Колочкова")
    contact_type — "менеджер" или "дизайнер"
    known_names  — список известных имён этого типа

    Возвращает: name (возможно уточнённое) или "" если отменили.
    """
    import tkinter as tk
    from tkinter import messagebox

    if not name:
        return name  # пустое поле — оставляем пустым, это нормально

    # Проверяем точное совпадение (без учёта регистра)
    name_lower = name.lower().strip()
    found = False
    for known in known_names:
        if known.lower().strip() == name_lower:
            found = True
            break

    if found:
        return name  # всё ок, имя есть в справочнике

    # Имени нет — предлагаем добавить
    answer = messagebox.askyesno(
        "Нет в справочнике",
        f"Имя '{name}' не найдено в справочнике.\n\n"
        f"Telegram-уведомления по этому имени работать НЕ будут.\n\n"
        f"Добавить '{name}' в справочник как {contact_type}?",
        parent=None
    )

    if answer:
        # Добавляем в справочник
        if add_contact_to_directory(name, contact_type):
            messagebox.showinfo("Добавлено", f"'{name}' добавлен в справочник.\n\n"
                              f"Теперь нужно, чтобы {name} написал боту /start\n"
                              f"и прислал свой Telegram ID для привязки.")
            return name
        else:
            messagebox.showerror("Ошибка", "Не удалось добавить в справочник. Проверьте интернет.")
            return name
    else:
        # Не добавлять — продолжаем как есть
        return name


def show_invoice_dialog(invoice, invoice_date, client, qty, default_manager="",
                       contacts=None):
    """
    ОКОШКО 1: Данные по счёту (один раз на весь счёт).

    Показывает данные из PDF + поля Дизайнер, Менеджер и Форма оплаты.
    Эти данные общие для всех поставщиков по этому счёту.

    contacts — dict с именами из справочника (для автодополнения):
      {"менеджеры": [...], "дизайнеры": [...], "все": [...]}

    Возвращает (designer, manager, payment_form) или None при отмене.
    """
    import tkinter as tk
    from tkinter import messagebox

    if contacts is None:
        contacts = {"менеджеры": [], "дизайнеры": [], "все": []}

    result = {"designer": "", "manager": default_manager, "payment_form": ""}
    dialog_done = False

    def on_ok():
        result["designer"] = combo_designer.get()
        result["manager"] = combo_manager.get()
        result["payment_form"] = entry_payment.get().strip()
        nonlocal dialog_done
        dialog_done = True
        root.destroy()

    def on_cancel():
        nonlocal dialog_done
        dialog_done = True
        root.destroy()

    root = tk.Tk()
    root.title(f"Счёт №{invoice}")
    root.attributes("-topmost", True)
    root.resizable(False, False)

    # Данные из PDF (не редактируемые)
    section_pdf = tk.LabelFrame(root, text="  📄 Данные из счёта  ", font=("Segoe UI", 9, "bold"), padx=10, pady=5)
    section_pdf.grid(row=0, column=0, columnspan=2, padx=10, pady=(10, 5), sticky="ew")

    pdf_data = [
        ("Номер счёта:", f"№{invoice}"),
        ("Дата:", invoice_date if invoice_date else "не распознана"),
        ("Клиент:", client),
        ("Позиций:", str(qty)),
    ]
    for i, (label, value) in enumerate(pdf_data):
        tk.Label(section_pdf, text=label, font=("Segoe UI", 9)).grid(row=i, column=0, sticky="w", pady=1)
        tk.Label(section_pdf, text=value, font=("Segoe UI", 9, "bold"), fg="#0066CC").grid(row=i, column=1, sticky="w", padx=(10, 0), pady=1)

    # Поля ввода
    section_input = tk.LabelFrame(root, text="  ✏️ Заполните  ", font=("Segoe UI", 9, "bold"), padx=10, pady=5)
    section_input.grid(row=1, column=0, columnspan=2, padx=10, pady=5, sticky="ew")

    # Дизайнер (с автодополнением из справочника)
    tk.Label(section_input, text="Дизайнер:", font=("Segoe UI", 9)).grid(row=0, column=0, sticky="w", pady=2)
    combo_designer = AutocompleteEntry(section_input, values=contacts.get("дизайнеры", []))
    combo_designer.grid(row=0, column=1, sticky="ew", pady=2)
    combo_designer.focus_set()

    # Менеджер (с автодополнением из справочника)
    tk.Label(section_input, text="Менеджер:", font=("Segoe UI", 9)).grid(row=1, column=0, sticky="w", pady=2)
    combo_manager = AutocompleteEntry(section_input, values=contacts.get("менеджеры", []))
    combo_manager.grid(row=1, column=1, sticky="ew", pady=2)
    combo_manager.set(default_manager)

    # Форма оплаты (обычное поле — там фиксированные варианты)
    tk.Label(section_input, text="Форма оплаты:", font=("Segoe UI", 9)).grid(row=2, column=0, sticky="w", pady=2)
    entry_payment = tk.Entry(section_input, width=35, font=("Segoe UI", 9))
    entry_payment.grid(row=2, column=1, sticky="ew", pady=2)

    # Кнопки
    btn_frame = tk.Frame(root)
    btn_frame.grid(row=2, column=0, columnspan=2, pady=(5, 10))
    tk.Button(btn_frame, text="OK", width=12, font=("Segoe UI", 9, "bold"),
              bg="#4CAF50", fg="white", command=on_ok).pack(side="left", padx=5)
    tk.Button(btn_frame, text="Отмена", width=12, font=("Segoe UI", 9),
              command=on_cancel).pack(side="left", padx=5)

    root.bind("<Return>", lambda e: on_ok())
    root.bind("<Escape>", lambda e: on_cancel())
    _center_window(root)
    root.mainloop()

    if not dialog_done or not result["manager"]:
        return None
    return result["designer"], result["manager"], result["payment_form"]


def show_supplier_dialog(remaining_positions, invoice, supplier_hint=""):
    """
    ОКОШКО 2: Поставщик и позиции (показывается циклически).

    remaining_positions — список свободных позиций (напр. [3,5,6,7])
    invoice — номер счёта (для заголовка)
    supplier_hint — подставка названия поставщика (если была ошибка ввода)

    Возвращает (supplier, positions_list) или None при отмене.
      - supplier: строка (напр. "ВИА")
      - positions_list: список int (напр. [3,5,6])
      Если позиции введены с ошибкой — возвращает кортеж с строкой ошибки.
    """
    import tkinter as tk

    result = {"supplier": supplier_hint, "input_text": ""}
    dialog_done = False
    error_msg = ""

    def on_ok():
        result["input_text"] = entry_positions.get().strip()
        nonlocal dialog_done
        dialog_done = True
        root.destroy()

    def on_cancel():
        nonlocal dialog_done
        dialog_done = True
        root.destroy()

    root = tk.Tk()
    root.title(f"Счёт №{invoice} — Поставщик")
    root.attributes("-topmost", True)
    root.resizable(False, False)

    # Показываем свободные позиции
    remaining_str = ", ".join(str(p) for p in remaining_positions)
    tk.Label(root, text=f"Свободные позиции ({len(remaining_positions)}):",
             font=("Segoe UI", 9, "bold")).pack(padx=15, pady=(10, 0), anchor="w")
    tk.Label(root, text=remaining_str,
             font=("Segoe UI", 16, "bold"), fg="#0066CC").pack(padx=15, pady=(0, 10), anchor="w")

    # Поля ввода
    section = tk.LabelFrame(root, text="  🏭 Поставщик и позиции  ", font=("Segoe UI", 9, "bold"), padx=10, pady=5)
    section.pack(padx=10, pady=5, fill="x")

    tk.Label(section, text="Формат: 1,2,4 — ВИА", font=("Segoe UI", 8), fg="gray").grid(row=0, column=0, columnspan=2, sticky="w")
    tk.Label(section, text="Поз. — Поставщик:", font=("Segoe UI", 9)).grid(row=1, column=0, sticky="w", pady=2)
    entry_positions = tk.Entry(section, width=35, font=("Segoe UI", 9))
    entry_positions.grid(row=1, column=1, sticky="ew", pady=2)

    # Добавляем отдельное поле для поставщика (если формат с разделителем не сработает)
    # Но пока используем один формат: "1,2,4 — ВИА"
    entry_supplier = None  # не используется в текущей схеме

    entry_positions.focus_set()

    # Кнопки
    btn_frame = tk.Frame(root)
    btn_frame.pack(pady=(5, 10))
    tk.Button(btn_frame, text="OK", width=12, font=("Segoe UI", 9, "bold"),
              bg="#4CAF50", fg="white", command=on_ok).pack(side="left", padx=5)
    tk.Button(btn_frame, text="Отмена", width=12, font=("Segoe UI", 9),
              command=on_cancel).pack(side="left", padx=5)

    root.bind("<Return>", lambda e: on_ok())
    root.bind("<Escape>", lambda e: on_cancel())
    _center_window(root)
    root.mainloop()

    if not dialog_done or not result["input_text"]:
        return None

    # ==========================================
    # Парсим ввод: "1,2,4 — ВИА" или "1,2,4 - ВИА"
    # ==========================================
    input_text = result["input_text"]

    # Пробуем разделить по "—" (длинное тире) или "-" (короткое)
    parts = None
    for separator in [" — ", " - ", " —  ", " —\t", " -\t"]:
        if separator in input_text:
            parts = input_text.split(separator, 1)
            break

    if parts is None or len(parts) != 2:
        # Не смогли разделить — просим переписать
        return "Формат: позиции — поставщик\nПример: 1,2,4 — ВИА"

    positions_str = parts[0].strip()  # "1,2,4"
    supplier = parts[1].strip()       # "ВИА"

    # Превращаем "1,2,4" в список чисел [1, 2, 4]
    try:
        parsed_positions = []
        for p in positions_str.split(","):
            p = p.strip()
            if not p:
                continue
            parsed_positions.append(int(p))
    except ValueError:
        return f"Позиции должны быть числами.\nБыло: '{positions_str}'"

    # Проверяем: все ли введённые позиции — свободные
    for p in parsed_positions:
        if p not in remaining_positions:
            remaining_str = ", ".join(str(x) for x in remaining_positions)
            return f"Позиция {p} уже занята или не существует.\nСвободные: {remaining_str}"

    return supplier, parsed_positions

# ==========================================
# ЛОГИКА РАБОТЫ С ФАЙЛОМ (НОВЫЙ FLOW)
# ==========================================
def process_pdf(filepath):
    """
    Обрабатывает PDF-счёт: читает → диалог → распределение позиций → запись.

    Новый flow:
      1. Извлекаем номер, дата, клиент, кол-во из PDF
      2. Окошко 1: Менеджер + Форма оплаты (один раз)
      3. Окошко 2 (цикл): Позиции → Поставщик
         - Бот показывает свободные позиции
         - Менеджер вводит "1,2,4 — ВИА"
         - Бот отмечает позиции как занятые
         - Если остались свободные — окошко снова
         - Если все распределены — завершаем
      4. Запись в Google Sheets (одна строка на поставщика)
      5. Переименование файла + уведомление
    """
    logger.info(f"Обнаружен новый файл: {filepath}")

    # 1. Извлекаем номер счета ИЗ НАЗВАНИЯ ФАЙЛА
    filename = os.path.basename(filepath)
    invoice = "Неизвестно"

    if "№" in filename:
        start = filename.find("№") + 1
        end = filename.find(" от", start)
        if end == -1: end = len(filename) - 4
        invoice = filename[start:end].strip()

    # 1b. Извлекаем дату из названия
    invoice_date = extract_invoice_date(filename)

    logger.info(f"Номер счёта: {invoice}, Дата: {invoice_date}")

    # ==========================================
    # ШАГ 2: Читаем PDF
    # ==========================================
    try:
        with pdfplumber.open(filepath) as pdf:
            text = pdf.pages[0].extract_text()

        if not text:
            raise ValueError("PDF не содержит текста. Возможно, это скан-копия.")

        # Нормализуем текст: ё → е (в разных шрифтах ё может быть как 'ё' так и 'е')
        text = text.replace("ё", "е").replace("Ё", "Е")

    except Exception as e:
        error_msg = f"Не удалось прочитать PDF '{filename}': {e}"
        logger.error(error_msg)
        show_notification("⚠️ Ошибка чтения PDF", error_msg)
        return

    # ==========================================
    # ШАГ 3: Извлекаем данные из текста
    # ==========================================
    try:
        start_client = text.find("Покупатель") + len("Покупатель")
        if start_client == len("Покупатель") - 1:
            raise ValueError("В PDF не найдено слово 'Покупатель'. Проверьте формат счёта.")
        end_client = text.find("\n", start_client)
        client = text[start_client:end_client].strip()

        start_qty = text.find("Всего наименований") + len("Всего наименований")
        if start_qty == len("Всего наименований") - 1:
            raise ValueError("В PDF не найдено 'Всего наименований'. Проверьте формат счёта.")
        end_qty = text.find(",", start_qty)
        qty = text[start_qty:end_qty].strip()
        qty_int = int(qty.strip())

    except ValueError as e:
        error_msg = f"Неправильный формат счёта '{filename}': {e}"
        logger.error(error_msg)
        show_notification("⚠️ Неверный формат счёта", str(e))
        return
    except Exception as e:
        error_msg = f"Неожиданная ошибка при извлечении данных из '{filename}': {e}"
        logger.error(error_msg)
        show_notification("⚠️ Ошибка обработки", error_msg)
        return

    logger.info(f"Клиент: {client}, Позиций: {qty_int}")

    # ==========================================
    # ШАГ 4: Читаем справочник + Окошко 1
    # ==========================================
    # Загружаем справочник контактов (для автодополнения в диалоге)
    contacts = get_contacts_list()

    invoice_data = show_invoice_dialog(
        invoice, invoice_date, client, qty_int,
        default_manager="",
        contacts=contacts
    )
    if invoice_data is None:
        logger.info("Менеджер отменил ввод. Обработка прервана.")
        show_notification("⚠️ Ввод отменён", f"Счёт №{invoice} не добавлен")
        return

    designer, manager, payment_form = invoice_data

    # Проверяем имена по справочнику, предлагаем добавить если нет
    designer = check_and_offer_add(designer, "дизайнер", contacts.get("дизайнеры", []))
    manager = check_and_offer_add(manager, "менеджер", contacts.get("менеджеры", []))

    logger.info(f"Дизайнер: {designer}, Менеджер: {manager}, Оплата: {payment_form}")

    # ==========================================
    # ШАГ 5: Подключаемся к Google Sheets
    # ==========================================
    try:
        gc = gspread.service_account(filename="key.json")
        spreadsheet = gc.open_by_url(SHEET_URL)
        worksheet = spreadsheet.sheet1
    except FileNotFoundError:
        error_msg = "Файл key.json не найден! Проверьте, что он лежит рядом с bot.py"
        logger.critical(error_msg)
        show_notification("🚨 КРИТИЧЕСКАЯ ОШИБКА", error_msg)
        return
    except gspread.exceptions.SpreadsheetNotFound:
        error_msg = "Нет доступа к Google Sheets. Проверьте ссылку и права key.json"
        logger.error(error_msg)
        show_notification("⚠️ Нет доступа к таблице", error_msg)
        return
    except Exception as e:
        error_msg = f"Ошибка подключения к Google Sheets: {e}"
        logger.error(error_msg)
        show_notification("⚠️ Нет связи с Google", "Проверьте интернет-подключение")
        return

    # ==========================================
    # ШАГ 6: ЦИКЛ — распределение позиций по поставщикам
    # ==========================================
    # remaining — список свободных позиций.
    # started с [1, 2, 3, ..., qty_int], и убираем по мере ввода.
    remaining = list(range(1, qty_int + 1))
    supplier_rows = []  # Accumulate: [(supplier, positions_str), ...]
    supplier_hint = ""   # Подставка названия поставщика при ошибке

    while remaining:
        # Показываем окошко: свободные позиции + поле ввода
        result = show_supplier_dialog(remaining, invoice, supplier_hint)

        if result is None:
            # Менеджер нажал "Отмена"
            logger.info("Менеджер отменил распределение позиций.")
            show_notification("⚠️ Ввод отменён", f"Счёт №{invoice} не добавлен")
            return

        # Если result — строка, это ошибка ввода
        if isinstance(result, str):
            show_notification("⚠️ Ошибка ввода", result, duration=8)
            # Не обновляем remaining — показываем то же окно снова
            # supplier_hint сохраняем пустым — ошибка была в формате
            continue

        # result — кортеж (supplier, positions_list)
        supplier, positions = result
        supplier_hint = supplier  # Запоминаем на случай ошибки в следующем вводе

        # Убираем занятые позиции из remaining
        for p in positions:
            remaining.remove(p)

        positions_str = ",".join(str(p) for p in positions)
        supplier_rows.append((supplier, positions_str))
        supplier_hint = ""  # Сбрасываем подсказку после успешного ввода

        logger.info(f"Поставщик '{supplier}' — поз. {positions_str} (осталось {len(remaining)})")

    # ==========================================
    # ШАГ 7: Записываем ВСЕ строки в Google Sheets
    # ==========================================
    try:
        for supplier, positions_str in supplier_rows:
            # Порядок столбцов по таблице:
            # A: № счёта, B: Дата, C: Клиент, D: Дизайнер, E: к-во поз.,
            # F: Уведомлено, G: Позиции ПОСТ, H: Поставщик, I: № счета ПОСТ / дата,
            # J: Дата опл ПОСТ, K: Дата отгр, L: Отправка в тк,
            # M: Дата прихода ТК КЗН, N: Дата прихода СКЛАД,
            # O: Дополнительно, P: Менеджер, Q: Форма оплаты
            new_row = [
                invoice,        # A
                invoice_date,   # B
                client,         # C
                designer,       # D
                qty_int,        # E
                "",             # F — Уведомлено (пока пусто)
                positions_str,  # G
                supplier,       # H
                "",             # I — № счета ПОСТ / дата (логист)
                "",             # J — Дата опл ПОСТ (логист)
                "",             # K — Дата отгр (логист)
                "",             # L — Отправка в тк (логист)
                "",             # M — Дата прихода ТК КЗН (логист)
                "",             # N — Дата прихода СКЛАД (логист)
                "",             # O — Дополнительно (логист)
                manager,        # P
                payment_form,   # Q
            ]
            worksheet.append_row(new_row)

        logger.info(f"Записано {len(supplier_rows)} строк в таблицу")

        # ==========================================
        # Объединяем одинаковые ячейки (если >1 поставщика)
        # ==========================================
        if len(supplier_rows) > 1:
            all_data = worksheet.get_all_values()
            last_row = len(all_data)
            first_row = last_row - len(supplier_rows) + 1

            # Столбцы для объединения: A(1), B(2), C(3), D(4), E(5), P(16), Q(17)
            merge_cols = {1: "A", 2: "B", 3: "C", 4: "D", 5: "E", 16: "P", 17: "Q"}

            for col_num, letter in merge_cols.items():
                range_str = f"{letter}{first_row}:{letter}{last_row}"
                try:
                    worksheet.merge_cells(range_str)
                    logger.info(f"Объединены: {range_str}")
                except Exception as e:
                    logger.warning(f"Не удалось объединить {range_str}: {e}")

        # ==========================================
        # Визуальное оформление: полоса под счётом
        # ==========================================
        # Добавляем толстую нижнюю границу на последней строке счёта,
        # чтобы визуально отделить один заказ от другого.
        try:
            all_data = worksheet.get_all_values()
            last_row = len(all_data)

            # Стиль: толстая сплошная линия снизу, тёмно-синяя (#4472C4)
            border_format = {
                "borders": {
                    "bottom": {
                        "style": "SOLID",
                        "width": 2,
                        "color": {"red": 0.27, "green": 0.45, "blue": 0.77}
                    }
                }
            }

            # Применяем ко всем столбцам A-Q последней строки
            worksheet.format(f"A{last_row}:Q{last_row}", border_format)
            logger.info(f"Полоса-разделитель добавлена на строку {last_row}")
        except Exception as e:
            logger.warning(f"Не удалось добавить полосу: {e}")

    except Exception as e:
        error_msg = f"Ошибка записи в таблицу: {e}"
        logger.error(error_msg)
        show_notification("⚠️ Ошибка записи", error_msg)
        return

    # ==========================================
    # ШАГ 8: Завершение — переименовать файл
    # ==========================================
    try:
        base, ext = os.path.splitext(filepath)
        new_filepath = f"{base}_ОБРАБОТАНО{ext}"
        os.rename(filepath, new_filepath)
        logger.info(f"Файл переименован: {os.path.basename(new_filepath)}")
    except Exception as e:
        logger.error(f"Не удалось переименовать файл: {e}")

    # Уведомление об успехе
    show_notification(
        "✅ Счёт обработан",
        f"Счёт №{invoice} — {client}\nДобавлено {len(supplier_rows)} поставщиков",
        duration=7
    )


# ==========================================
# ЛОГИКА СЛУШАТЕЛЯ ПАПКИ (WATCHDOG)
# ==========================================
class PdfHandler(FileSystemEventHandler):
    def on_created(self, event):
        # Если создали не файл, или это не PDF - игнорируем
        if event.is_directory or not event.src_path.endswith(".pdf"): 
            return
        
        # Windows иногда блокирует файл на секунду при копировании, ждем чуть-чуть
        time.sleep(1) 
        process_pdf(event.src_path)

# ==========================================
# ЗАПУСК ПРОГРАММЫ
# ==========================================
def show_welcome_screen():
    """
    Приветственное окно при ПЕРВОМ запуске.

    Показывает:
    - ссылку на Google Таблицу (с кнопкой "Открыть")
    - ссылку на инструкцию
    - кнопку "Продолжить" → выбор папки

    Возвращает True если пользователь нажал "Продолжить".
    """
    import tkinter as tk
    import webbrowser

    result = {"continue": False}

    def on_continue():
        result["continue"] = True
        root.destroy()

    def open_sheet():
        webbrowser.open(SHEET_URL)

    def open_instructions():
        # Ссылка на инструкцию в Google Doc
        webbrowser.open("https://docs.google.com/document/d/1dkYN-TVIqcA86mI10_yEcQwLTCitzZgHf1o6-9huCik/edit")

    root = tk.Tk()
    root.title("Добро пожаловать! PDF-бот Аганим")
    root.attributes("-topmost", True)
    root.resizable(False, False)
    root.configure(padx=20, pady=20)

    # Заголовок
    tk.Label(root, text="🤖 PDF-бот Аганим",
             font=("Segoe UI", 16, "bold"), fg="#0066CC").pack(pady=(0, 10))

    tk.Label(root, text="Программа для автоматического добавления счетов в таблицу.",
             font=("Segoe UI", 9), wraplength=400).pack(pady=(0, 20))

    # Полезные ссылки
    links_frame = tk.LabelFrame(root, text="  📌 Полезные ссылки  ",
                                  font=("Segoe UI", 9, "bold"), padx=10, pady=10)
    links_frame.pack(fill="x", pady=(0, 20))

    tk.Button(links_frame, text="📊 Открыть Google Таблицу",
              font=("Segoe UI", 9), command=open_sheet).pack(fill="x", pady=2)

    tk.Button(links_frame, text="📖 Открыть инструкцию по работе",
              font=("Segoe UI", 9), command=open_instructions).pack(fill="x", pady=2)

    # Информация
    tk.Label(root, text="⚠️ Не удаляйте и не перемещайте файл key.json — \nбез него бот не сможет работать!",
             font=("Segoe UI", 8), fg="red", justify="center").pack(pady=(0, 15))

    # Кнопка продолжить
    tk.Button(root, text="Продолжить →", width=20, font=("Segoe UI", 10, "bold"),
              bg="#4CAF50", fg="white", command=on_continue).pack()

    _center_window(root)
    root.mainloop()

    return result["continue"]


def main():
    folder_path = ""

    # Проверяем, есть ли сохраненный путь
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
                folder_path = config.get("folder_path", "")
        except Exception as e:
            logger.error(f"Ошибка чтения config.json: {e}")

    # Если пути нет — это первый запуск
    if not folder_path or not os.path.exists(folder_path):
        # Показываем приветственное окно
        show_welcome_screen()

        logger.info("Первый запуск! Выбор папки для счетов...")
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw() # Прячем главное окно
        folder_path = filedialog.askdirectory(title="Выберите папку для счетов")

        if not folder_path:
            logger.info("Папка не выбрана. Программа закрыта.")
            return

        # Сохраняем выбор в config.json
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({"folder_path": folder_path}, f, ensure_ascii=False, indent=4)
        logger.info(f"Папка сохранена: {folder_path}")

    logger.info("==================================================")
    logger.info("БОТ ЗАПУЩЕН И СЛУШАЕТ ПАПКУ...")
    logger.info(f"Папка: {folder_path}")
    logger.info("==================================================")

    # Запускаем слушателя
    event_handler = PdfHandler()
    observer = Observer()
    observer.schedule(event_handler, folder_path, recursive=False)
    observer.start()

    # Бесконечный цикл, чтобы программа не закрылась
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # Это СТРОЖАЙШИЙ уровень — программа вообще не смогла запуститься.
        # Например: watchdog не установлен, или Python сломан.
        logger.critical(f"КРИТИЧЕСКАЯ ОШИБКА: {e}", exc_info=True)
        # exc_info=True — добавляет в лог полный стекtrace (откуда именно упали)
        show_notification("🚨 Бот не запустился", f"Ошибка: {e}")