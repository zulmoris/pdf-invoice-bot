"""
Демо Telegram-бот для портфолио.
Функции:
  - Главное меню с красивой клавиатурой
  - Каталог услуг с фотографиями
  - Запись на консультацию (сохраняет в JSON)
  - Статистика посещений
  - Генерация PDF-отчёта по записям
  - Админ-панель (/admin)
  
Показывает клиентам, что умею:
  - Inline-клавиатуры и callback-обработка
  - Работа с данными (сохранение, поиск, агрегация)
  - PDF-генерация
  - Админ-функции
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, ReplyKeyboardRemove
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

# ==========================================
# НАСТРОЙКИ
# ==========================================
BOT_TOKEN = os.getenv("DEMO_BOT_TOKEN", "ВАШ_ТОКЕН_ЗДЕСЬ")
DATA_DIR = Path(__file__).parent / "bot_data"
DATA_DIR.mkdir(exist_ok=True)
BOOKINGS_FILE = DATA_DIR / "bookings.json"
VISITS_FILE = DATA_DIR / "visits.json"

# Настройки логирования
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# ==========================================
# УТИЛИТЫ ДЛЯ РАБОТЫ С ДАННЫМИ
# ==========================================
def _safe_data_path(path: Path) -> Path | None:
    """Пропускает только пути внутри DATA_DIR (resolve устраняет ../)."""
    try:
        resolved = path.resolve()
        base = DATA_DIR.resolve()
        if resolved == base or base in resolved.parents:
            return resolved
    except Exception:
        pass
    return None


def load_json(path: Path) -> list:
    """Загружает JSON-файл или возвращает пустой список.
    Читает только из DATA_DIR (защита от выхода за пределы папки данных)."""
    safe = _safe_data_path(path)
    if safe and safe.is_file():
        try:
            return json.loads(safe.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, IOError):
            return []
    return []


def save_json(path: Path, data: list):
    """Сохраняет список в JSON-файл.
    Пишет только в DATA_DIR (защита от выхода за пределы папки данных)."""
    safe = _safe_data_path(path)
    if not safe:
        logger.warning("Отказ записи: путь вне папки данных (%s)", path)
        return
    try:
        safe.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except IOError as e:
        logger.error("Ошибка записи %s: %s", safe, e)


def track_visit(user_id: int, username: str):
    """Записывает посещение для статистики."""
    visits = load_json(VISITS_FILE)
    today = datetime.now().strftime("%Y-%m-%d")
    visits.append({
        "user_id": user_id,
        "username": username,
        "date": today,
        "time": datetime.now().strftime("%H:%M")
    })
    save_json(VISITS_FILE, visits)


# ==========================================
# ГЕНЕРАЦИЯ PDF-ОТЧЁТА
# ==========================================
def generate_report() -> str | None:
    """
    Генерирует PDF-отчёт по записям.
    Возвращает путь к файлу или None.
    """
    bookings = load_json(BOOKINGS_FILE)
    if not bookings:
        return None

    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.colors import HexColor
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer,
            Table, TableStyle
        )

        pdf_path = DATA_DIR / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

        doc = SimpleDocTemplate(
            str(pdf_path), pagesize=A4,
            leftMargin=20 * mm, rightMargin=20 * mm,
            topMargin=20 * mm, bottomMargin=20 * mm
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "CustomTitle", parent=styles["Title"],
            fontSize=20, spaceAfter=20,
            textColor=HexColor("#1a1a2e")
        )
        subtitle_style = ParagraphStyle(
            "Subtitle", parent=styles["Normal"],
            fontSize=11, textColor=HexColor("#666666"),
            spaceAfter=15
        )

        elements = []
        elements.append(Paragraph("Отчёт по записям", title_style))
        elements.append(Paragraph(
            f"Сформирован: {datetime.now().strftime('%d.%m.%Y в %H:%M')}",
            subtitle_style
        ))
        elements.append(Paragraph(
            f"Всего записей: {len(bookings)}",
            subtitle_style
        ))
        elements.append(Spacer(1, 10 * mm))

        # Таблица записей
        table_data = [["#", "Имя", "Услуга", "Дата", "Контакт"]]
        for i, b in enumerate(bookings, 1):
            table_data.append([
                str(i),
                b.get("name", "—"),
                b.get("service", "—"),
                b.get("date", "—"),
                b.get("contact", "—"),
            ])

        table = Table(table_data, colWidths=[10*mm, 35*mm, 40*mm, 30*mm, 40*mm])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), HexColor("#1a1a2e")),
            ("TEXTCOLOR", (0, 0), (-1, 0), HexColor("#ffffff")),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 10),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
            ("TOPPADDING", (0, 0), (-1, 0), 8),
            ("BACKGROUND", (0, 1), (-1, -1), HexColor("#f8f9fa")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1),
             [HexColor("#f8f9fa"), HexColor("#ffffff")]),
            ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#dee2e6")),
            ("FONTSIZE", (0, 1), (-1, -1), 9),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
            ("TOPPADDING", (0, 1), (-1, -1), 6),
        ]))
        elements.append(table)

        doc.build(elements)
        return str(pdf_path)

    except ImportError:
        logger.warning("reportlab не установлен. Установите: pip install reportlab")
        return None


# ==========================================
# КЛАВИАТУРЫ
# ==========================================
def main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Главная клавиатура бота."""
    return ReplyKeyboardMarkup(
        [
            ["📋 Услуги", "📅 Запись"],
            ["📊 Статистика", "📄 Отчёт (PDF)"],
            ["📞 Контакты", "ℹ️ О нас"],
        ],
        resize_keyboard=True
    )


def services_keyboard() -> InlineKeyboardMarkup:
    """Инлайн-клавиатура с услугами."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💡 Разработка ботов", callback_data="svc_bot"),
            InlineKeyboardButton("🌐 Веб-сайты", callback_data="svc_web"),
        ],
        [
            InlineKeyboardButton("📊 Автоматизация", callback_data="svc_auto"),
            InlineKeyboardButton("📄 PDF-инструменты", callback_data="svc_pdf"),
        ],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_menu")],
    ])


def booking_services_keyboard() -> InlineKeyboardMarkup:
    """Выбор услуги при записи."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Telegram-бот", callback_data="book_bot"),
            InlineKeyboardButton("Веб-сайт", callback_data="book_web"),
        ],
        [
            InlineKeyboardButton("Автоматизация", callback_data="book_auto"),
            InlineKeyboardButton("PDF-генерация", callback_data="book_pdf"),
        ],
        [InlineKeyboardButton("❌ Отмена", callback_data="book_cancel")],
    ])


# ==========================================
# HANDLERS
# ==========================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start."""
    user = update.effective_user
    track_visit(user.id, user.username or "unknown")

    text = (
        f"👋 Привет, <b>{user.first_name}</b>!\n\n"
        "Это демо-бот, показывающий мои навыки разработки.\n"
        "Здесь вы можете посмотреть функционал:\n"
        "• Каталог услуг\n"
        "• Запись на консультацию\n"
        "• Статистика посещений\n"
        "• Генерация PDF-отчёта\n\n"
        "Выберите действие ниже 👇"
    )
    await update.message.reply_text(
        text,
        parse_mode="HTML",
        reply_markup=main_menu_keyboard()
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик всех inline-кнопок."""
    query = update.callback_query
    await query.answer()
    data = query.data

    # --- Услуги ---
    if data == "back_menu":
        await query.message.edit_text(
            "Выберите действие:",
            reply_markup=services_keyboard()
        )
    elif data == "svc_bot":
        await query.message.edit_text(
            "<b>🤖 Разработка Telegram-ботов</b>\n\n"
            "• Боты для бизнеса (запись, меню, оплата)\n"
            "• Боты-уведомления из CRM/Google Sheets\n"
            "• Боты с PDF-генерацией отчётов\n"
            "• Групповые боты с модерацией\n\n"
            "💰 от 3 000 ₽\n"
            "⏱ Срок: 2–5 дней",
            parse_mode="HTML",
            reply_markup=services_keyboard()
        )
    elif data == "svc_web":
        await query.message.edit_text(
            "<b>🌐 Разработка веб-сайтов</b>\n\n"
            "• Лендинги (HTML/CSS/JS)\n"
            "• Веб-приложения (Flask, React)\n"
            "• Адаптивный дизайн под мобильные\n"
            "• SEO-оптимизация\n\n"
            "💰 от 5 000 ₽\n"
            "⏱ Срок: 3–7 дней",
            parse_mode="HTML",
            reply_markup=services_keyboard()
        )
    elif data == "svc_auto":
        await query.message.edit_text(
            "<b>📊 Автоматизация бизнес-процессов</b>\n\n"
            "• Интеграция Telegram + Google Sheets\n"
            "• Автоматические отчёты в PDF\n"
            "• Парсинг и агрегация данных\n"
            "• Connecting CRM + мессенджеры\n\n"
            "💰 от 5 000 ₽\n"
            "⏱ Срок: 5–14 дней",
            parse_mode="HTML",
            reply_markup=services_keyboard()
        )
    elif data == "svc_pdf":
        await query.message.edit_text(
            "<b>📄 PDF-инструменты</b>\n\n"
            "• Генерация PDF-отчётов\n"
            "• Извлечение данных из PDF\n"
            "• Шаблоны документов\n"
            "• Пакетная обработка файлов\n\n"
            "💰 от 2 000 ₽\n"
            "⏱ Срок: 1–3 дня",
            parse_mode="HTML",
            reply_markup=services_keyboard()
        )

    # --- Запись ---
    elif data.startswith("book_") and data != "book_cancel":
        service_map = {
            "book_bot": "Telegram-бот",
            "book_web": "Веб-сайт",
            "book_auto": "Автоматизация",
            "book_pdf": "PDF-генерация",
        }
        context.user_data["booking_service"] = service_map.get(data, "Услуга")
        await query.message.edit_text(
            f"<b>📅 Запись на консультацию</b>\n\n"
            f"Услуга: {context.user_data['booking_service']}\n\n"
            "Отправьте сообщение в формате:\n"
            "<code>Имя | Дата | Контакт</code>\n\n"
            "Пример:\n"
            "<code>Алексей | 15.08 | +7 900 123-45-67</code>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Отмена", callback_data="book_cancel")]
            ])
        )
    elif data == "book_cancel":
        context.user_data.clear()
        await query.message.edit_text(
            "Запись отменена.",
            reply_markup=services_keyboard()
        )

    # --- О нас ---
    elif data == "about":
        await query.message.edit_text(
            "<b>ℹ️ Обо мне</b>\n\n"
            "👋 Привет! Я — разработчик, специализируюсь на:\n"
            "• Telegram-ботах для бизнеса\n"
            "• Веб-разработке\n"
            "• Автоматизации рутинных задач\n"
            "• PDF-инструментах\n\n"
            "📦 Использую: Python, Flask, HTML/CSS/JS, Google Apps Script\n"
            "⚡ Быстро, качественно, с поддержкой после сдачи\n\n"
            "📧 Telegram: @ваш_никнейм\n"
            "📧 Email: ваш@email.com",
            parse_mode="HTML",
            reply_markup=services_keyboard()
        )


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений."""
    text = update.message.text or ""

    # --- Главная клавиатура ---
    if text == "📋 Услуги":
        await update.message.reply_text(
            "<b>Выберите категорию услуг:</b>",
            parse_mode="HTML",
            reply_markup=services_keyboard()
        )

    elif text == "📅 Запись":
        await update.message.reply_text(
            "Какая вас интересует услуга?",
            reply_markup=booking_services_keyboard()
        )

    elif text == "📊 Статистика":
        visits = load_json(VISITS_FILE)
        bookings = load_json(BOOKINGS_FILE)
        unique_users = len(set(v["user_id"] for v in visits))
        await update.message.reply_text(
            "<b>📊 Статистика бота</b>\n\n"
            f"👥 Уникальных пользователей: <b>{unique_users}</b>\n"
            f"📨 Всего посещений: <b>{len(visits)}</b>\n"
            f"📅 Записей на консультацию: <b>{len(bookings)}</b>\n"
            f"📈 Конверсия: "
            f"<b>{len(bookings)/max(unique_users,1)*100:.1f}%</b>",
            parse_mode="HTML"
        )

    elif text == "📄 Отчёт (PDF)":
        await update.message.reply_text(
            "⏳ Генерирую PDF-отчёт по записям..."
        )
        pdf_path = generate_report()
        if pdf_path:
            await update.message.reply_document(
                document=open(pdf_path, "rb"),
                caption="📄 Готовый отчёт по записям"
            )
        else:
            await update.message.reply_text(
                "📭 Записей пока нет. Сначала запишитесь (/📅 Запись), "
                "затем запросите отчёт."
            )

    elif text == "📞 Контакты":
        await update.message.reply_text(
            "<b>📞 Связаться со мной:</b>\n\n"
            "📧 Telegram: @ваш_никнейм\n"
            "📧 Email: ваш@email.com\n"
            "💬 Готов обсудить ваш проект!\n\n"
            "⏱ Обычно отвечаю в течение часа.",
            parse_mode="HTML"
        )

    elif text == "ℹ️ О нас":
        await update.message.reply_text(
            "<b>ℹ️ Обо мне</b>\n\n"
            "👋 Разработчик с опытом в:\n"
            "• Telegram-ботах для бизнеса\n"
            "• Веб-разработке (Flask, HTML/CSS/JS)\n"
            "• Автоматизации бизнес-процессов\n"
            "• PDF-обработке и генерации отчётов\n\n"
            "📦 Технологии:\n"
            "Python, Flask, SQLite, Google Apps Script, "
            "ReportLab, pdfplumber, Telegram Bot API\n\n"
            "⚡ Работаю быстро, общаюсь ясно,\n"
            "   поддерживаю после сдачи.",
            parse_mode="HTML"
        )

    # --- Обработка записи (простой текстовый парсинг) ---
    elif context.user_data.get("booking_service") and "|" in text:
        parts = [p.strip() for p in text.split("|")]
        if len(parts) >= 3:
            booking = {
                "name": parts[0],
                "date": parts[1],
                "contact": parts[2],
                "service": context.user_data["booking_service"],
                "username": update.effective_user.username or "",
                "created_at": datetime.now().isoformat(),
            }
            bookings = load_json(BOOKINGS_FILE)
            bookings.append(booking)
            save_json(BOOKINGS_FILE, bookings)

            await update.message.reply_text(
                f"✅ <b>Запись принята!</b>\n\n"
                f"👤 Имя: {booking['name']}\n"
                f"📋 Услуга: {booking['service']}\n"
                f"📅 Дата: {booking['date']}\n"
                f"📞 Контакт: {booking['contact']}\n\n"
                "Я свяжусь с вами для подтверждения!",
                parse_mode="HTML"
            )
            context.user_data.clear()
        else:
            await update.message.reply_text(
                "❌ Неверный формат.\n"
                "Ожидается: <code>Имя | Дата | Контакт</code>",
                parse_mode="HTML"
            )

    else:
        # Неизвестная команда — подсказка
        await update.message.reply_text(
            "Выберите действие из меню ниже 👇",
            reply_markup=main_menu_keyboard()
        )


async def admin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Админ-панель — /admin."""
    user_id = update.effective_user.id
    ADMIN_IDS = os.getenv("ADMIN_IDS", "").split(",")
    # Если ADMIN_IDS не задан — доступ для всех (демо-режим)
    if ADMIN_IDS and ADMIN_IDS[0] and str(user_id) not in ADMIN_IDS:
        await update.message.reply_text("⛔ У вас нет доступа.")
        return

    visits = load_json(VISITS_FILE)
    bookings = load_json(BOOKINGS_FILE)
    unique_users = len(set(v["user_id"] for v in visits))

    report = (
        "<b>🔧 АДМИН-ПАНЕЛЬ</b>\n\n"
        f"👥 Уникальных пользователей: {unique_users}\n"
        f"📨 Всего посещений: {len(visits)}\n"
        f"📅 Записей: {len(bookings)}\n"
        f"📊 Конверсия: {len(bookings)/max(unique_users,1)*100:.1f}%\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
    )

    if bookings:
        report += "<b>Последние записи:</b>\n"
        for b in bookings[-5:]:
            report += (
                f"  • {b['name']} — {b['service']} ({b['date']})\n"
            )

    await update.message.reply_text(report, parse_mode="HTML")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок."""
    logger.error(f"Ошибка: {context.error}", exc_info=context.error)


# ==========================================
# ЗАПУСК
# ==========================================
def main():
    """Запуск бота."""
    logger.info("Демо-бот запускается...")
    app = Application.builder().token(BOT_TOKEN).build()

    # Обработчики
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_handler))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, message_handler
    ))

    # Глобальный обработчик ошибок
    app.add_error_handler(error_handler)

    logger.info("Бот запущен! Нажмите Ctrl+C для остановки.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
