# -*- coding: utf-8 -*-
# Презентация «PDF-бот Аганим v3.5» в стиле macOS (python-pptx)
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.oxml.ns import qn
from lxml import etree

# ---------- палитра (Apple) ----------
BG      = "F5F5F7"   # фон контентных слайдов
BG_DARK = "1D1D1F"   # титул/финал
CARD    = "FFFFFF"
CARD2   = "F2F2F7"   # светло-серая плашка
HAIR    = "E5E5EA"   # хайрлайн
TEXT    = "1D1D1F"
MUTED   = "86868B"
ACCENT  = "0A84FF"   # Apple blue
ACCENT_D= "0060DF"
GREEN   = "28C840"
GREEN_BG= "E4F8E8"
GREEN_TX= "1D8A34"
GRAY_TX = "6E6E73"
WHITE   = "FFFFFF"
RED     = "FF5F57"
YELLOW  = "FEBC2E"
FONT    = "Segoe UI"

EMU_IN = 914400
W, H = 13.333, 7.5

prs = Presentation()
prs.slide_width  = Emu(int(W * EMU_IN))
prs.slide_height = Emu(int(H * EMU_IN))
BLANK = prs.slide_layouts[6]

def C(h): return RGBColor.from_string(h)

def slide(bg=BG):
    s = prs.slides.add_slide(BLANK)
    r = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
    r.fill.solid(); r.fill.fore_color.rgb = C(bg); r.line.fill.background()
    r.shadow.inherit = False
    return s

def shadow(shape, blur=100000, dist=28000, alpha=12):
    spPr = shape._element.spPr
    for el in spPr.findall(qn('a:effectLst')): spPr.remove(el)
    xml = ('<a:effectLst xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
           f'<a:outerShdw blurRad="{blur}" dist="{dist}" dir="5400000" rotWithShape="0">'
           f'<a:srgbClr val="000000"><a:alpha val="{alpha*1000}"/></a:srgbClr>'
           '</a:outerShdw></a:effectLst>')
    spPr.append(etree.fromstring(xml))

def shape(s, kind, x, y, w, h, fill=None, line=None, lw=0.75, rad=None):
    sp = s.shapes.add_shape(kind, Inches(x), Inches(y), Inches(w), Inches(h))
    sp.shadow.inherit = False
    if fill is None: sp.fill.background()
    else: sp.fill.solid(); sp.fill.fore_color.rgb = C(fill)
    if line is None: sp.line.fill.background()
    else: sp.line.color.rgb = C(line); sp.line.width = Pt(lw)
    if rad is not None and kind == MSO_SHAPE.ROUNDED_RECTANGLE:
        try: sp.adjustments[0] = rad
        except Exception: pass
    return sp

def rrect(s, x, y, w, h, fill=CARD, line=HAIR, lw=0.75, rad=0.06):
    return shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h, fill, line, lw, rad)

def oval(s, x, y, d, fill):
    return shape(s, MSO_SHAPE.OVAL, x, y, d, d, fill)

def text(s, x, y, w, h, paras, size=14, color=TEXT, bold=False,
         align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, leading=None, space_after=None):
    tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    for m in ('margin_left','margin_right','margin_top','margin_bottom'):
        setattr(tf, m, 0)
    tf.vertical_anchor = anchor
    if isinstance(paras, str): paras = [paras]
    if paras and isinstance(paras[0], tuple): paras = [paras]  # один rich-абзац
    for i, para in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        if leading: p.line_spacing = leading
        if space_after is not None: p.space_after = Pt(space_after)
        runs = para if isinstance(para, list) else [(para, {})]
        for txt, st in runs:
            r = p.add_run(); r.text = txt
            f = r.font
            f.name = st.get('font', FONT)
            f.size = Pt(st.get('size', size))
            f.bold = st.get('bold', bold)
            f.italic = st.get('italic', False)
            f.color.rgb = C(st.get('color', color))
    return tb

def chip(s, x, y, w, h, label, fill=ACCENT, color=WHITE, size=11, bold=True, line=None):
    c = rrect(s, x, y, w, h, fill, line, 0.75, 0.5)
    text(s, x, y-0.012, w, h, label, size=size, color=color, bold=bold,
         align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    return c

def btn(s, x, y, w, h, label, fill=ACCENT, color=WHITE, size=12, bold=True, line=None):
    b = rrect(s, x, y, w, h, fill, line, 0.75, 0.5)
    shadow(b, 60000, 15000, 10)
    text(s, x, y-0.012, w, h, label, size=size, color=color, bold=bold,
         align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    return b

def traffic(s, x, y, d=0.10, gap=0.185):
    for i, col in enumerate((RED, YELLOW, GREEN)):
        oval(s, x + i*gap, y, d, col)

def window(s, x, y, w, h, title="", bar=True):
    card = rrect(s, x, y, w, h, CARD, HAIR, 1.0, 0.045)
    shadow(card)
    traffic(s, x + 0.22, y + 0.18)
    if bar:
        shape(s, MSO_SHAPE.RECTANGLE, x + 0.02, y + 0.42, w - 0.04, 0.011, HAIR, None)
    if title:
        text(s, x, y + 0.07, w, 0.3, title, size=12.5, color=MUTED, bold=True,
             align=PP_ALIGN.CENTER)
    return card

def title_block(s, kicker, title, sub=None):
    text(s, 0.9, 0.52, 11.5, 0.3, kicker.upper(), size=12.5, color=ACCENT, bold=True)
    text(s, 0.9, 0.86, 11.6, 0.75, title, size=33, color=TEXT, bold=True)
    if sub:
        text(s, 0.9, 1.52, 11.4, 0.35, sub, size=15, color=MUTED)

def arrow(s, x, y, label=""):
    text(s, x, y, 0.5, 0.5, "→", size=22, color=MUTED, bold=True,
         align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)

def grid(s, x, y, colws, rowh, rows, header=True, size=10.5, row_fills=None,
         cell_styles=None, header_fill=CARD2):
    """rows: list of list[str]; cell_styles: {(r,c): {'color':..,'bold':..,'fill':..}}"""
    cx = x
    for ri, row in enumerate(rows):
        ry = y + ri * rowh
        if ri == 0 and header:
            shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, x, y, sum(colws)-0.06, rowh,
                  header_fill, None, 0.75, 0.18)
        fill = None
        if row_fills and ri in row_fills: fill = row_fills[ri]
        cx = x + 0.04
        for ci, cell in enumerate(row):
            st = {}
            if cell_styles and (ri, ci) in cell_styles: st = cell_styles[(ri, ci)]
            f = st.get('fill', fill)
            if f:
                shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, cx-0.03, ry, colws[ci], rowh,
                      f, None, 0.75, 0.18)
            text(s, cx, ry - 0.02, colws[ci] - 0.06, rowh, str(cell),
                 size=st.get('size', size if ri else size + 0.5),
                 color=st.get('color', TEXT if ri == 0 and header else TEXT),
                 bold=st.get('bold', ri == 0 and header),
                 anchor=MSO_ANCHOR.MIDDLE)
            cx += colws[ci]

# ================= S1. ТИТУЛ (тёмный) =================
s = slide(BG_DARK)
text(s, 0, 1.05, W, 0.35, "СИСТЕМА УЧЁТА СЧЁТОВ ДЛЯ САЛОНОВ", size=13,
     color=MUTED, bold=True, align=PP_ALIGN.CENTER)
wx, wy, ww, wh = 3.87, 1.75, 5.6, 3.5
window(s, wx, wy, ww, wh, "")
# иконка приложения
ic = rrect(s, wx + ww/2 - 0.45, wy + 0.55, 0.9, 0.9, ACCENT, None, 0, 0.22)
shadow(ic, 120000, 20000, 30)
doc = rrect(s, wx + ww/2 - 0.17, wy + 0.72, 0.34, 0.56, WHITE, None, 0, 0.12)
for i in range(3):
    shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, wx + ww/2 - 0.11, wy + 0.84 + i*0.12,
          0.22, 0.035, ACCENT, None, 0, 0.5)
text(s, wx, wy + 1.62, ww, 0.5, "PDF-бот Аганим", size=30, color=TEXT, bold=True,
     align=PP_ALIGN.CENTER)
text(s, wx + 0.5, wy + 2.2, ww - 1.0, 0.75,
     "Счёт из PDF попадает в Google-таблицу,\nуведомления уходят в Telegram — без ручного ввода",
     size=14.5, color=GRAY_TX, align=PP_ALIGN.CENTER, leading=1.15)
chip(s, wx + ww/2 - 0.55, wy + 3.0, 1.1, 0.32, "версия 3.5", CARD2, GRAY_TX, 11)
text(s, 0, H - 0.62, W, 0.3, "Аганим · 2026", size=12, color=MUTED,
     align=PP_ALIGN.CENTER)

# ================= S2. ПРОБЛЕМА =================
s = slide()
title_block(s, "Знакомая ситуация", "Счёт съедает время всей команды",
            "Каждый PDF — это ручной перенос цифр в несколько мест")
text(s, 0.9, 2.05, 3.0, 0.3, "Как это выглядит", size=13, color=MUTED, bold=True)
stats = [
    ("~15 мин", "уходит на перенос одного счёта в таблицу (пример)"),
    ("3 места", "где живут одни и те же цифры: PDF, таблица, мессенджер"),
    ("0 напоминаний", "клиент узнаёт о приходе, только если менеджер вспомнил позвонить"),
]
sy = 2.45
for num, desc in stats:
    text(s, 0.9, sy, 3.0, 0.55, num, size=21, color=ACCENT, bold=True)
    text(s, 3.6, sy + 0.06, 3.1, 0.9, desc, size=13.5, color=GRAY_TX, leading=1.1)
    sy += 1.35
wx, wy, ww, wh = 7.2, 2.05, 5.2, 4.5
window(s, wx, wy, ww, wh, "Менеджер · типичный счёт")
todo = [
    ("Открыть PDF и найти номер, дату, клиента", False),
    ("Переписать позиции в Google-таблицу", False),
    ("Посчитать бонус дизайнеру", False),
    ("Написать дизайнеру о счёте", True),
    ("Позвонить клиенту, когда придёт товар", True),
]
ty = wy + 0.62
for label, missed in todo:
    bx = rrect(s, wx + 0.3, ty, 0.26, 0.26, GREEN_BG if not missed else "FFE9E9",
               None, 0, 0.3)
    text(s, wx + 0.33, ty - 0.02, 0.22, 0.3, "✓" if not missed else "×",
         size=13, color=GREEN_TX if not missed else RED, bold=True,
         align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    text(s, wx + 0.75, ty - 0.015, ww - 1.1, 0.32, label,
         size=13, color=TEXT if not missed else GRAY_TX,
         bold=False, anchor=MSO_ANCHOR.MIDDLE)
    ty += 0.62
chip(s, wx + 0.3, ty + 0.05, 3.3, 0.36, "Последние два шага часто забывают",
     "FFE9E9", RED, 11.5)

# ================= S3. КАК РАБОТАЕТ =================
s = slide()
title_block(s, "Архитектура", "Как это работает",
            "Менеджер сохраняет PDF — дальше всё происходит само")
steps = [
    ("PDF-счёт", "менеджер сохраняет файл в рабочую папку"),
    ("PDF-бот", "читает номер, дату, клиента, телефон и сумму"),
    ("Google-таблица", "строки счетов, бонусы, детализация"),
    ("Apps Script", "следит за приходом и событиями таблицы"),
    ("Telegram", "уведомления команде, дизайнерам и клиентам"),
]
cw, ch, gap = 2.14, 1.7, 0.44
total = len(steps)*cw + (len(steps)-1)*gap
x0 = (W - total) / 2
y0 = 2.6
for i, (t, d) in enumerate(steps):
    x = x0 + i*(cw+gap)
    card = rrect(s, x, y0, cw, ch)
    shadow(card)
    num = shape(s, MSO_SHAPE.OVAL, x + cw/2 - 0.26, y0 - 0.26, 0.52, 0.52, ACCENT)
    text(s, x + cw/2 - 0.26, y0 - 0.30, 0.52, 0.52, str(i+1), size=15, color=WHITE,
         bold=True, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    text(s, x + 0.1, y0 + 0.42, cw - 0.2, 0.4, t, size=14.5, color=TEXT, bold=True,
         align=PP_ALIGN.CENTER)
    text(s, x + 0.14, y0 + 0.82, cw - 0.28, 0.8, d, size=11, color=GRAY_TX,
         align=PP_ALIGN.CENTER, leading=1.1)
    if i < len(steps) - 1:
        arrow(s, x + cw + gap/2 - 0.25, y0 + ch/2 - 0.25)
text(s, 0.9, 5.1, 11.5, 0.4,
     "Что нужно: ПК менеджера с ботом · Google-таблица · Telegram-бот. Настройка — один раз.",
     size=13.5, color=MUTED, align=PP_ALIGN.CENTER)

# ================= S4. ШАГ 1 — PDF В ПАПКУ =================
s = slide()
title_block(s, "Шаг 1", "Просто сохранить PDF",
            "Бот следит за папкой и сам открывает окно ввода")
wx, wy, ww, wh = 0.9, 2.15, 6.6, 4.6
window(s, wx, wy, ww, wh, "Счета — Finder")
# сайдбар
shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, wx + 0.25, wy + 0.65, 1.5, 3.6, CARD2, None, 0, 0.1)
side = ["Рабочий стол", "Документы", "Счета", "Загрузки"]
for i, item in enumerate(side):
    active = item == "Счета"
    if active:
        shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, wx + 0.32, wy + 0.78 + i*0.44,
              1.36, 0.34, ACCENT, None, 0, 0.25)
    text(s, wx + 0.45, wy + 0.76 + i*0.44, 1.3, 0.34, item, size=11,
         color=WHITE if active else TEXT, bold=active, anchor=MSO_ANCHOR.MIDDLE)
files = [
    ("Счёт №1041 — Смирнова.pdf", "вчера, 17:40", False),
    ("Счёт №1042 — Иванова.pdf", "сейчас добавлен", True),
    ("Счёт №1043 — Кузнецов.pdf", "2 дня назад", False),
]
fx = wx + 2.0
fy = wy + 0.75
for name, when, sel in files:
    if sel:
        shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, fx - 0.08, fy - 0.05, ww - 2.3, 0.62,
              ACCENT, None, 0, 0.15)
    doc2 = rrect(s, fx, fy + 0.05, 0.28, 0.36, CARD if sel else "DEE8F5", None, 0, 0.06)
    text(s, fx + 0.45, fy - 0.02, 3.4, 0.32, name, size=12,
         color=WHITE if sel else TEXT, bold=sel)
    text(s, fx + 0.45, fy + 0.24, 3.4, 0.25, when, size=9.5,
         color="CDE4FF" if sel else MUTED)
    fy += 0.78
text(s, fx, fy + 0.12, 4.2, 0.3, "Бот заметил новый файл за секунду", size=10.5,
     color=ACCENT, bold=True)
# правая колонка
pts = [
    ("Значок в трее", "бот работает в фоне, ничего нажимать не нужно"),
    ("Читает PDF сам", "номер, дата, клиент, телефон, сумма позиций"),
    ("Окно — само", "как только файл появился, открывается ввод"),
]
py = 2.35
for t, d in pts:
    b = rrect(s, 8.1, py, 0.34, 0.34, GREEN_BG, None, 0, 0.3)
    text(s, 8.1, py - 0.02, 0.34, 0.36, "✓", size=14, color=GREEN_TX, bold=True,
         align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    text(s, 8.65, py - 0.04, 3.7, 0.35, t, size=15, color=TEXT, bold=True)
    text(s, 8.65, py + 0.32, 3.7, 0.6, d, size=12.5, color=GRAY_TX, leading=1.1)
    py += 1.28

# ================= S5. ШАГ 2 — ОКНО ВВОДА =================
s = slide()
title_block(s, "Шаг 2", "Проверить и дополнить",
            "Большинство полей уже заполнены из PDF")
wx, wy, ww, wh = 0.9, 2.1, 7.6, 4.7
window(s, wx, wy, ww, wh, "Счёт №1042 — Иванова · PDF-бот Аганим")
fields = [
    ("Клиент", "Иванова Анна", "из PDF"),
    ("Телефон", "+7 900 123-45-67", "найден в базе"),
    ("Позиций", "4", "из PDF"),
    ("Дизайнер", "Петрова", "подсказки при вводе"),
    ("Менеджер", "Сидоров", "обычно это вы"),
    ("Форма оплаты", "оплата при получении", ""),
]
for i, (lab, val, note) in enumerate(fields):
    col = i % 2; row = i // 2
    fx = wx + 0.35 + col * 3.6
    fy = wy + 0.62 + row * 0.98
    text(s, fx, fy, 3.3, 0.25, lab.upper(), size=9.5, color=MUTED, bold=True)
    f = rrect(s, fx, fy + 0.26, 3.3, 0.42, CARD2, HAIR, 0.75, 0.18)
    text(s, fx + 0.14, fy + 0.26, 3.0, 0.42, val, size=12.5, color=TEXT,
         anchor=MSO_ANCHOR.MIDDLE, bold=True)
    if note:
        text(s, fx + 0.1, fy + 0.7, 3.2, 0.22, note, size=9.5, color=ACCENT)
# дата уведомления + чекбокс
cx0 = wx + 0.35
cy0 = wy + 3.62
bx = rrect(s, cx0, cy0, 0.26, 0.26, ACCENT, None, 0, 0.25)
text(s, cx0 - 0.015, cy0 - 0.05, 0.3, 0.34, "✓", size=13, color=WHITE, bold=True,
     align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
text(s, cx0 + 0.4, cy0 - 0.03, 4.0, 0.32, "Клиент уже извещён об оплате — сегодня",
     size=12.5, color=TEXT, anchor=MSO_ANCHOR.MIDDLE)
btn(s, wx + ww - 2.15, cy0 - 0.04, 1.0, 0.38, "Отмена", CARD2, GRAY_TX, 12, False, HAIR)
btn(s, wx + ww - 1.05, cy0 - 0.04, 0.85, 0.38, "Далее")
# правая колонка
text(s, 9.0, 2.3, 3.4, 0.3, "Что уже заполнено", size=13, color=MUTED, bold=True)
fills = [("6 полей из 7", "заполнены сами — седьмое лишь галочка извещения"),
         ("Телефон", "подтягивается из истории счетов клиента"),
         ("Esc или крестик", "счёт не запишется, PDF останется на месте")]
fy2 = 2.75
for t, d in fills:
    rrect(s, 9.0, fy2, 3.35, 0.95, CARD, HAIR, 0.75, 0.12)
    text(s, 9.18, fy2 + 0.12, 3.05, 0.3, t, size=13, color=ACCENT, bold=True)
    text(s, 9.18, fy2 + 0.44, 3.05, 0.45, d, size=10.5, color=GRAY_TX, leading=1.05)
    fy2 += 1.15

# ================= S6. ШАГ 3 — ПОСТАВЩИКИ =================
s = slide()
title_block(s, "Шаг 3", "Разделить по поставщикам",
            "Одна строка на группу позиций — в любом формате")
wx, wy, ww, wh = 0.9, 2.15, 6.9, 4.55
window(s, wx, wy, ww, wh, "Позиции счёта №1042")
pos = ["Позиция 1 — стеллаж", "Позиция 2 — стеллаж", "Позиция 3 — кресло", "Позиция 4 — кресло"]
for i, p in enumerate(pos):
    text(s, wx + 0.35, wy + 0.6 + i*0.42, 0.4, 0.3, str(i+1), size=12, color=MUTED,
         bold=True, anchor=MSO_ANCHOR.MIDDLE)
    text(s, wx + 0.75, wy + 0.6 + i*0.42, 4.4, 0.3, p, size=12, color=TEXT,
         anchor=MSO_ANCHOR.MIDDLE)
text(s, wx + 0.35, wy + 2.45, 3.0, 0.25, "РАСПРЕДЕЛЕНИЕ", size=9.5, color=MUTED, bold=True)
f1 = rrect(s, wx + 0.35, wy + 2.72, 3.1, 0.44, CARD, ACCENT, 1.1, 0.18)
text(s, wx + 0.5, wy + 2.72, 2.9, 0.44, "1,2 - ВИА", size=13, color=TEXT,
     anchor=MSO_ANCHOR.MIDDLE, bold=True)
f2 = rrect(s, wx + 3.6, wy + 2.72, 3.0, 0.44, CARD, HAIR, 1.0, 0.18)
text(s, wx + 3.75, wy + 2.72, 2.8, 0.44, "3,4 - Бонтон", size=13, color=TEXT,
     anchor=MSO_ANCHOR.MIDDLE, bold=True)
text(s, wx + 0.35, wy + 3.35, 6.2, 0.6,
     "Писать можно как угодно: «1,2-ВИА», «1.2 - виа», «1, 2 - ВИА» — бот поймёт.\nEnter — и позиции ушли своим поставщикам.",
     size=11.5, color=GRAY_TX, leading=1.15)
text(s, wx + 0.35, wy + 4.02, 6.2, 0.3, "", size=11)
# правая колонка — результат
text(s, 8.35, 2.3, 4.1, 0.3, "Что попадёт в таблицу", size=13, color=MUTED, bold=True)
rows = [
    ("№1042", "ВИА", "поз. 1–2 · стеллаж"),
    ("№1042", "Бонтон", "поз. 3–4 · кресло"),
]
ry = 2.75
for num, sup, desc in rows:
    rrect(s, 8.35, ry, 4.05, 1.05, CARD, HAIR, 0.75, 0.12)
    chip(s, 8.55, ry + 0.18, 0.75, 0.3, num, CARD2, GRAY_TX, 10)
    chip(s, 9.4, ry + 0.18, 1.1, 0.3, sup,
         "E8F1FF" if sup == "ВИА" else CARD2, ACCENT_D if sup == "ВИА" else GRAY_TX, 10.5)
    text(s, 8.55, ry + 0.58, 3.7, 0.3, desc, size=11.5, color=GRAY_TX)
    ry += 1.25
text(s, 8.35, ry + 0.05, 4.05, 0.9,
     "Дальше — автоматически: строки в «Лист1», бонусы в «Детализацию», сообщение дизайнеру.",
     size=11.5, color=MUTED, leading=1.15)

# ================= S7. ТАБЛИЦА =================
s = slide()
title_block(s, "Результат", "Счёт в таблице, бонус посчитан",
            "Те же данные — сразу в учётной системе")
wx, wy, ww, wh = 0.9, 2.15, 8.3, 4.55
window(s, wx, wy, ww, wh, "Google-таблица · Лист1")
colws = [0.75, 0.9, 1.5, 1.25, 0.65, 1.3, 1.4]
hdr = ["№", "Дата", "Клиент", "Дизайнер", "Поз.", "Поставщик", "Менеджер"]
rows = [
    hdr,
    ["1042", "10.09", "Иванова А.", "Петрова", "2", "ВИА", "Сидоров"],
    ["1042", "10.09", "Иванова А.", "Петрова", "2", "Бонтон", "Сидоров"],
    ["1041", "09.09", "Смирнова О.", "Смирнова", "5", "ВИА", "Сидоров"],
    ["1039", "07.09", "Кузнецов Д.", "Петрова", "2", "Бонтон", "Сидоров"],
]
grid(s, wx + 0.3, wy + 0.6, colws, 0.42, rows, header=True, size=10.5,
     row_fills={1: GREEN_BG, 2: GREEN_BG},
     cell_styles={(1, 5): {'color': GREEN_TX, 'bold': True},
                  (2, 5): {'color': GREEN_TX, 'bold': True}})
chip(s, wx + 4.85, wy + 3.05, 1.65, 0.32, "все позиции пришли", GREEN_BG, GREEN_TX, 9.5)
chip(s, wx + 6.6, wy + 3.05, 1.35, 0.32, "УВЕДОМЛЕНО", GREEN_BG, GREEN_TX, 9.5)
text(s, wx + 0.3, wy + 3.5, 7.6, 0.5,
     "Зелёная строка — по всем позициям заполнен приход. Как только заполнены все — в Telegram уходит уведомление.",
     size=11.5, color=GRAY_TX, leading=1.15)
# правая колонка — бонус
rrect(s, 9.5, 2.35, 2.9, 2.3, CARD, HAIR, 0.75, 0.1)
text(s, 9.7, 2.55, 2.6, 0.3, "Детализация · бонус", size=12, color=MUTED, bold=True)
text(s, 9.7, 2.92, 2.6, 0.35, "Петрова · 4 позиции", size=13, color=TEXT, bold=True)
text(s, 9.7, 3.3, 2.65, 0.95,
     [[("Сумма: 48 000 ₽", {'size': 12, 'color': GRAY_TX})],
      [("Ставка: 5%", {'size': 12, 'color': GRAY_TX})],
      [("Бонус: ", {'size': 12, 'color': GRAY_TX}),
       ("2 400 ₽", {'size': 15, 'color': ACCENT, 'bold': True})]], leading=1.25)
text(s, 9.5, 4.95, 2.95, 1.0, "Оборот дизайнера от 500 000 ₽ за месяц — ставка 10%.",
     size=11.5, color=MUTED, leading=1.15)
text(s, 0.9, 6.95, 8, 0.3, "Цифры в примере — иллюстративные", size=10, color=MUTED)

# ================= S8. ДАШБОРД — СЧЕТА =================
s = slide()
title_block(s, "Дашборд", "Все счета под рукой",
            "Отдельное окно с таблицей, статусами и действиями")
wx, wy, ww, wh = 0.9, 2.15, 11.5, 4.6
window(s, wx, wy, ww, wh, "")
tabs = [("Счета", True), ("Дизайнеры", False), ("Календарь", False)]
tx = wx + 0.35
for t, act in tabs:
    w_t = 1.15
    if act:
        shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, tx, wy + 0.55, w_t, 0.34, CARD2, None, 0, 0.25)
    text(s, tx, wy + 0.53, w_t, 0.36, t, size=12, color=TEXT if act else MUTED,
         bold=act, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    tx += w_t + 0.15
chip(s, wx + 4.3, wy + 0.56, 0.95, 0.32, "Все", "E8F1FF", ACCENT_D, 10)
chip(s, wx + 5.35, wy + 0.56, 1.55, 0.32, "Ожидаются", CARD2, TEXT, 10, False)
chip(s, wx + 7.0, wy + 0.56, 1.1, 0.32, "Пришло", GREEN_BG, GREEN_TX, 10)
btn(s, wx + ww - 2.5, wy + 0.52, 2.15, 0.4, "Отгружено сегодня", size=11)
colws = [0.9, 1.9, 1.5, 0.75, 1.7, 1.8, 1.3]
hdr = ["№", "Клиент", "Дизайнер", "Поз.", "Поставщик", "Приход", "Действие"]
rows = [hdr,
        ["1042", "Иванова А.", "Петрова", "4", "ВИА + Бонтон", "все · 10.09", "Изменить"],
        ["1041", "Смирнова О.", "Смирнова", "5", "ВИА", "ждём · 2 из 5", "Изменить"],
        ["1039", "Кузнецов Д.", "Петрова", "2", "Бонтон", "все · 07.09", "Изменить"]]
grid(s, wx + 0.35, wy + 1.05, colws, 0.46, rows, header=True, size=10.5,
     row_fills={1: GREEN_BG, 3: CARD2},
     cell_styles={(1, 5): {'color': GREEN_TX, 'bold': True},
                  (2, 5): {'color': ACCENT_D, 'bold': True},
                  (3, 5): {'color': GREEN_TX, 'bold': True}})
# легенда
ly = wy + 3.55
oval(s, wx + 0.4, ly + 0.05, 0.14, GREEN)
text(s, wx + 0.62, ly - 0.04, 2.6, 0.3, "все позиции пришли", size=11, color=GRAY_TX,
     anchor=MSO_ANCHOR.MIDDLE)
oval(s, wx + 3.2, ly + 0.05, 0.14, MUTED)
text(s, wx + 3.42, ly - 0.04, 2.2, 0.3, "отгружено клиенту", size=11, color=GRAY_TX,
     anchor=MSO_ANCHOR.MIDDLE)
oval(s, wx + 5.8, ly + 0.05, 0.14, ACCENT)
text(s, wx + 6.02, ly - 0.04, 2.0, 0.3, "ждём приход — у кого спросить", size=11, color=GRAY_TX, anchor=MSO_ANCHOR.MIDDLE)
text(s, wx + 8.15, ly - 0.04, 3.0, 0.3,
     "Кнопка «Изменить» — поправить даты прихода",
     size=10.5, color=MUTED, anchor=MSO_ANCHOR.MIDDLE)

# ================= S9. ДАШБОРД — ДИЗАЙНЕРЫ =================
s = slide()
title_block(s, "Дашборд · вкладка «Дизайнеры»", "Бонусы без Excel",
            "Ставка считается сама, выплата отмечается кнопкой")
wx, wy, ww, wh = 0.9, 2.15, 11.5, 4.6
window(s, wx, wy, ww, wh, "")
tabs = [("Счета", False), ("Дизайнеры", True), ("Календарь", False)]
tx = wx + 0.35
for t, act in tabs:
    w_t = 1.15
    if act:
        shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, tx, wy + 0.55, w_t, 0.34, CARD2, None, 0, 0.25)
    text(s, tx, wy + 0.53, w_t, 0.36, t, size=12, color=TEXT if act else MUTED,
         bold=act, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    tx += w_t + 0.15
designers = [
    ("Петрова", "26 счетов · 512 000 ₽", "10%", "51 200 ₽"),
    ("Смирнова", "12 счетов · 248 000 ₽", "5%", "12 400 ₽"),
    ("Кузнецова", "7 счетов · 62 000 ₽", "5%", "3 100 ₽"),
]
dy = wy + 1.1
for name, vol, rate, bonus in designers:
    rrect(s, wx + 0.35, dy, 5.0, 0.92, CARD, HAIR, 0.75, 0.1)
    text(s, wx + 0.55, dy + 0.12, 2.4, 0.3, name, size=13.5, color=TEXT, bold=True)
    text(s, wx + 0.55, dy + 0.47, 2.8, 0.3, vol, size=11, color=GRAY_TX)
    chip(s, wx + 3.5, dy + 0.3, 0.6, 0.32, rate, "E8F1FF", ACCENT_D, 10.5)
    text(s, wx + 4.2, dy + 0.24, 1.1, 0.42, bonus, size=14, color=ACCENT, bold=True,
         anchor=MSO_ANCHOR.MIDDLE)
    dy += 1.06
# правая карточка — детали
rrect(s, wx + 5.7, wy + 1.1, 5.45, 3.35, CARD, HAIR, 0.75, 0.08)
text(s, wx + 5.95, wy + 1.32, 4.9, 0.35, "Петрова — сентябрь", size=15, color=TEXT, bold=True)
rows2 = [
    ("Оборот за месяц", "512 000 ₽"),
    ("Ставка", "10% — оборот выше 500 000 ₽"),
    ("Бонус к выплате", "51 200 ₽"),
    ("Ожидаемая дата", "5 октября"),
]
ry2 = wy + 1.8
for lab, val in rows2:
    text(s, wx + 5.95, ry2, 2.3, 0.3, lab, size=12, color=GRAY_TX)
    bold = lab == "Бонус к выплате"
    text(s, wx + 8.3, ry2 - 0.03, 2.7, 0.32, val, size=13 if bold else 12,
         color=ACCENT if bold else TEXT, bold=bold)
    ry2 += 0.44
btn(s, wx + 5.95, wy + 3.62, 1.75, 0.4, "Выплачено ✓", GREEN, WHITE, 11)
btn(s, wx + 7.85, wy + 3.62, 3.1, 0.4, "Отправить дизайнеру", size=11)
text(s, wx + 5.95, wy + 4.1, 5.0, 0.3, "готовое сообщение — копируется одной кнопкой",
     size=10.5, color=MUTED)

# ================= S10. КАЛЕНДАРЬ =================
s = slide()
title_block(s, "Дашборд · вкладка «Календарь»", "Календарь и напоминания",
            "Звонки, заметки и сроки бонусов — в одном месте")
wx, wy, ww, wh = 0.9, 2.15, 6.4, 4.6
window(s, wx, wy, ww, wh, "Сентябрь 2026")
days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
grid_x, grid_y, cell = wx + 0.4, wy + 0.65, 0.78
for ci, d in enumerate(days):
    text(s, grid_x + ci*cell, grid_y, cell, 0.3, d, size=10.5, color=MUTED, bold=True,
         align=PP_ALIGN.CENTER)
import calendar as _cal
first, n = _cal.monthrange(2026, 9)  # ср=2 (Пн=0)
first = (first) % 7  # Пн=0
for day in range(1, n + 1):
    r = (day + first - 1) // 7
    c = (day + first - 1) % 7
    dx = grid_x + c*cell
    dy2 = grid_y + 0.38 + r*0.62
    today = day == 10
    if today:
        shape(s, MSO_SHAPE.OVAL, dx + cell/2 - 0.19, dy2 + 0.02, 0.38, 0.38, ACCENT)
    text(s, dx, dy2 + 0.04, cell, 0.34, str(day), size=11,
         color=WHITE if today else TEXT, bold=today, align=PP_ALIGN.CENTER,
         anchor=MSO_ANCHOR.MIDDLE)
    if day in (11, 15, 18):
        oval(s, dx + cell/2 - 0.03, dy2 + 0.42, 0.06, ACCENT)
# правая колонка — события
text(s, 7.85, 2.3, 4.6, 0.3, "События на этой неделе", size=13, color=MUTED, bold=True)
events = [
    ("11 сен, пт", "Срок бонуса — Петрова", "появляется сам при расчёте", ACCENT),
    ("15 сен, вт", "15:00 — позвонить Ивановой", "заметка по счёту №1042", MUTED),
    ("18 сен, пт", "Оплата поставщику — Бонтон", "заметка менеджера", MUTED),
]
ey = 2.75
for date, title_, note, col in events:
    rrect(s, 7.85, ey, 4.55, 1.0, CARD, HAIR, 0.75, 0.1)
    shape(s, MSO_SHAPE.OVAL, 8.05, ey + 0.2, 0.14, 0.14, col)
    text(s, 8.32, ey + 0.12, 3.9, 0.3, title_, size=13, color=TEXT, bold=True)
    text(s, 8.05, ey + 0.52, 4.2, 0.3, date + " · " + note, size=10.5, color=GRAY_TX)
    ey += 1.18
text(s, 7.85, ey + 0.02, 4.55, 0.6,
     "Клик по дню — добавить событие. Напоминания всплывают при открытии дашборда.",
     size=11, color=MUTED, leading=1.15)

# ================= S11. TELEGRAM =================
s = slide()
title_block(s, "Уведомления", "Telegram: все в курсе",
            "Клиенту — кнопки, команде — события, вам — заявки")
# iPhone
px, py, pw, ph = 1.15, 2.05, 3.3, 5.1
frame = rrect(s, px, py, pw, ph, "3A3A3C", None, 0, 0.14)
shadow(frame, 130000, 30000, 22)
scr = rrect(s, px + 0.12, py + 0.12, pw - 0.24, ph - 0.24, "F2F2F7", None, 0, 0.1)
shape(s, MSO_SHAPE.ROUNDED_RECTANGLE, px + pw/2 - 0.4, py + 0.16, 0.8, 0.16, "3A3A3C", None, 0, 0.5)
text(s, px + 0.25, py + 0.42, pw - 0.5, 0.3, "Бот Аганим", size=11.5, color=TEXT,
     bold=True, align=PP_ALIGN.CENTER)
b1 = rrect(s, px + 0.25, py + 0.85, pw - 0.85, 0.72, "E8F1FF", None, 0, 0.16)
text(s, px + 0.4, py + 0.93, pw - 1.15, 0.6, "Счёт №1042:\nвсе позиции пришли",
     size=11, color=TEXT, leading=1.1)
btn(s, px + 0.25, py + 1.68, pw - 0.5, 0.36, "Заказать доставку", CARD, ACCENT_D, 10.5, True, "CBDBFF")
btn(s, px + 0.25, py + 2.12, pw - 0.5, 0.36, "Заберу сам", CARD, ACCENT_D, 10.5, True, "CBDBFF")
btn(s, px + 0.25, py + 2.56, pw - 0.5, 0.36, "Свяжитесь со мной", CARD, ACCENT_D, 10.5, True, "CBDBFF")
b2 = rrect(s, px + 0.7, py + 3.1, pw - 0.95, 0.42, ACCENT, None, 0, 0.16)
text(s, px + 0.85, py + 3.1, pw - 1.25, 0.42, "Заберу сам", size=10.5, color=WHITE,
     anchor=MSO_ANCHOR.MIDDLE, bold=True)
b3 = rrect(s, px + 0.25, py + 3.68, pw - 0.85, 0.66, "34C759", None, 0, 0.16)
text(s, px + 0.4, py + 3.76, pw - 1.15, 0.55, "Менеджеру: КЛИЕНТ\nЗАБЕРЁТ САМ · №1042",
     size=10, color=WHITE, leading=1.1, bold=True)
# правая колонка
who = [
    ("Менеджеру счёта", "приход товара и события по его счетам — лично"),
    ("Дизайнеру", "новый счёт и начисленный бонус"),
    ("Главный рабочий чат", "заявки на доставку, «заберу сам», тревоги"),
    ("Привязка людей", "человек пишет /start — chat_id попадает в лист «Telegram ID»"),
]
wy3 = 2.3
for t, d in who:
    text(s, 5.15, wy3, 3.6, 0.3, t, size=14.5, color=TEXT, bold=True)
    text(s, 5.15, wy3 + 0.36, 3.7, 0.62, d, size=12, color=GRAY_TX, leading=1.1)
    wy3 += 1.06
rrect(s, 9.05, 2.35, 3.4, 3.4, CARD, HAIR, 0.75, 0.1)
text(s, 9.3, 2.6, 2.9, 0.3, "Почему через таблицу", size=12.5, color=MUTED, bold=True)
for i, ln in enumerate(["api.telegram.org может быть закрыт на рабочих ПК",
                        "Apps Script шлёт сообщения из облака Google",
                        "история уведомлений связана с данными таблицы"]):
    oval(s, 9.3, 3.08 + i*0.75, 0.1, ACCENT)
    text(s, 9.52, 2.98 + i*0.75, 2.75, 0.65, ln, size=11, color=GRAY_TX, leading=1.1)

# ================= S12. ЗАЩИТА И БЭКАПЫ =================
s = slide()
title_block(s, "Надёжность", "Данные под защитой",
            "Бэкапы и контроль встроены в таблицу — включаются один раз")
cards = [
    ("23:23", "ежедневно", "полный бэкап таблицы на Google Drive, папка «Аганим — Бэкапы»"),
    ("30 дней", "хранение", "автоматическое удаление старых копий, восстановление из бэкапа"),
    ("1 час", "снапшот", "почасовой слайд данных — быстрый откат функцией restoreFromSnapshot"),
]
cw2 = 3.75
x0 = 0.9
for i, (num, lab, desc) in enumerate(cards):
    x = x0 + i*(cw2 + 0.2)
    card = rrect(s, x, 2.3, cw2, 2.5)
    shadow(card)
    text(s, x + 0.3, 2.6, cw2 - 0.6, 0.75, num, size=40, color=ACCENT, bold=True)
    text(s, x + 0.3, 3.38, cw2 - 0.6, 0.3, lab.upper(), size=11, color=MUTED, bold=True)
    text(s, x + 0.3, 3.75, cw2 - 0.6, 0.9, desc, size=12, color=GRAY_TX, leading=1.15)
wide = rrect(s, 0.9, 5.15, 11.55, 1.5, CARD, HAIR, 0.75, 0.08)
shadow(wide)
chip(s, 1.25, 5.55, 1.5, 0.4, "Тревога", "FFE9E9", RED, 12)
text(s, 3.0, 5.42, 9.2, 1.0,
     [("Удаление строк или столбцов блокируется предупреждением. ", {}),
      ("Если всё же удалили — мгновенная аварийная копия и алерт", {}),
      (" с email нарушителя", {'bold': True, 'color': TEXT}),
      (" в главный Telegram.", {})],
     size=13, color=GRAY_TX, leading=1.2, anchor=MSO_ANCHOR.MIDDLE)
text(s, 0.9, 6.95, 8, 0.3, "Включается запуском функции setupBackupSystem в Apps Script — один раз на таблицу",
     size=10, color=MUTED)

# ================= S13. ЗАПУСК =================
s = slide()
title_block(s, "Развёртывание", "Запуск на новом объекте — за один день",
            "Четыре шага, каждый занимает минуты")
steps4 = [
    ("Таблица", "копия эталонной Google-таблицы на аккаунте объекта"),
    ("Доступ", "key.json сервисного аккаунта — редактор таблицы"),
    ("Установка", "setup.exe: бот, дашборд, ярлыки, автозапуск"),
    ("Telegram", "Apps Script, токен бота, webhook, setupBackupSystem"),
]
cw3 = 2.85
x0 = 0.9
for i, (t, d) in enumerate(steps4):
    x = x0 + i*(cw3 + 0.25)
    card = rrect(s, x, 2.35, cw3, 2.15)
    shadow(card)
    num = shape(s, MSO_SHAPE.OVAL, x + 0.3, 2.62, 0.5, 0.5, ACCENT)
    text(s, x + 0.3, 2.58, 0.5, 0.5, str(i+1), size=15, color=WHITE, bold=True,
         align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    text(s, x + 0.95, 2.66, cw3 - 1.1, 0.4, t, size=15.5, color=TEXT, bold=True)
    text(s, x + 0.3, 3.35, cw3 - 0.6, 0.95, d, size=11.5, color=GRAY_TX, leading=1.15)
    if i < 3:
        arrow(s, x + cw3 + 0.25/2 - 0.25, 3.25)
note = rrect(s, 0.9, 4.95, 11.55, 1.55, CARD, HAIR, 0.75, 0.08)
shadow(note)
text(s, 1.25, 5.15, 5.5, 0.3, "Каждой компании — своё", size=13.5, color=TEXT, bold=True)
text(s, 1.25, 5.52, 5.6, 0.85,
     "В релизной сборке нет ни таблицы, ни ключей владельца: при первом запуске мастер просит ссылку на таблицу объекта.",
     size=11.5, color=GRAY_TX, leading=1.15)
text(s, 7.2, 5.15, 5.0, 0.3, "Обновления", size=13.5, color=TEXT, bold=True)
text(s, 7.2, 5.52, 5.0, 0.85,
     "update.exe находит установленную копию сам: остановил, заменил файлы, запустил обратно.",
     size=11.5, color=GRAY_TX, leading=1.15)

# ================= S14. ФИНАЛ (тёмный) =================
s = slide(BG_DARK)
text(s, 0, 2.0, W, 0.4, "PDF-БОТ АГАНИМ", size=13, color=MUTED, bold=True,
     align=PP_ALIGN.CENTER)
text(s, 0, 2.45, W, 1.1, "Порядок в счетах.\nБез рутины.", size=44, color=WHITE,
     bold=True, align=PP_ALIGN.CENTER, leading=1.05)
stats3 = [("30 сек", "на счёт вместо ~15 минут"),
          ("0", "руточного переноса цифр"),
          ("1 день", "на запуск на новом объекте")]
x0 = 2.3
for i, (num, lab) in enumerate(stats3):
    x = x0 + i*3.1
    text(s, x, 4.45, 2.9, 0.6, num, size=34, color=ACCENT, bold=True,
         align=PP_ALIGN.CENTER)
    text(s, x, 5.1, 2.9, 0.55, lab, size=12.5, color=MUTED, align=PP_ALIGN.CENTER,
         leading=1.1)
chip(s, W/2 - 1.35, 6.0, 2.7, 0.44, "Живое демо — по запросу", ACCENT, WHITE, 13)
text(s, 0, H - 0.55, W, 0.3, "Аганим · 2026 · v3.5", size=11, color=MUTED,
     align=PP_ALIGN.CENTER)

prs.save("PDF-бот Аганим — презентация.pptx")
print("SAVED:", len(prs.slides.__iter__.__self__._sldIdLst), "slides")
