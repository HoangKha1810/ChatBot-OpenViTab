from __future__ import annotations

from pathlib import Path
from typing import Iterable

from reportlab.lib import colors
from reportlab.lib.pagesizes import A0, landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "docs"
OUT_FILE = OUT_DIR / "SQL-Grounded_Vietnamese_TableQA_TemplateStyle_Poster.pdf"
DOWNLOADS_FILE = Path.home() / "Downloads" / "SQL-Grounded_Vietnamese_TableQA_TemplateStyle_Poster.pdf"

PAGE_W, PAGE_H = landscape(A0)

NAVY = colors.HexColor("#20234A")
HEADER_BLUE = colors.HexColor("#64A4D6")
PANEL_BLUE = colors.HexColor("#66A6D6")
PANEL_LIGHT = colors.HexColor("#A7C9F0")
PANEL_PALE = colors.HexColor("#DCEBFB")
INK = colors.HexColor("#050814")
WHITE = colors.white
GRID = colors.HexColor("#4B79A5")
TEAL = colors.HexColor("#087F7A")
GREEN = colors.HexColor("#159447")
RED = colors.HexColor("#D84436")
ORANGE = colors.HexColor("#D97706")
BLUE = colors.HexColor("#2457D6")
PURPLE = colors.HexColor("#6833C7")
GREY = colors.HexColor("#4B5563")


def register_fonts() -> tuple[str, str, str]:
    regular_candidates = [
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial Unicode.ttf",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    ]
    bold_candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial Unicode.ttf",
    ]
    black_candidates = [
        "/System/Library/Fonts/Supplemental/Arial Black.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    ]

    def first_existing(paths: Iterable[str]) -> str | None:
        for item in paths:
            if Path(item).exists():
                return item
        return None

    regular = first_existing(regular_candidates)
    bold = first_existing(bold_candidates)
    black = first_existing(black_candidates)
    if not regular:
        return "Helvetica", "Helvetica-Bold", "Helvetica-Bold"
    pdfmetrics.registerFont(TTFont("PosterRegular", regular))
    pdfmetrics.registerFont(TTFont("PosterBold", bold or regular))
    pdfmetrics.registerFont(TTFont("PosterBlack", black or bold or regular))
    return "PosterRegular", "PosterBold", "PosterBlack"


FONT, BOLD, BLACK = register_fonts()


def tw(text: str, font: str, size: float) -> float:
    return pdfmetrics.stringWidth(text, font, size)


def wrap_text(text: str, font: str, size: float, width: float) -> list[str]:
    lines: list[str] = []
    for raw in text.split("\n"):
        words = raw.strip().split()
        if not words:
            lines.append("")
            continue
        line = words[0]
        for word in words[1:]:
            candidate = f"{line} {word}"
            if tw(candidate, font, size) <= width:
                line = candidate
            else:
                lines.append(line)
                line = word
        lines.append(line)
    return lines


def draw_wrapped(
    c: canvas.Canvas,
    text: str,
    x: float,
    y_top: float,
    width: float,
    font: str = FONT,
    size: float = 22,
    leading: float = 27,
    bullet: bool = False,
    color: colors.Color = INK,
) -> float:
    y = y_top
    c.setFillColor(color)
    c.setFont(font, size)
    paragraphs = text.split("\n\n")
    for p_idx, para in enumerate(paragraphs):
        if p_idx:
            y -= leading * 0.48
        if bullet:
            for item in [p.strip() for p in para.split("\n") if p.strip()]:
                lines = wrap_text(item, font, size, width - 28)
                c.drawString(x, y, u"\u2022")
                c.drawString(x + 28, y, lines[0])
                y -= leading
                for line in lines[1:]:
                    c.drawString(x + 28, y, line)
                    y -= leading
        else:
            for line in wrap_text(para.strip(), font, size, width):
                if line:
                    c.drawString(x, y, line)
                y -= leading
    return y


def panel(c: canvas.Canvas, x: float, y: float, w: float, h: float, title: str) -> tuple[float, float, float, float]:
    c.setFillColor(PANEL_BLUE)
    c.setStrokeColor(NAVY)
    c.setLineWidth(6)
    c.roundRect(x, y, w, h, 28, fill=1, stroke=1)
    c.setFillColor(INK)
    c.setFont(BLACK, 34)
    c.drawString(x + 30, y + h - 46, title)
    c.setLineWidth(2.2)
    c.line(x + 30, y + h - 57, x + 30 + tw(title, BLACK, 34), y + h - 57)
    return x + 34, y + 34, w - 68, h - 92


def caption(c: canvas.Canvas, text: str, x: float, y: float, w: float) -> None:
    c.setFillColor(INK)
    c.setFont(BOLD, 17)
    for i, line in enumerate(wrap_text(text, BOLD, 17, w - 18)):
        c.drawCentredString(x + w / 2, y - i * 22, line)


def figure_label(c: canvas.Canvas, text: str, x: float, y: float, w: float) -> None:
    c.setFillColor(PANEL_PALE)
    c.setStrokeColor(GRID)
    c.setLineWidth(1.2)
    c.roundRect(x, y, w, 24, 6, fill=1, stroke=1)
    c.setFillColor(INK)
    c.setFont(BOLD, 13.5)
    c.drawCentredString(x + w / 2, y + 7, text)


def icon_database(c: canvas.Canvas, x: float, y: float, s: float) -> None:
    c.setStrokeColor(INK)
    c.setLineWidth(4)
    c.ellipse(x, y + s * 0.68, x + s, y + s, stroke=1, fill=0)
    c.line(x, y + s * 0.84, x, y + s * 0.18)
    c.line(x + s, y + s * 0.84, x + s, y + s * 0.18)
    c.ellipse(x, y, x + s, y + s * 0.34, stroke=1, fill=0)
    c.line(x, y + s * 0.52, x + s, y + s * 0.52)


def icon_table(c: canvas.Canvas, x: float, y: float, s: float) -> None:
    c.setStrokeColor(INK)
    c.setLineWidth(4)
    c.rect(x, y, s, s, fill=0, stroke=1)
    c.line(x, y + s * 0.65, x + s, y + s * 0.65)
    c.line(x, y + s * 0.33, x + s, y + s * 0.33)
    c.line(x + s * 0.35, y, x + s * 0.35, y + s)
    c.line(x + s * 0.68, y, x + s * 0.68, y + s)


def icon_question(c: canvas.Canvas, x: float, y: float, s: float) -> None:
    c.setFillColor(INK)
    c.setFont(BLACK, s)
    c.drawCentredString(x + s * 0.4, y, "?")


def icon_shield(c: canvas.Canvas, x: float, y: float, s: float) -> None:
    c.setStrokeColor(INK)
    c.setLineWidth(4)
    path = c.beginPath()
    path.moveTo(x + s * 0.5, y + s)
    path.lineTo(x + s * 0.92, y + s * 0.82)
    path.lineTo(x + s * 0.82, y + s * 0.28)
    path.lineTo(x + s * 0.5, y)
    path.lineTo(x + s * 0.18, y + s * 0.28)
    path.lineTo(x + s * 0.08, y + s * 0.82)
    path.close()
    c.drawPath(path, fill=0, stroke=1)
    c.setLineWidth(5)
    c.line(x + s * 0.30, y + s * 0.52, x + s * 0.46, y + s * 0.35)
    c.line(x + s * 0.46, y + s * 0.35, x + s * 0.74, y + s * 0.67)


def draw_header(c: canvas.Canvas) -> None:
    x, y, w, h = 60, PAGE_H - 300, PAGE_W - 120, 240
    c.setFillColor(HEADER_BLUE)
    c.setStrokeColor(NAVY)
    c.setLineWidth(7)
    c.roundRect(x, y, w, h, 38, fill=1, stroke=1)
    c.setFillColor(INK)
    c.setFont(FONT, 52)
    c.drawCentredString(
        x + w * 0.43,
        y + 148,
        "SQL-Grounded Vietnamese TableQA: A Multi-Agent Demo",
    )
    c.drawCentredString(
        x + w * 0.43,
        y + 90,
        "for Reliable Answers from Real Open-ViTabQA Tables",
    )
    c.setFont(FONT, 30)
    c.drawRightString(x + w - 50, y + 47, "Nguyen Huynh Hoang Kha - 25195654/1")

    logo_x, logo_y, logo_w, logo_h = x + w - 700, y + h - 112, 640, 88
    c.setFillColor(WHITE)
    c.setStrokeColor(NAVY)
    c.setLineWidth(5)
    c.rect(logo_x, logo_y, logo_w, logo_h, fill=1, stroke=1)
    c.setFillColor(NAVY)
    c.rect(logo_x + 12, logo_y + 12, 78, 64, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont(BLACK, 24)
    c.drawCentredString(logo_x + 51, logo_y + 42, "BCU")
    c.setFillColor(NAVY)
    c.setFont(BLACK, 42)
    c.drawString(logo_x + 112, logo_y + 48, "BIRMINGHAM CITY")
    c.setFont(BOLD, 34)
    c.drawString(logo_x + 112, logo_y + 13, "University")

    c.setFillColor(INK)
    c.setFont(BOLD, 20)
    c.drawString(
        x + 52,
        y + 31,
        "BSc (Hons) Computer Science | Supervisors: Nguyen Luu Thuy Ngan, Dang Van Thin | 06 June 2026",
    )


def arrow_head(c: canvas.Canvas, sx: float, sy: float, ex: float, ey: float, color: colors.Color = NAVY) -> None:
    import math

    ang = math.atan2(ey - sy, ex - sx)
    length = 18
    spread = 0.45
    p1 = (ex - length * math.cos(ang - spread), ey - length * math.sin(ang - spread))
    p2 = (ex - length * math.cos(ang + spread), ey - length * math.sin(ang + spread))
    c.setFillColor(color)
    p = c.beginPath()
    p.moveTo(ex, ey)
    p.lineTo(*p1)
    p.lineTo(*p2)
    p.close()
    c.drawPath(p, fill=1, stroke=0)


def process_box(c: canvas.Canvas, x: float, y: float, w: float, h: float, label: str, side: str) -> None:
    c.setFillColor(PANEL_PALE)
    c.setStrokeColor(NAVY)
    c.setLineWidth(2)
    c.roundRect(x, y, w, h, 12, fill=1, stroke=1)
    c.setFillColor(INK)
    c.setFont(BOLD, 20)
    c.drawString(x + 16, y + h - 28, label)
    c.setFont(FONT, 16.2)
    for i, line in enumerate(wrap_text(side, FONT, 16.2, w - 34)[:2]):
        c.drawString(x + 18, y + h - 55 - i * 21, line)


def chevron(c: canvas.Canvas, x: float, y: float, w: float, h: float, label: str) -> None:
    c.setFillColor(NAVY)
    p = c.beginPath()
    p.moveTo(x, y + h)
    p.lineTo(x + w / 2, y + h * 0.55)
    p.lineTo(x + w, y + h)
    p.lineTo(x + w, y + h * 0.25)
    p.lineTo(x + w / 2, y - h * 0.15)
    p.lineTo(x, y + h * 0.25)
    p.close()
    c.drawPath(p, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont(BOLD, 17)
    c.drawCentredString(x + w / 2, y + h * 0.48, label)


def step_badge(c: canvas.Canvas, x: float, y: float, size: float, number: int, label: str) -> None:
    c.setFillColor(NAVY)
    c.circle(x + size / 2, y + size / 2, size / 2, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont(BLACK, 28)
    c.drawCentredString(x + size / 2, y + size / 2 - 9, str(number))


def draw_methods_figure(c: canvas.Canvas, x: float, y: float, w: float, h: float) -> None:
    c.setFillColor(INK)
    c.setFont(BLACK, 32)
    c.drawCentredString(x + w / 2, y + h - 42, "Experimental Pipeline")
    left_x = x + 102
    right_x = x + w * 0.55
    box_w = w * 0.41
    row_h = 102
    start_y = y + h - 150
    rows = [
        ("Data", "Open-ViTabQA tables and questions are loaded from real JSON files.", "Real tables, 329 indexed demo tables"),
        ("Schema", "Headers, aliases, cells, and numeric shadow columns are normalised.", "bge-m3 ranks question-column relevance"),
        ("Plan", "The coordinator maps the question to lookup, count, max, min, filter, or compare.", "Operation plan guides SQL shape"),
        ("SQL", "qwen2.5-coder:14b proposes executable SQLite over table rows.", "Guards repair column and ordering errors"),
        ("Evidence", "SQL execution returns rows used as the only support for answering.", "Empty retrieval triggers fallback or re-plan"),
        ("Answer", "qwen2.5:7b writes the answer, verifier checks support, confidence is logged.", "Answer, SQL, evidence, trace are displayed"),
    ]
    for i, (stage, left, right) in enumerate(rows):
        ry = start_y - i * row_h
        step_badge(c, x + 18, ry + 19, 62, i + 1, stage)
        process_box(c, left_x, ry + 6, box_w, 88, stage, left)
        process_box(c, right_x, ry + 6, box_w, 88, "Output", right)
        c.setStrokeColor(NAVY)
        c.setLineWidth(2)
        c.line(left_x + box_w + 8, ry + 50, right_x - 10, ry + 50)
        arrow_head(c, left_x + box_w + 8, ry + 50, right_x - 10, ry + 50, NAVY)
    figure_label(c, "Fig. 1  Multi-agent SQL-grounded processing flow", x + w * 0.29, y + 8, w * 0.42)


def draw_interface_mockup(c: canvas.Canvas, x: float, y: float, w: float, h: float) -> None:
    c.setFillColor(WHITE)
    c.setStrokeColor(NAVY)
    c.setLineWidth(3)
    c.roundRect(x, y, w, h, 15, fill=1, stroke=1)
    c.setFillColor(colors.HexColor("#EEF4FA"))
    sidebar_w = w * 0.21
    c.rect(x, y, sidebar_w, h, fill=1, stroke=0)
    c.setFillColor(NAVY)
    c.roundRect(x + 14, y + h - 66, 44, 44, 9, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont(BLACK, 15)
    c.drawCentredString(x + 36, y + h - 41, "SQL")
    c.setFillColor(INK)
    c.setFont(BOLD, 16)
    c.drawString(x + 66, y + h - 38, "Vietnamese TableQA")
    c.setFont(FONT, 12)
    c.setFillColor(GREY)
    c.drawString(x + 66, y + h - 57, "Real data + trace")
    for i, q in enumerate(["Tallest NYC building?", "Hero awarded?", "Which club won?"]):
        yy = y + h - 118 - i * 58
        c.setFillColor(WHITE if i else colors.HexColor("#E6F6F7"))
        c.setStrokeColor(GRID)
        c.roundRect(x + 14, yy, sidebar_w - 24, 44, 8, fill=1, stroke=1)
        c.setFillColor(INK)
        c.setFont(BOLD if i == 0 else FONT, 10.2)
        c.drawString(x + 24, yy + 25, q)

    main_x = x + sidebar_w + 18
    main_w = w - sidebar_w - 34
    c.setFillColor(WHITE)
    c.setStrokeColor(colors.HexColor("#CBD5E1"))
    c.roundRect(main_x, y + h - 126, main_w, 82, 12, fill=1, stroke=1)
    c.setFillColor(GREY)
    c.setFont(FONT, 13)
    c.drawString(main_x + 22, y + h - 72, "Demo without training - real data")
    c.setFillColor(INK)
    c.setFont(BLACK, 21)
    c.drawString(main_x + 22, y + h - 105, "Tallest Buildings in New York City")

    c.setFillColor(WHITE)
    c.setStrokeColor(colors.HexColor("#CBD5E1"))
    c.roundRect(main_x, y + h - 235, main_w, 86, 12, fill=1, stroke=1)
    c.setFillColor(INK)
    c.setFont(FONT, 15)
    c.drawString(main_x + 20, y + h - 186, "Question: Which building has the most floors?")
    c.setFillColor(TEAL)
    c.roundRect(main_x + 20, y + h - 223, 162, 31, 7, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont(BOLD, 16)
    c.drawString(main_x + 42, y + h - 213, "Run pipeline")

    half_w = (main_w - 18) / 2
    c.setFillColor(WHITE)
    c.setStrokeColor(colors.HexColor("#CBD5E1"))
    c.roundRect(main_x, y + 42, half_w, 148, 12, fill=1, stroke=1)
    c.roundRect(main_x + half_w + 18, y + 42, half_w, 148, 12, fill=1, stroke=1)
    c.setFillColor(INK)
    c.setFont(BLACK, 18)
    c.drawString(main_x + 22, y + 156, "Answer")
    c.drawString(main_x + half_w + 40, y + 156, "Trace")
    c.setFont(BLACK, 31)
    c.setFillColor(TEAL)
    c.drawString(main_x + 24, y + 103, "110 floors")
    c.setFillColor(GREY)
    c.setFont(FONT, 13)
    c.drawString(main_x + 24, y + 78, "Grounded by SQL evidence")
    c.setFont(FONT, 10.2)
    traces = ["schema: c2=Floors", "SQL: ORDER BY floors DESC", "evidence: One World Trade Center", "verifier: passed"]
    for i, line in enumerate(traces):
        c.drawString(main_x + half_w + 40, y + 126 - i * 20, line)

    figure_label(c, "Fig. 2  Demo interface", x + w * 0.31, y + 8, w * 0.38)


def draw_terminal_mockup(c: canvas.Canvas, x: float, y: float, w: float, h: float) -> None:
    c.setFillColor(colors.HexColor("#111827"))
    c.setStrokeColor(NAVY)
    c.setLineWidth(3)
    c.roundRect(x, y, w, h, 12, fill=1, stroke=1)
    c.setFillColor(colors.HexColor("#374151"))
    c.rect(x, y + h - 35, w, 35, fill=1, stroke=0)
    c.setFillColor(WHITE)
    c.setFont(BOLD, 13.5)
    c.drawString(x + 18, y + h - 23, "uvicorn app.main:app --host 0.0.0.0 --port 8000")
    logs = [
        "15:56:16 [TableQA] schema_linking  Top columns: Floors, Height, Name",
        "15:56:16 [TableQA] text_to_sql     qwen2.5-coder:14b validating SQL",
        "15:56:19 [TableQA] execute_sql     SELECT row_index,* FROM rows ORDER BY c2_num DESC LIMIT 1",
        "15:56:19 [TableQA] evidence        SQL returned 1 evidence row",
        "15:56:20 [TableQA] verifier        deterministic evidence verifier passed=True",
        "15:56:20 [TableQA] done            Answer ready, confidence=1.0",
    ]
    c.setFont(FONT, 13.6)
    for i, line in enumerate(logs):
        c.setFillColor(colors.HexColor("#A7F3D0") if i in [0, 3, 5] else colors.HexColor("#E5E7EB"))
        c.drawString(x + 18, y + h - 62 - i * 24, line)
    figure_label(c, "Fig. 3  Runtime progress log", x + w * 0.30, y + 8, w * 0.40)


def draw_sql_evidence(c: canvas.Canvas, x: float, y: float, w: float, h: float) -> None:
    c.setFillColor(WHITE)
    c.setStrokeColor(NAVY)
    c.setLineWidth(3)
    c.roundRect(x, y, w, h, 12, fill=1, stroke=1)
    c.setFillColor(colors.HexColor("#EAF2FE"))
    c.rect(x, y + h - 43, w, 43, fill=1, stroke=0)
    c.setFillColor(INK)
    c.setFont(BLACK, 18)
    c.drawString(x + 16, y + h - 28, "SQL + Evidence Example")
    c.setFont(FONT, 14)
    c.drawString(x + 18, y + h - 68, "SQL: SELECT row_index,* FROM rows ORDER BY floors_num DESC LIMIT 1")
    cols = ["Name", "City", "Floors", "Grounded answer"]
    vals = ["One World Trade Center", "New York", "110", "110 floors"]
    col_w = w / 4
    yy = y + h - 125
    for i, col in enumerate(cols):
        c.setFillColor(PANEL_PALE)
        c.setStrokeColor(GRID)
        c.rect(x + i * col_w, yy, col_w, 31, fill=1, stroke=1)
        c.setFillColor(INK)
        c.setFont(BOLD, 13)
        c.drawCentredString(x + i * col_w + col_w / 2, yy + 10, col)
        c.setFillColor(WHITE)
        c.rect(x + i * col_w, yy - 36, col_w, 36, fill=1, stroke=1)
        c.setFillColor(INK)
        c.setFont(FONT, 12)
        for j, line in enumerate(wrap_text(vals[i], FONT, 12, col_w - 10)[:2]):
            c.drawCentredString(x + i * col_w + col_w / 2, yy - 15 - j * 13, line)
    figure_label(c, "Fig. 4  SQL + executed evidence rows", x + w * 0.24, y + 8, w * 0.52)


def draw_model_stack(c: canvas.Canvas, x: float, y: float, w: float, h: float) -> None:
    c.setFillColor(WHITE)
    c.setStrokeColor(NAVY)
    c.setLineWidth(3)
    c.roundRect(x, y, w, h, 12, fill=1, stroke=1)
    c.setFillColor(colors.HexColor("#EAF2FE"))
    c.rect(x, y + h - 40, w, 40, fill=1, stroke=0)
    c.setFillColor(INK)
    c.setFont(BLACK, 18)
    c.drawString(x + 16, y + h - 27, "Model / Runtime Stack")
    items = [
        ("bge-m3", "schema embedding"),
        ("qwen2.5-coder:14b", "SQL generation"),
        ("qwen2.5:7b", "answer + verifier"),
        ("SQLite", "evidence execution"),
        ("FastAPI", "demo GUI"),
    ]
    chip_w = (w - 55) / 2
    chip_h = 42
    for i, (name, role) in enumerate(items):
        row = i // 2
        col = i % 2
        cx = x + 18 + col * (chip_w + 18)
        cy = y + h - 95 - row * 53
        if i == 4:
            cx = x + 18
            chip_w_i = w - 36
        else:
            chip_w_i = chip_w
        c.setFillColor(PANEL_PALE)
        c.setStrokeColor(GRID)
        c.setLineWidth(1.8)
        c.roundRect(cx, cy, chip_w_i, chip_h, 9, fill=1, stroke=1)
        c.setFillColor(INK)
        c.setFont(BOLD, 14)
        c.drawString(cx + 12, cy + 23, name)
        c.setFont(FONT, 11)
        c.drawString(cx + 12, cy + 8, role)
    figure_label(c, "Fig. 4  Runtime stack for 24 GB VRAM", x + w * 0.24, y + 8, w * 0.52)


def draw_baseline_bars(c: canvas.Canvas, x: float, y: float, w: float, h: float) -> None:
    data = [
        ("Zero-shot", 0.000, 0.077),
        ("LoRA", 0.436, 0.500),
        ("QLoRA", 0.419, 0.487),
        ("Text-SQL", 0.491, 0.579),
        ("No verifier", 0.517, 0.603),
        ("Final", 0.586, 0.674),
    ]
    c.setFillColor(WHITE)
    c.setStrokeColor(NAVY)
    c.setLineWidth(3)
    c.roundRect(x, y, w, h, 12, fill=1, stroke=1)
    c.setFillColor(INK)
    c.setFont(BLACK, 19)
    c.drawString(x + 20, y + h - 31, "Answer Quality")
    base_y = y + 58
    max_h = h - 112
    group_w = (w - 65) / len(data)
    for i, (name, em, f1) in enumerate(data):
        gx = x + 36 + i * group_w
        c.setFillColor(BLUE)
        c.rect(gx, base_y, group_w * 0.27, max_h * em / 0.72, fill=1, stroke=0)
        c.setFillColor(TEAL)
        c.rect(gx + group_w * 0.31, base_y, group_w * 0.27, max_h * f1 / 0.72, fill=1, stroke=0)
        c.setFillColor(INK)
        c.setFont(FONT, 11.5)
        c.drawCentredString(gx + group_w * 0.29, base_y - 22, name)
    c.setStrokeColor(GREY)
    c.line(x + 28, base_y, x + w - 18, base_y)
    c.setFillColor(BLUE)
    c.rect(x + w - 120, y + h - 27, 12, 8, fill=1, stroke=0)
    c.setFillColor(TEAL)
    c.rect(x + w - 68, y + h - 27, 12, 8, fill=1, stroke=0)
    c.setFillColor(INK)
    c.setFont(FONT, 12)
    c.drawString(x + w - 104, y + h - 29, "EM")
    c.drawString(x + w - 52, y + h - 29, "F1")
    figure_label(c, "Fig. 5  EM/F1 answer quality", x + w * 0.25, y + 8, w * 0.50)


def draw_unsupported_chart(c: canvas.Canvas, x: float, y: float, w: float, h: float) -> None:
    data = [
        ("Zero-shot", 42.8),
        ("LoRA", 19.2),
        ("Text-SQL", 12.4),
        ("No verifier", 9.8),
        ("Final", 4.6),
    ]
    c.setFillColor(WHITE)
    c.setStrokeColor(NAVY)
    c.setLineWidth(3)
    c.roundRect(x, y, w, h, 12, fill=1, stroke=1)
    c.setFillColor(INK)
    c.setFont(BLACK, 19)
    c.drawString(x + 20, y + h - 31, "Unsupported Answer Rate")
    bar_x = x + 125
    bar_w = w - 170
    for i, (name, val) in enumerate(data):
        yy = y + h - 74 - i * 33
        c.setFillColor(INK)
        c.setFont(FONT, 12.2)
        c.drawRightString(bar_x - 10, yy, name)
        c.setFillColor(colors.HexColor("#E5E7EB"))
        c.roundRect(bar_x, yy - 4, bar_w, 10, 5, fill=1, stroke=0)
        c.setFillColor(RED if name != "Final" else GREEN)
        c.roundRect(bar_x, yy - 4, bar_w * val / 45.0, 10, 5, fill=1, stroke=0)
        c.setFillColor(INK)
        c.setFont(BOLD, 11)
        c.drawString(bar_x + bar_w * val / 45.0 + 5, yy - 4, f"{val:.1f}%")
    figure_label(c, "Fig. 6  Unsupported answers reduced to 4.6%", x + w * 0.19, y + 8, w * 0.62)


def draw_error_reduction(c: canvas.Canvas, x: float, y: float, w: float, h: float) -> None:
    data = [
        ("Schema", 38, 22),
        ("SQL fail", 76, 43),
        ("Empty retrieval", 69, 37),
        ("Unsupported", 71, 46),
        ("Verifier miss", 17, 8),
    ]
    c.setFillColor(WHITE)
    c.setStrokeColor(NAVY)
    c.setLineWidth(3)
    c.roundRect(x, y, w, h, 12, fill=1, stroke=1)
    c.setFillColor(INK)
    c.setFont(BLACK, 19)
    c.drawString(x + 20, y + h - 31, "Failure Modes per 1,000")
    chart_x = x + 118
    chart_w = w - 168
    for i, (name, before, after) in enumerate(data):
        yy = y + h - 74 - i * 33
        c.setFillColor(INK)
        c.setFont(FONT, 12)
        c.drawRightString(chart_x - 10, yy - 4, name)
        c.setStrokeColor(GREY)
        c.line(chart_x, yy, chart_x + chart_w, yy)
        bx = chart_x + chart_w * before / 80
        ax = chart_x + chart_w * after / 80
        c.setFillColor(RED)
        c.circle(bx, yy, 5, fill=1, stroke=0)
        c.setFillColor(GREEN)
        c.circle(ax, yy, 5, fill=1, stroke=0)
        c.setStrokeColor(GREEN)
        c.setLineWidth(3)
        c.line(bx, yy, ax, yy)
        c.setFillColor(INK)
        c.setFont(BOLD, 10)
        c.drawString(bx + 7, yy + 4, str(before))
        c.drawString(ax + 7, yy - 13, str(after))
    figure_label(c, "Fig. 7  Diagnostic error reduction", x + w * 0.24, y + 8, w * 0.52)


def draw_metric_dials(c: canvas.Canvas, x: float, y: float, w: float, h: float) -> None:
    c.setFillColor(WHITE)
    c.setStrokeColor(NAVY)
    c.setLineWidth(3)
    c.roundRect(x, y, w, h, 12, fill=1, stroke=1)
    c.setFillColor(INK)
    c.setFont(BLACK, 19)
    c.drawString(x + 20, y + h - 31, "Operational Metrics")
    metrics = [
        ("SQL valid", "98.4%", BLUE),
        ("Exec ok", "95.7%", TEAL),
        ("Grounded", "90.4%", GREEN),
        ("Median", "1.8s", ORANGE),
    ]
    radius = min((w - 50) / 8, (h - 70) / 2)
    for i, (label, value, color) in enumerate(metrics):
        cx = x + 58 + i * ((w - 110) / 3)
        cy = y + 90
        c.setFillColor(colors.HexColor("#EEF2F7"))
        c.circle(cx, cy, radius, fill=1, stroke=0)
        c.setStrokeColor(color)
        c.setLineWidth(8)
        c.circle(cx, cy, radius - 4, fill=0, stroke=1)
        c.setFillColor(color)
        c.setFont(BLACK, 22)
        c.drawCentredString(cx, cy + 2, value)
        c.setFillColor(INK)
        c.setFont(BOLD, 12.5)
        c.drawCentredString(cx, y + 28, label)
    figure_label(c, "Fig. 8  Runtime stability metrics", x + w * 0.24, y + 8, w * 0.52)


def draw_interpretation_note(c: canvas.Canvas, x: float, y: float, w: float, h: float) -> None:
    c.setFillColor(PANEL_PALE)
    c.setStrokeColor(NAVY)
    c.setLineWidth(2)
    c.roundRect(x, y, w, h, 12, fill=1, stroke=1)
    c.setFillColor(INK)
    c.setFont(BLACK, 19)
    c.drawString(x + 18, y + h - 29, "Interpretation")
    text = (
        "The system improves reliability by moving the main reasoning step from hidden text generation "
        "to executable SQL. This matters in Vietnamese tables because abbreviations, accents, units, "
        "and numeric formats can mislead a direct LLM. The trace lets the examiner inspect where the "
        "answer came from and why the verifier accepted it."
    )
    draw_wrapped(c, text, x + 18, y + h - 58, w - 36, FONT, 17.2, 21)


def draw_intro(c: canvas.Canvas, x: float, y: float, w: float, h: float) -> None:
    px, py, pw, ph = panel(c, x, y, w, h, "Introduction")
    icon_x = px - 7
    text_x = px + 90
    body_w = pw - 100
    sections = [
        (
            icon_question,
            "Vietnamese Table Question Answering asks a system to answer natural-language questions from a table. "
            "The hard cases require filtering, comparison, counting, ranking, temporal reasoning, and interpretation "
            "of abbreviated Vietnamese headers.",
        ),
        (
            icon_table,
            "Prompt-only LLMs can write fluent answers but may guess when the relevant row or column is ambiguous. "
            "Fine-tuning improves domain familiarity, yet it still does not guarantee row-level evidence or an auditable path.",
        ),
        (
            icon_database,
            "This project converts real Open-ViTabQA tables into SQLite, generates SQL, executes it, and gives the answer "
            "only from returned evidence rows. The demo indexes 329 real tables and does not use mock responses.",
        ),
        (
            icon_shield,
            "Aim: build a demo-ready multi-agent pipeline that exposes the SQL, evidence, verifier decision, confidence score, "
            "and progress trace so examiners can see how each answer was produced.",
        ),
    ]
    yy = py + ph - 38
    for icon_fn, text in sections:
        icon_fn(c, icon_x, yy - 62, 55)
        yy = draw_wrapped(c, text, text_x, yy, body_w, FONT, 20, 25)
        yy -= 44

    c.setFillColor(PANEL_PALE)
    c.setStrokeColor(NAVY)
    c.setLineWidth(2)
    c.roundRect(text_x, py + 185, body_w, 255, 12, fill=1, stroke=1)
    c.setFillColor(INK)
    c.setFont(BLACK, 24)
    c.drawString(text_x + 22, py + 405, "Key contributions")
    contribution_text = (
        "A schema-linked SQL agent maps Vietnamese questions to executable table operations instead of relying on hidden reasoning.\n"
        "An evidence-first answerer uses returned rows as the source of truth, so every final answer can be inspected.\n"
        "A verifier, confidence score, and runtime trace make the artifact easier to debug, film, and defend during assessment."
    )
    draw_wrapped(c, contribution_text, text_x + 22, py + 370, body_w - 44, FONT, 17.4, 22, bullet=True)

    c.setFillColor(PANEL_PALE)
    c.setStrokeColor(NAVY)
    c.setLineWidth(2)
    c.roundRect(text_x, py + 20, body_w, 118, 12, fill=1, stroke=1)
    c.setFillColor(INK)
    c.setFont(BLACK, 24)
    c.drawString(text_x + 22, py + 86, "Research question")
    c.setFont(FONT, 19)
    draw_wrapped(
        c,
        "Can executable SQL grounding and multi-agent verification make Vietnamese TableQA answers more reliable than direct LLM answering?",
        text_x + 22,
        py + 58,
        body_w - 44,
        FONT,
        19,
        23,
    )


def draw_methods(c: canvas.Canvas, x: float, y: float, w: float, h: float) -> None:
    px, py, pw, ph = panel(c, x, y, w, h, "Methods")
    bullets = (
        "Dataset split: 7,928 train, 991 validation, 992 test questions from Open-ViTabQA-style tables.\n"
        "Runtime models: bge-m3 for schema embeddings, qwen2.5-coder:14b for SQL, qwen2.5:7b for answer synthesis and verification.\n"
        "Evaluation: exact match, F1, grounding, unsupported answer rate, SQL validity, execution success, semantic SQL accuracy, verifier catch rate, latency, and trace completeness."
    )
    draw_wrapped(c, bullets, px, py + ph - 30, pw, FONT, 20.5, 26, bullet=True)
    left_w = pw * 0.58
    right_x = px + pw * 0.615
    right_w = pw * 0.365
    draw_methods_figure(c, px + 12, py + 95, left_w, ph - 278)
    draw_terminal_mockup(c, right_x, py + 690, right_w, 224)
    draw_interface_mockup(c, right_x, py + 352, right_w, 285)
    draw_model_stack(c, right_x, py + 82, right_w, 218)


def draw_results(c: canvas.Canvas, x: float, y: float, w: float, h: float) -> None:
    px, py, pw, ph = panel(c, x, y, w, h, "Results and Discussion")
    summary = (
        "The final SQL-grounded system reached EM 0.586 and F1 0.674, compared with 0.548 and 0.636 for the earlier full system. "
        "Grounding increased to 0.904, unsupported answers fell to 4.6%, SQL execution success reached 95.7%, and median latency was 1.8 seconds after caching. "
        "The largest practical gain is not only a higher score: the system gives a visible evidence trail, so wrong or uncertain answers are easier to diagnose."
    )
    draw_wrapped(c, summary, px, py + ph - 36, pw * 0.36, FONT, 20.5, 26, bullet=True)
    chart_w = pw * 0.292
    top_y = py + ph - 288
    bottom_y = py + 54
    draw_baseline_bars(c, px + pw * 0.368, top_y, chart_w, 248)
    draw_unsupported_chart(c, px + pw * 0.685, top_y, chart_w, 248)
    draw_error_reduction(c, px + pw * 0.368, bottom_y, chart_w, 232)
    draw_metric_dials(c, px + pw * 0.685, bottom_y, chart_w, 232)
    draw_sql_evidence(c, px, py + 62, pw * 0.34, 248)
    draw_interpretation_note(c, px, py + 324, pw * 0.34, 145)


def draw_conclusions(c: canvas.Canvas, x: float, y: float, w: float, h: float) -> None:
    px, py, pw, ph = panel(c, x, y, w, h, "Conclusions")
    text = (
        "Executable retrieval made the demo more trustworthy: the system does not only state an answer, it shows the SQL path and evidence rows behind that answer.\n"
        "The verifier is advisory, while deterministic evidence checks remain authoritative for demo stability.\n"
        "The approach is strongest for lookup, filtering, maximum/minimum, counting, comparison, and aggregation questions.\n"
        "Limitations remain for descriptive questions, noisy table conversion, and rare Vietnamese alias or unit forms.\n"
        "For the presentation, the most convincing demonstration is to show a question, run the pipeline, then open SQL, evidence, progress, and verifier tabs."
    )
    draw_wrapped(c, text, px, py + ph - 30, pw, FONT, 20, 25, bullet=True)


def draw_next_steps(c: canvas.Canvas, x: float, y: float, w: float, h: float) -> None:
    px, py, pw, ph = panel(c, x, y, w, h, "References / Future Work")
    text = (
        "Future work: evaluate on larger and noisier Vietnamese table collections; build a stronger alias, abbreviation, and unit-normalisation resource; collect labelled verifier-mismatch examples; add adaptive routing for descriptive questions; and compare newer open multilingual models under the same SQL-grounded protocol.\n\n"
        "Key sources: Open-ViTabQA dataset; Vietnamese TableQA final report; project artifact HoangKha1810/ChatBot-OpenViTab; qwen2.5 and bge-m3 model families used in the non-training demo. The artifact is designed for reproducibility: install dependencies, pull models on the GPU server, launch Ollama, run Uvicorn, and record the browser demo."
    )
    draw_wrapped(c, text, px, py + ph - 30, pw, FONT, 19, 24)
    c.setFillColor(PANEL_PALE)
    c.setStrokeColor(NAVY)
    c.setLineWidth(2)
    c.roundRect(px, py + 18, pw, 72, 10, fill=1, stroke=1)
    c.setFillColor(INK)
    c.setFont(BLACK, 20)
    c.drawCentredString(px + pw / 2, py + 60, "Artifact")
    c.setFont(BOLD, 18)
    c.drawCentredString(px + pw / 2, py + 33, "github.com/HoangKha1810/ChatBot-OpenViTab")


def draw_connectors(c: canvas.Canvas) -> None:
    c.setStrokeColor(NAVY)
    c.setLineWidth(8)
    for off in [0, 22, 44]:
        c.line(1195, 1720 - off, 1342, 1720 - off)
    for off in [0, 22, 44, 66]:
        c.line(1195, 910 + off, 1328, 910 + off)
    for off in [0, 22, 44]:
        c.line(1988, 705 + off, 2027, 705 + off)


def build_poster(output: Path = OUT_FILE, downloads_output: Path = DOWNLOADS_FILE) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(output), pagesize=landscape(A0))
    c.setTitle("SQL-Grounded Vietnamese TableQA Template Style Poster")
    c.setAuthor("Nguyen Huynh Hoang Kha")
    c.setFillColor(WHITE)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    draw_header(c)
    draw_intro(c, 60, 875, 1120, 1205)
    draw_methods(c, 1350, 875, 1960, 1205)
    draw_results(c, 60, 95, 1930, 730)
    draw_conclusions(c, 2030, 600, 1280, 300)
    draw_next_steps(c, 2030, 95, 1280, 450)
    draw_connectors(c)
    c.showPage()
    c.save()
    downloads_output.write_bytes(output.read_bytes())


if __name__ == "__main__":
    build_poster()
    print(f"Wrote {OUT_FILE}")
    print(f"Wrote {DOWNLOADS_FILE}")
