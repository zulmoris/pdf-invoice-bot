import pdfplumber
import gspread
import os
import json
# МАГИЯ ПУТЕЙ: Заставляем Питона всегда работать в папке со скриптом
import sys
os.chdir(os.path.dirname(os.path.abspath(__file__)))
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# ВАША ССЫЛКА НА ТАБЛИЦУ
SHEET_URL = "https://docs.google.com/spreadsheets/d/1phaXa8GZo8W3xnzpdFYPs_cjng2WmvkTxFctkjnGoUU/edit?gid=0#gid=0" 

# Файл, где будет храниться путь к папке
CONFIG_FILE = "config.json"

# ==========================================
# ЛОГИКА РАБОТЫ С ФАЙЛОМ
# ==========================================
def process_pdf(filepath):
    print(f"\n[!] Обнаружен новый файл: {filepath}")
    
    # 1. Извлекаем номер счета ИЗ НАЗВАНИЯ ФАЙЛА
    # Пример: "Счет на оплату № 921 от 30 мая 2026 г.pdf"
    filename = os.path.basename(filepath)
    invoice = "Неизвестно"
    
    if "№" in filename:
        start = filename.find("№") + 1
        end = filename.find(" от", start)
        if end == -1: end = len(filename) - 4 # обрезаем .pdf
        invoice = filename[start:end].strip()

    # 2. Читаем PDF (Ищем только Клиента и Кол-во)
    try:
        with pdfplumber.open(filepath) as pdf:
            text = pdf.pages[0].extract_text()

        start_client = text.find("Покупатель") + len("Покупатель")
        end_client = text.find("\n", start_client)
        client = text[start_client:end_client].strip()

        start_qty = text.find("Всего наименований") + len("Всего наименований")
        end_qty = text.find(",", start_qty)
        qty = text[start_qty:end_qty].strip()
        qty_int = int(qty.strip())
        
        post_statuses = ["ПОСТ"] * qty_int
        new_row = [invoice, client, "", "", qty_int, ""] + post_statuses

        # 3. Подключаемся к Гугл Таблице
        gc = gspread.service_account(filename="key.json")
        spreadsheet = gc.open_by_url(SHEET_URL)
        worksheet = spreadsheet.sheet1 

        # --- ЛОГИКА: ПОИСК ДУБЛИКАТА И ПОДКРАШИВАНИЕ ---
        print("Проверяю на дубликаты...")
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
            print(f"[!] ОБНАРУЖЕН ДУБЛИКАТ в строке {matched_row}! Подсвечиваем обе строки.")
            # Красим старую строку
            worksheet.format(f"A{matched_row}:Z{matched_row}", yellow_format)
            # Красим новую строку
            worksheet.format(f"A{new_row_num}:Z{new_row_num}", yellow_format)
        else:
            print(f"[+] Успешно добавлено в таблицу: Счет {invoice}, Клиент: {client}")
        # ----------------------------------------

        # 4. Файл НЕ трогаем, оставляем в папке!
        print(f"[*] Файл оставлен в папке: {os.path.basename(filepath)}")

        # 4. Переименовываем файл, чтобы не обрабатывать дважды
        base, ext = os.path.splitext(filepath)
        new_filepath = f"{base}_ОБРАБОТАНО{ext}"
        os.rename(filepath, new_filepath)
        print(f"[*] Файл переименован в: {os.path.basename(new_filepath)}")

    except Exception as e:
        print(f"[!] ОШИБКА при обработке файла: {e}")

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
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
            folder_path = config.get("folder_path", "")

    # Если пути нет, просим пользователя выбрать папку
    if not folder_path or not os.path.exists(folder_path):
        print("первый запуск! Выберите папку, куда менеджеры будут кидать счета.")
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw() # Прячем главное окно
        folder_path = filedialog.askdirectory(title="Выберите папку для счетов")
        
        if not folder_path:
            print("Папка не выбрана. Программа закрыта.")
            return
            
        # Сохраняем выбор в config.json
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({"folder_path": folder_path}, f, ensure_ascii=False, indent=4)
        print(f"Папка сохранена: {folder_path}")

    print("==================================================")
    print("🤖 БОТ ЗАПУЩЕН И СЛУШАЕТ ПАПКУ...")
    print(f"📁 Папка: {folder_path}")
    print("(!) Не закрывайте это окно. Чтобы остановить, нажмите Ctrl+C")
    print("==================================================")

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
        print(f"\n!!! КРИТИЧЕСКАЯ ОШИБКА !!!")
        print(f"Текст ошибки: {e}")
        print("\nОкно не закроется, пока не нажмешь Enter. Скопируй ошибку и пришли Дамиру.")
        input() # ЗАСТАВЛЯЕТ ОКНО ЖДАТЬ НАЖАТИЯ КЛАВИШИ