"""
Мини-утилита: меняет рабочий Telegram ID в таблице.

Показывает окошко с полем ввода — менеджер вставляет новый ID,
программа записывает его во вкладку "Настройки" Google Sheets.
"""
import gspread
import tkinter as tk
from tkinter import messagebox

# Ссылка на таблицу (та же что в основном боте)
SHEET_URL = "https://docs.google.com/spreadsheets/d/1QkXocbAJu1a5rcu3XNEfpHnoF_mA5flgehjO6E7VIWM/edit?usp=sharing"


def main():
    # ==========================================
    # Читаем текущий ID из таблицы
    # ==========================================
    try:
        gc = gspread.service_account(filename="key.json")
        spreadsheet = gc.open_by_url(SHEET_URL)

        # Получаем (или создаём) вкладку "Настройки"
        try:
            settings = spreadsheet.worksheet("Настройки")
            current_id = settings.get("B1").first()
            if not current_id:
                current_id = "438544636"
        except gspread.exceptions.WorksheetNotFound:
            current_id = "438544636"  # вкладки пока нет — покажем дефолт
    except Exception as e:
        messagebox.showerror("Ошибка", f"Не удалось подключиться к таблице:\n{e}")
        return

    # ==========================================
    # Окошко ввода
    # ==========================================
    result = {"id": None, "done": False}

    def on_save():
        new_id = entry.get().strip()
        if not new_id:
            messagebox.showwarning("Пусто", "Введите ID!")
            return
        if not new_id.lstrip("-").isdigit():
            messagebox.showwarning("Ошибка", "ID должен быть числом!\n"
                                          "Например: 438544636")
            return
        result["id"] = new_id
        result["done"] = True
        root.destroy()

    def on_cancel():
        result["done"] = True
        root.destroy()

    root = tk.Tk()
    root.title("Смена рабочего Telegram ID")
    root.attributes("-topmost", True)
    root.resizable(False, False)
    root.configure(padx=20, pady=20)

    tk.Label(root, text="🔑 Смена рабочего Telegram ID",
             font=("Segoe UI", 12, "bold"), fg="#0066CC").pack(pady=(0, 10))

    tk.Label(root, text=f"Текущий ID: {current_id}",
             font=("Segoe UI", 9), fg="gray").pack(pady=(0, 15))

    tk.Label(root, text="Введите новый ID:",
             font=("Segoe UI", 9)).pack(anchor="w")

    entry = tk.Entry(root, width=30, font=("Segoe UI", 11))
    entry.pack(pady=5)
    entry.insert(0, current_id)
    entry.focus_set()

    btn_frame = tk.Frame(root)
    btn_frame.pack(pady=(15, 0))

    tk.Button(btn_frame, text="💾 Сохранить", width=12,
              font=("Segoe UI", 9, "bold"), bg="#4CAF50", fg="white",
              command=on_save).pack(side="left", padx=5)
    tk.Button(btn_frame, text="Отмена", width=12,
              font=("Segoe UI", 9), command=on_cancel).pack(side="left", padx=5)

    root.bind("<Return>", lambda e: on_save())
    root.bind("<Escape>", lambda e: on_cancel())

    # Центрируем
    root.update_idletasks()
    w = root.winfo_width()
    h = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (w // 2)
    y = (root.winfo_screenheight() // 2) - (h // 2)
    root.geometry(f"+{x}+{y}")

    root.mainloop()

    # ==========================================
    # Сохраняем новый ID в таблицу
    # ==========================================
    if result["done"] and result["id"] and result["id"] != current_id:
        try:
            # Создаём вкладку "Настройки" если её нет
            try:
                settings = spreadsheet.worksheet("Настройки")
            except gspread.exceptions.WorksheetNotFound:
                settings = spreadsheet.add_worksheet("Настройки", rows=10, cols=2)
                settings.update("A1", [["Рабочий Telegram ID"]])

            # Записываем новый ID в B1
            settings.update("B1", [[result["id"]]])
            messagebox.showinfo("Готово", f"✅ ID изменён на: {result['id']}\n\n"
                                          f"Теперь уведомления пойдут на новый номер.")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить:\n{e}")


if __name__ == "__main__":
    main()
