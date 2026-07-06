import pdfplumber
import gspread
import os
import json
import logging
from datetime import datetime
# МАГИЯ ПУТЕЙ: Заставляем Питона всегда работать в папке со скриптом
import sys
os.chdir(os.path.dirname(os.path.abspath(__file__)))
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

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
# win10toast — это библиотека, которая показывает всплывающие уведомления
# в правом нижнем углу экрана (как уведомления от Skype, Telegram и т.д.)
#
# УСТАНОВКА: pip install win10toast
#
# ЗАЧЕМ: Вместо страшного красного окна менеджер увидит аккуратное
# уведомление: "⚠️ Ошибка обработки счёта" с кратким описанием.

try:
    from win10toast import ToastNotifier
    toaster = ToastNotifier()
    TOAST_AVAILABLE = True
except ImportError:
    # Если библиотека не установлена — не крашимся, просто уведомления не будут работать
    TOAST_AVAILABLE = False
    logger.warning("win10toast не установлен. Уведомления отключены. pip install win10toast")


def show_notification(title, message, duration=5):
    """
    Показывает всплывающее уведомление в Windows.

    title    — заголовок уведомления (короткий, например "✅ Счёт обработан")
    message  — текст уведомления (подробности)
    duration — сколько секунд показывать (по умолчанию 5)

    Функция безопасна: если win10toast не установлен — просто запишет в лог.
    """
    if TOAST_AVAILABLE:
        try:
            toaster.show_toast(title, message, duration=duration, threaded=True)
            # threaded=True означает, что уведомление показывается в фоне
            # и программа не ждёт, пока менеджер нажмёт на него
        except Exception as e:
            logger.error(f"Не удалось показать уведомление: {e}")
    else:
        logger.info(f"[УВЕДОМЛЕНИЕ] {title}: {message}")
SHEET_URL = "https://docs.google.com/spreadsheets/d/1phaXa8GZo8W3xnzpdFYPs_cjng2WmvkTxFctkjnGoUU/edit?gid=0#gid=0" 

# Файл, где будет храниться путь к папке
CONFIG_FILE = "config.json"

# ==========================================
# ЛОГИКА РАБОТЫ С ФАЙЛОМ
# ==========================================
def process_pdf(filepath):
    logger.info(f"Обнаружен новый файл: {filepath}")

    # 1. Извлекаем номер счета ИЗ НАЗВАНИЯ ФАЙЛА
    # Пример: "Счет на оплату № 921 от 30 мая 2026 г.pdf"
    filename = os.path.basename(filepath)
    invoice = "Неизвестно"

    if "№" in filename:
        start = filename.find("№") + 1
        end = filename.find(" от", start)
        if end == -1: end = len(filename) - 4 # обрезаем .pdf
        invoice = filename[start:end].strip()
    logger.info(f"Номер счета из названия: {invoice}")

    # ==========================================
    # ШАГ 2: Читаем PDF
    # ==========================================
    try:
        with pdfplumber.open(filepath) as pdf:
            text = pdf.pages[0].extract_text()

        # Проверяем, что текст вообще извлёкся (бывает, что PDF-скан без текста)
        if not text:
            raise ValueError("PDF не содержит текста. Возможно, это скан-копия.")

    except Exception as e:
        # ОШИБКА: Не смогли прочитать PDF
        error_msg = f"Не удалось прочитать PDF '{filename}': {e}"
        logger.error(error_msg)
        show_notification("⚠️ Ошибка чтения PDF", error_msg)
        return  # Прерываем обработку — смысла продолжать нет

    # ==========================================
    # ШАГ 3: Извлекаем данные из текста
    # ==========================================
    try:
        start_client = text.find("Покупатель") + len("Покупатель")
        if start_client == len("Покупатель") - 1:
            # find() возвращает -1 если не нашёл. Значит + len() даст -1 + len =<len
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
        # ОШИБКА: Формат PDF отличается от ожидаемого
        error_msg = f"Неправильный формат счёта '{filename}': {e}"
        logger.error(error_msg)
        show_notification("⚠️ Неверный формат счёта", str(e))
        return

    except Exception as e:
        # ОШИБКА: Что-то непредвиденное при извлечении данных
        error_msg = f"Неожиданная ошибка при извлечении данных из '{filename}': {e}"
        logger.error(error_msg)
        show_notification("⚠️ Ошибка обработки", error_msg)
        return

    logger.info(f"Клиент: {client}, Позиций: {qty_int}")

    post_statuses = ["ПОСТ"] * qty_int
    new_row = [invoice, client, "", "", qty_int, ""] + post_statuses

    # ==========================================
    # ШАГ 4: Подключаемся к Google Sheets
    # ==========================================
    try:
        gc = gspread.service_account(filename="key.json")
        spreadsheet = gc.open_by_url(SHEET_URL)
        worksheet = spreadsheet.sheet1
    except FileNotFoundError:
        # ОШИБКА: Нет файла ключа
        error_msg = "Файл key.json не найден! Проверьте, что он лежит рядом с bot.py"
        logger.critical(error_msg)
        show_notification("🚨 КРИТИЧЕСКАЯ ОШИБКА", error_msg)
        return
    except gspread.exceptions.SpreadsheetNotFound:
        # ОШИБКА: Нет доступа к таблице
        error_msg = f"Нет доступа к Google Sheets. Проверьте ссылку и права key.json"
        logger.error(error_msg)
        show_notification("⚠️ Нет доступа к таблице", error_msg)
        return
    except Exception as e:
        # ОШИБКА: Нет интернета или другая проблема подключения
        error_msg = f"Ошибка подключения к Google Sheets: {e}"
        logger.error(error_msg)
        show_notification("⚠️ Нет связи с Google", "Проверьте интернет-подключение")
        return

    # ==========================================
    # ШАГ 5: Записываем в таблицу
    # ==========================================
    try:
        logger.info("Проверяю на дубликаты...")
        existing_data = worksheet.get_all_values()
        is_duplicate = False
        matched_row = None

        for i, row in enumerate(existing_data[1:], start=2):
            if len(row) > 4:
                ex_invoice = str(row[0]).strip()
                ex_client = str(row[1]).strip()
                ex_qty = str(row[4]).strip()

                if ex_invoice == str(invoice).strip() and ex_client == client.strip() and ex_qty == str(qty_int):
                    is_duplicate = True
                    matched_row = i
                    break

        # ВСЕГДА добавляем новую строку
        worksheet.append_row(new_row)
        new_row_num = len(existing_data) + 1 # Вычисляем номер новой строки

        # Настройка желтого цвета
        yellow_format = {
            "backgroundColor": {"red": 1.0, "green": 1.0, "blue": 0.0}
        }

        if is_duplicate:
            logger.warning(f"ОБНАРУЖЕН ДУБЛИКАТ в строке {matched_row}! Подсвечиваем обе строки.")
            # Красим старую строку
            worksheet.format(f"A{matched_row}:Z{matched_row}", yellow_format)
            # Красим новую строку
            worksheet.format(f"A{new_row_num}:Z{new_row_num}", yellow_format)
        else:
            logger.info(f"Успешно добавлено: Счет {invoice}, Клиент: {client}")

        # Переименовываем файл, чтобы не обрабатывать дважды
        base, ext = os.path.splitext(filepath)
        new_filepath = f"{base}_ОБРАБОТАНО{ext}"
        os.rename(filepath, new_filepath)
        logger.info(f"Файл переименован: {os.path.basename(new_filepath)}")

        # Уведомляем менеджера об успехе!
        show_notification("✅ Счёт обработан", f"Счёт №{invoice} — {client} ({qty_int} поз.)")

    except Exception as e:
        # ОШИБКА: Что-то пошло не так при записи в таблицу
        error_msg = f"Ошибка записи в таблицу для '{filename}': {e}"
        logger.error(error_msg)
        show_notification("⚠️ Ошибка записи", "Не удалось записать в Google Sheets")

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

    # Если пути нет, просим пользователя выбрать папку
    if not folder_path or not os.path.exists(folder_path):
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