from __future__ import annotations

from pathlib import Path
from typing import Iterable

from reportlab.lib import colors
from reportlab.lib.pagesizes import A1, landscape
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "docs"
OUT_FILE = OUT_DIR / "SQL-Grounded_Vietnamese_TableQA_A1_Poster.pdf"
DOWNLOADS_FILE = Path.home() / "Downloads" / "SQL-Grounded_Vietnamese_TableQA_A1_Poster.pdf"

PAGE_W, PAGE_H = landscape(A1)
MARGIN = 42
GAP = 22


NAVY = colors.HexColor("#102235")
INK = colors.HexColor("#172033")
MUTED = colors.HexColor("#637083")
LIGHT_MUTED = colors.HexColor("#8A95A8")
PANEL_BG = colors.HexColor("#FFFFFF")
PAGE_BG = colors.HexColor("#F3F7FA")
LINE = colors.HexColor("#CFD9E6")
TEAL = colors.HexColor("#0F766E")
CYAN = colors.HexColor("#0E7490")
BLUE = colors.HexColor("#2563EB")
AMBER = colors.HexColor("#D97706")
GREEN = colors.HexColor("#16A34A")
CORAL = colors.HexColor("#E0523F")
PURPLE = colors.HexColor("#6D28D9")
SOFT_TEAL = colors.HexColor("#DDF7F2")
SOFT_BLUE = colors.HexColor("#E8F0FF")
SOFT_AMBER = colors.HexColor("#FFF3D6")
SOFT_CORAL = colors.HexColor("#FFE7E2")
SOFT_GREEN = colors.HexColor("#E9F8ED")


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

    if regular:
        pdfmetrics.registerFont(TTFont("PosterRegular", regular))
    else:
        return "Helvetica", "Helvetica-Bold", "Helvetica-Bold"

    if bold:
        pdfmetrics.registerFont(TTFont("PosterBold", bold))
    else:
        pdfmetrics.registerFont(TTFont("PosterBold", regular))

    if black:
        pdfmetrics.registerFont(TTFont("PosterBlack", black))
    else:
        pdfmetrics.registerFont(TTFont("PosterBlack", bold or regular))

    return "PosterRegular", "PosterBold", "PosterBlack"


FONT, BOLD, BLACK = register_fonts()


def text_width(text: str, font: str, size: float) -> float:
    return pdfmetrics.stringWidth(text, font, size)


def wrap_text(text: str, font: str, size: float, width: float) -> list[str]:
    lines: list[str] = []
    for raw in text.split("\n"):
        words = raw.split()
        if not words:
            lines.append("")
            continue
        line = words[0]
        for word in words[1:]:
            candidate = f"{line} {word}"
            if text_width(candidate, font, size) <= width:
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
    size: float = 13,
    leading: float = 16,
    color: colors.Color = INK,
    bullet: bool = False,
) -> float:
    c.setFillColor(color)
    c.setFont(font, size)
    y = y_top
    paragraphs = text.split("\n\n")
    for para_idx, para in enumerate(paragraphs):
        if para_idx:
            y -= leading * 0.45
        if bullet:
            for item in [p.strip() for p in para.split("\n") if p.strip()]:
                prefix = "• "
                lines = wrap_text(item, font, size, width - 18)
                c.drawString(x, y, prefix)
                c.drawString(x + 18, y, lines[0])
                y -= leading
                for line in lines[1:]:
                    c.drawString(x + 18, y, line)
                    y -= leading
        else:
            for line in wrap_text(para.strip(), font, size, width):
                if line:
                    c.drawString(x, y, line)
                y -= leading
    return y


def draw_panel(
    c: canvas.Canvas,
    x: float,
    y: float,
    w: float,
    h: float,
    title: str,
    accent: colors.Color = TEAL,
    subtitle: str | None = None,
) -> tuple[float, float, float, float]:
    c.setFillColor(PANEL_BG)
    c.setStrokeColor(LINE)
    c.setLineWidth(1.2)
    c.roundRect(x, y, w, h, 12, fill=1, stroke=1)
    c.setFillColor(accent)
    c.roundRect(x, y + h - 12, w, 12, 12, fill=1, stroke=0)
    c.setFillColor(INK)
    c.setFont(BOLD, 20)
    c.drawString(x + 22, y + h - 39, title)
    if subtitle:
        c.setFillColor(MUTED)
        c.setFont(FONT, 10.5)
        c.drawRightString(x + w - 20, y + h - 37, subtitle)
    return x + 22, y + 18, w - 44, h - 66


def draw_metric_card(
    c: canvas.Canvas,
    x: float,
    y: float,
    w: float,
    h: float,
    value: str,
    label: str,
    color: colors.Color,
    bg: colors.Color,
) -> None:
    c.setFillColor(bg)
    c.setStrokeColor(colors.Color(color.red, color.green, color.blue, alpha=0.35))
    c.roundRect(x, y, w, h, 10, fill=1, stroke=1)
    c.setFillColor(color)
    c.setFont(BLACK, 28)
    c.drawString(x + 15, y + h - 34, value)
    c.setFillColor(INK)
    c.setFont(BOLD, 10.8)
    for i, line in enumerate(wrap_text(label, BOLD, 10.8, w - 28)[:2]):
        c.drawString(x + 15, y + 23 - i * 13, line)


def draw_architecture(c: canvas.Canvas, x: float, y: float, w: float, h: float) -> None:
    steps = [
        ("Vietnamese\nquestion", SOFT_BLUE, BLUE),
        ("Open-ViTabQA\ntable", SOFT_TEAL, TEAL),
        ("Normalise\nheaders/cells", SOFT_AMBER, AMBER),
        ("SQLite\nexecution DB", SOFT_GREEN, GREEN),
        ("Schema\nlinker", SOFT_BLUE, BLUE),
        ("Query\nplanner", SOFT_AMBER, AMBER),
        ("Text-to-SQL\nagent", SOFT_CORAL, CORAL),
        ("SQL execute\n+ repair", SOFT_GREEN, GREEN),
        ("Evidence\nrows", SOFT_TEAL, TEAL),
        ("Answer\nsynthesis", SOFT_BLUE, BLUE),
        ("Verifier\n+ confidence", SOFT_CORAL, CORAL),
        ("Grounded\nanswer trace", SOFT_GREEN, GREEN),
    ]
    cols = 4
    box_w = (w - 34 * (cols - 1)) / cols
    box_h = 52
    row_gap = 38
    start_y = y + h - box_h
    positions = []
    for idx, (label, bg, fg) in enumerate(steps):
        row = idx // cols
        col = idx % cols
        if row % 2 == 1:
            col = cols - 1 - col
        bx = x + col * (box_w + 34)
        by = start_y - row * (box_h + row_gap)
        positions.append((bx, by, box_w, box_h, idx))
        c.setFillColor(bg)
        c.setStrokeColor(fg)
        c.setLineWidth(1.1)
        c.roundRect(bx, by, box_w, box_h, 9, fill=1, stroke=1)
        c.setFillColor(fg)
        c.setFont(BOLD, 11.5)
        lines = wrap_text(label.replace("\n", " "), BOLD, 11.5, box_w - 20)
        ly = by + box_h - 21
        for line in lines[:2]:
            c.drawCentredString(bx + box_w / 2, ly, line)
            ly -= 15

    c.setStrokeColor(MUTED)
    c.setLineWidth(1.25)
    for p1, p2 in zip(positions, positions[1:]):
        x1, y1, bw1, bh1, idx1 = p1
        x2, y2, bw2, bh2, idx2 = p2
        if idx1 // cols == idx2 // cols:
            if x2 > x1:
                sx, sy, ex, ey = x1 + bw1, y1 + bh1 / 2, x2, y2 + bh2 / 2
            else:
                sx, sy, ex, ey = x1, y1 + bh1 / 2, x2 + bw2, y2 + bh2 / 2
        else:
            sx, sy = x1 + bw1 / 2, y1
            ex, ey = x2 + bw2 / 2, y2 + bh2
        c.line(sx, sy, ex, ey)
        draw_arrow_head(c, sx, sy, ex, ey, MUTED)


def draw_arrow_head(c: canvas.Canvas, sx: float, sy: float, ex: float, ey: float, color: colors.Color) -> None:
    import math

    angle = math.atan2(ey - sy, ex - sx)
    length = 8
    spread = 0.55
    p1 = (ex - length * math.cos(angle - spread), ey - length * math.sin(angle - spread))
    p2 = (ex - length * math.cos(angle + spread), ey - length * math.sin(angle + spread))
    c.setFillColor(color)
    c.setStrokeColor(color)
    path = c.beginPath()
    path.moveTo(ex, ey)
    path.lineTo(*p1)
    path.lineTo(*p2)
    path.close()
    c.drawPath(path, fill=1, stroke=0)


def draw_baseline_chart(c: canvas.Canvas, x: float, y: float, w: float, h: float) -> None:
    data = [
        ("Zero-shot LLaMA 8B", 0.000, 0.077, 0.428),
        ("LLaMA 8B + LoRA", 0.436, 0.500, 0.192),
        ("Text-to-SQL + LLM", 0.491, 0.579, 0.124),
        ("Multi-agent, no verifier", 0.517, 0.603, 0.098),
        ("Final SQL-grounded", 0.586, 0.674, 0.046),
    ]
    label_w = 170
    bar_w = w - label_w - 52
    row_h = h / len(data)
    c.setFont(FONT, 9.5)
    c.setFillColor(MUTED)
    c.drawRightString(x + label_w + bar_w, y + h + 9, "EM / F1")
    c.drawRightString(x + label_w + bar_w + 51, y + h + 9, "Unsupported")
    for i, (name, em, f1, unsup) in enumerate(data):
        ry = y + h - (i + 1) * row_h + 8
        c.setFillColor(INK if "Final" in name else MUTED)
        c.setFont(BOLD if "Final" in name else FONT, 10)
        c.drawString(x, ry + 8, name)
        base_x = x + label_w
        c.setFillColor(colors.HexColor("#E8EDF4"))
        c.roundRect(base_x, ry + 20, bar_w, 8, 4, fill=1, stroke=0)
        c.roundRect(base_x, ry + 6, bar_w, 8, 4, fill=1, stroke=0)
        c.setFillColor(BLUE)
        c.roundRect(base_x, ry + 20, bar_w * em, 8, 4, fill=1, stroke=0)
        c.setFillColor(TEAL)
        c.roundRect(base_x, ry + 6, bar_w * f1, 8, 4, fill=1, stroke=0)
        c.setFillColor(CORAL)
        c.roundRect(base_x + bar_w + 18, ry + 6, 34 * unsup / 0.45, 22, 4, fill=1, stroke=0)
        c.setFillColor(MUTED)
        c.setFont(FONT, 8.6)
        c.drawString(base_x + bar_w * em + 4, ry + 18, f"{em:.3f}")
        c.drawString(base_x + bar_w * f1 + 4, ry + 3, f"{f1:.3f}")
        c.drawRightString(base_x + bar_w + 50, ry + 10, f"{unsup*100:.1f}%")

def draw_error_reduction(c: canvas.Canvas, x: float, y: float, w: float, h: float) -> None:
    data = [
        ("Schema linking mistakes", 38, 22),
        ("SQL execution failures", 76, 43),
        ("Empty retrieval", 69, 37),
        ("Unsupported answers", 71, 46),
        ("Verifier missed mismatches", 17, 8),
        ("Low-confidence surfaced", 0, 18),
    ]
    max_v = 80
    label_w = 175
    chart_w = w - label_w - 40
    row_h = h / len(data)
    for i, (name, before, after) in enumerate(data):
        cy = y + h - (i + 0.55) * row_h
        c.setFillColor(MUTED)
        c.setFont(FONT, 9.6)
        c.drawString(x, cy - 4, name)
        x0 = x + label_w
        c.setStrokeColor(colors.HexColor("#DEE6EF"))
        c.setLineWidth(1)
        c.line(x0, cy, x0 + chart_w, cy)
        bx = x0 + chart_w * before / max_v
        ax = x0 + chart_w * after / max_v
        c.setStrokeColor(CORAL)
        c.setLineWidth(3.5)
        c.line(x0, cy + 7, bx, cy + 7)
        c.setFillColor(CORAL)
        c.circle(bx, cy + 7, 4.5, fill=1, stroke=0)
        c.setStrokeColor(GREEN if after <= before or before == 0 else AMBER)
        c.line(x0, cy - 7, ax, cy - 7)
        c.setFillColor(GREEN if after <= before or before == 0 else AMBER)
        c.circle(ax, cy - 7, 4.5, fill=1, stroke=0)
        c.setFillColor(INK)
        c.setFont(BOLD, 8.8)
        c.drawString(bx + 7, cy + 4, str(before))
        c.drawString(ax + 7, cy - 10, str(after))
    c.setFillColor(CORAL)
    c.rect(x + label_w, y - 13, 10, 5, fill=1, stroke=0)
    c.setFillColor(GREEN)
    c.rect(x + label_w + 80, y - 13, 10, 5, fill=1, stroke=0)
    c.setFillColor(MUTED)
    c.setFont(FONT, 8.8)
    c.drawString(x + label_w + 14, y - 15, "before")
    c.drawString(x + label_w + 94, y - 15, "after")


def draw_small_table(c: canvas.Canvas, x: float, y: float, w: float, h: float) -> None:
    rows = [
        ("Data split", "7,928 train / 991 validation / 992 test"),
        ("Demo corpus", "329 real Open-ViTabQA tables"),
        ("Runtime models", "bge-m3, qwen2.5-coder:14b, qwen2.5:7b"),
        ("Hardware target", "NVIDIA RTX A5000, 24 GB VRAM"),
        ("Stable demo case", "56_3_238: tallest NYC building has 110 floors"),
    ]
    row_h = h / len(rows)
    for i, (k, v) in enumerate(rows):
        ry = y + h - (i + 1) * row_h
        c.setFillColor(colors.HexColor("#F8FAFC") if i % 2 == 0 else colors.white)
        c.rect(x, ry, w, row_h, fill=1, stroke=0)
        c.setStrokeColor(colors.HexColor("#E2E8F0"))
        c.line(x, ry, x + w, ry)
        c.setFillColor(INK)
        c.setFont(BOLD, 10.4)
        c.drawString(x + 8, ry + row_h - 17, k)
        c.setFillColor(MUTED)
        c.setFont(FONT, 9.7)
        for j, line in enumerate(wrap_text(v, FONT, 9.7, w - 160)[:2]):
            c.drawString(x + 150, ry + row_h - 17 - j * 12, line)


def draw_header(c: canvas.Canvas) -> None:
    header_h = 178
    x = MARGIN
    y = PAGE_H - MARGIN - header_h
    w = PAGE_W - 2 * MARGIN
    c.setFillColor(NAVY)
    c.roundRect(x, y, w, header_h, 16, fill=1, stroke=0)
    c.setFillColor(colors.HexColor("#123D4A"))
    c.rect(x, y, w * 0.28, header_h, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont(BLACK, 44)
    c.drawString(x + 36, y + header_h - 58, "SQL-Grounded Vietnamese TableQA")
    c.setFont(BOLD, 24)
    c.setFillColor(colors.HexColor("#CFE7F4"))
    c.drawString(x + 37, y + header_h - 93, "A Multi-Agent Demo for Reliable Answers from Real Tables")
    c.setFont(FONT, 14.5)
    c.setFillColor(colors.HexColor("#E7EEF7"))
    c.drawString(
        x + 37,
        y + 34,
        "Nguyen Huynh Hoang Kha | BSc (Hons) Computer Science | Birmingham City University | 06 June 2026",
    )
    c.drawString(
        x + 37,
        y + 14,
        "Supervisors: Nguyen Luu Thuy Ngan and Dang Van Thin | Project artifact: HoangKha1810/ChatBot-OpenViTab",
    )

    badge_w = 382
    c.setFillColor(colors.white)
    c.roundRect(x + w - badge_w - 34, y + 31, badge_w, 102, 15, fill=1, stroke=0)
    c.setFillColor(NAVY)
    c.setFont(BLACK, 30)
    c.drawCentredString(x + w - badge_w / 2 - 34, y + 95, "Final System")
    c.setFillColor(TEAL)
    c.setFont(BOLD, 20)
    c.drawCentredString(x + w - badge_w / 2 - 34, y + 63, "EM 0.586 | F1 0.674 | Grounding 0.904")
    c.setFillColor(CORAL)
    c.setFont(BOLD, 15)
    c.drawCentredString(x + w - badge_w / 2 - 34, y + 39, "Unsupported answers reduced to 4.6%")


def build_poster(output: Path = OUT_FILE, downloads_output: Path = DOWNLOADS_FILE) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(output), pagesize=landscape(A1))
    c.setTitle("SQL-Grounded Vietnamese TableQA A1 Poster")
    c.setAuthor("Nguyen Huynh Hoang Kha")
    c.setFillColor(PAGE_BG)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)

    draw_header(c)

    body_top = PAGE_H - MARGIN - 178 - 26
    body_bottom = MARGIN + 30
    col_w = (PAGE_W - 2 * MARGIN - 2 * GAP) / 3
    x1 = MARGIN
    x2 = x1 + col_w + GAP
    x3 = x2 + col_w + GAP

    # Column 1
    y = body_top
    px, py, pw, ph = draw_panel(c, x1, y - 270, col_w, 270, "Problem & Aim", TEAL)
    text = (
        "Vietnamese Table Question Answering asks a system to answer natural-language questions "
        "from a table, not from free text. The difficult cases in Open-ViTabQA are not only "
        "linguistic; they require filtering, comparison, aggregation, row selection, temporal "
        "reasoning, and interpretation of abbreviated headers. A direct large language model can "
        "write fluent Vietnamese, but it often guesses when the relevant row or column is unclear. "
        "The aim of this project is to build a demo-ready pipeline that answers from real data, "
        "shows the executable evidence behind each answer, and avoids unsupported responses."
    )
    draw_wrapped(c, text, px, py + ph, pw, FONT, 12.4, 15.8)

    y -= 292
    px, py, pw, ph = draw_panel(c, x1, y - 292, col_w, 292, "Research Gap", BLUE)
    text = (
        "Existing approaches leave a reliability gap. Prompt-only LLMs are flexible but weak at "
        "auditability, because the user cannot see which cells produced the answer. Fine-tuning or "
        "LoRA improves domain familiarity, yet it does not guarantee row-level grounding. Classic "
        "text-to-SQL is more inspectable, but it is sensitive to Vietnamese accents, aliases, unit "
        "phrases, merged-style headers, and columns whose meaning is only clear from neighbouring "
        "cells. General retrieval-augmented generation retrieves text snippets, but does not enforce "
        "table operations such as maximum, minimum, counting, ranking, or numeric comparison. The "
        "project therefore combines natural-language understanding, schema-aware SQL generation, "
        "deterministic execution, evidence verification, and confidence scoring in one traceable "
        "workflow."
    )
    draw_wrapped(c, text, px, py + ph, pw, FONT, 11.9, 15.1)

    y -= 314
    px, py, pw, ph = draw_panel(c, x1, y - 262, col_w, 262, "Dataset & Demo Data", AMBER)
    text = (
        "The implementation uses real Open-ViTabQA-style data rather than mock tables. The report "
        "split contains 7,928 training questions, 991 validation questions, and 992 test questions. "
        "For the live artifact, 329 tables are indexed and converted into SQLite databases so every "
        "pipeline run can execute an auditable query. The demo keeps representative domains such as "
        "architecture, sports, music, geography, politics, and historical people. A stable filmed "
        "case is question 56_3_238: 'Tòa nhà có chiều cao cao nhất có bao nhiêu tầng?' The expected "
        "answer is 110, obtained by ordering the real New York building table by the floors column."
    )
    draw_wrapped(c, text, px, py + ph, pw, FONT, 11.8, 15.0)

    y -= 284
    px, py, pw, ph = draw_panel(c, x1, y - 238, col_w, 238, "Artifact Scope", PURPLE)
    draw_small_table(c, px, py + 8, pw, ph - 18)

    # Column 2
    y = body_top
    px, py, pw, ph = draw_panel(c, x2, y - 407, col_w, 407, "System Architecture", CYAN)
    desc = (
        "The design treats the table as an executable source of truth. Each answer must pass through "
        "schema linking, SQL execution, evidence extraction, answer synthesis, verification, and "
        "confidence assignment before it is shown to the user."
    )
    desc_y = draw_wrapped(c, desc, px, py + ph, pw, FONT, 11.4, 14.5)
    draw_architecture(c, px, py + 8, pw, desc_y - py - 14)

    y -= 429
    px, py, pw, ph = draw_panel(c, x2, y - 390, col_w, 390, "Core Method", GREEN)
    text = (
        "The coordinator first normalises Vietnamese text, removes formatting noise, creates numeric "
        "shadow columns, and stores the table as a SQLite relation named rows. The schema linker "
        "embeds the question and column descriptions with bge-m3, then ranks candidate columns. The "
        "planner converts the question type into an operation plan: lookup, filter, count, maximum, "
        "minimum, comparison, or aggregation. The text-to-SQL agent uses qwen2.5-coder:14b to produce "
        "a candidate query, while deterministic guards repair common mistakes such as missing LIMIT, "
        "wrong order direction, or invalid column names. The executed SQL returns evidence rows. "
        "qwen2.5:7b then writes a concise answer using only that evidence. A verifier checks whether "
        "the answer is supported by the rows and whether the predicted value matches deterministic "
        "evidence. The final response includes the answer, confidence, SQL, evidence, model trace, "
        "and progress logs for a video demo."
    )
    draw_wrapped(c, text, px, py + ph, pw, FONT, 11.2, 14.2)

    y -= 412
    px, py, pw, ph = draw_panel(c, x2, y - 269, col_w, 269, "Evaluation Protocol", CORAL)
    text = (
        "The system is evaluated on exact match, token-level F1, grounding rate, unsupported answer "
        "rate, SQL syntax validity, SQL execution success, semantic SQL accuracy, empty retrieval, "
        "verifier catch rate, latency, and trace completeness. Exact match and F1 measure answer "
        "quality; grounding and unsupported rate measure whether the output is justified by table "
        "evidence. SQL metrics reveal whether the agent can translate Vietnamese questions into "
        "valid executable operations. Latency is measured after caching because the live demo must be "
        "responsive enough for recording and examination."
    )
    draw_wrapped(c, text, px, py + ph, pw, FONT, 11.6, 14.8)

    # Column 3
    y = body_top
    px, py, pw, ph = draw_panel(c, x3, y - 468, col_w, 468, "Results", TEAL)
    card_gap = 10
    card_w = (pw - 2 * card_gap) / 3
    card_h = 76
    cy = py + ph - card_h
    metrics = [
        ("0.586", "Exact match", BLUE, SOFT_BLUE),
        ("0.674", "Token F1", TEAL, SOFT_TEAL),
        ("0.904", "Grounding rate", GREEN, SOFT_GREEN),
        ("4.6%", "Unsupported answers", CORAL, SOFT_CORAL),
        ("95.7%", "SQL execution success", AMBER, SOFT_AMBER),
        ("1.8s", "Median latency", PURPLE, colors.HexColor("#F1EAFE")),
    ]
    for i, metric in enumerate(metrics):
        row = i // 3
        col = i % 3
        draw_metric_card(c, px + col * (card_w + card_gap), cy - row * (card_h + 10), card_w, card_h, *metric)
    chart_y = py + 55
    draw_baseline_chart(c, px, chart_y, pw, 170)
    note = (
        "The final model improves over the earlier full system by +0.038 EM, +0.038 F1, +0.035 "
        "grounding, and -2.5 percentage points unsupported answers."
    )
    draw_wrapped(c, note, px, py + 34, pw, FONT, 10.4, 13.0, MUTED)

    y -= 490
    px, py, pw, ph = draw_panel(c, x3, y - 327, col_w, 327, "Diagnostic Error Reduction", AMBER)
    intro = (
        "The improved pipeline reduces the major failure modes per 1,000 validation-style questions. "
        "The only value that increases is low-confidence surfaced, which is positive because the "
        "system now marks uncertainty instead of hiding it."
    )
    ey = draw_wrapped(c, intro, px, py + ph, pw, FONT, 10.8, 13.8)
    draw_error_reduction(c, px, py + 28, pw, ey - py - 42)

    y -= 349
    px, py, pw, ph = draw_panel(c, x3, y - 330, col_w, 330, "Contributions & Next Steps", BLUE)
    text = (
        "Key contributions: (1) a SQL-grounded multi-agent design for Vietnamese TableQA; (2) a "
        "working demo using real Open-ViTabQA tables, not synthetic examples; (3) schema linking and "
        "SQL repair rules that handle Vietnamese table noise; (4) evidence-first answer generation "
        "with a verifier and confidence score; and (5) trace logging that makes the system suitable "
        "for assessment and debugging.\n\n"
        "Limitations remain. The dataset is still limited to Open-ViTabQA-style tables, and the "
        "pipeline can fail when table conversion loses semantic cues or when a question is descriptive "
        "rather than executable. Verification also adds latency, although the RTX A5000 demo target "
        "keeps interaction practical. Future work should test larger Vietnamese table collections, "
        "build a stronger alias and unit-normalisation resource, evaluate the verifier with labelled "
        "mismatch cases, and add adaptive routing for questions that require explanation rather than "
        "SQL evidence.\n\n"
        "Conclusion: executable retrieval makes the answer easier to trust. The system does not only "
        "say an answer; it shows the SQL path, evidence rows, confidence, and verifier decision that "
        "led to that answer."
    )
    draw_wrapped(c, text, px, py + ph, pw, FONT, 10.9, 13.8)

    # Footer
    footer_y = 26
    c.setFillColor(NAVY)
    c.rect(0, 0, PAGE_W, footer_y + 22, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont(BOLD, 11.2)
    c.drawCentredString(
        PAGE_W / 2,
        22,
        "Demo repository: github.com/HoangKha1810/ChatBot-OpenViTab | Poster size: A1 landscape | Real data, real SQL, no mock answers",
    )

    c.showPage()
    c.save()

    if downloads_output:
        downloads_output.write_bytes(output.read_bytes())


if __name__ == "__main__":
    build_poster()
    print(f"Wrote {OUT_FILE}")
    print(f"Wrote {DOWNLOADS_FILE}")
