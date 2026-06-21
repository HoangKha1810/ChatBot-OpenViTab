from __future__ import annotations

from pathlib import Path
from html import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Flowable,
    ListFlowable,
    ListItem,
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "OpenViTabQA_Demo_Launch_Guide.pdf"
FONT_REGULAR = "GuideArial"
FONT_BOLD = "GuideArial-Bold"
FONT_MONO = "Courier"


def register_fonts() -> None:
    candidates = [
        (
            "/System/Library/Fonts/Supplemental/Arial.ttf",
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        ),
        (
            "/Library/Fonts/Arial Unicode.ttf",
            "/Library/Fonts/Arial Unicode.ttf",
        ),
    ]
    for regular, bold in candidates:
        if Path(regular).exists() and Path(bold).exists():
            pdfmetrics.registerFont(TTFont(FONT_REGULAR, regular))
            pdfmetrics.registerFont(TTFont(FONT_BOLD, bold))
            return


class Rule(Flowable):
    def __init__(self, width: float, color: colors.Color = colors.HexColor("#CBD5E1")) -> None:
        super().__init__()
        self.width = width
        self.color = color
        self.height = 1

    def draw(self) -> None:
        self.canv.setStrokeColor(self.color)
        self.canv.setLineWidth(0.75)
        self.canv.line(0, 0, self.width, 0)


def p(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(text, style)


def code(text: str, style: ParagraphStyle) -> Table:
    body = "<br/>".join(escape(line) or "&nbsp;" for line in text.rstrip().splitlines())
    table = Table([[Paragraph(body, style)]], colWidths=[6.3 * inch], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#0F172A")),
                ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#1E293B")),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    return table


def bullets(items: list[str], style: ParagraphStyle) -> ListFlowable:
    return ListFlowable(
        [ListItem(Paragraph(item, style), leftIndent=8) for item in items],
        bulletType="bullet",
        start="circle",
        leftIndent=16,
        bulletFontName=FONT_REGULAR,
        bulletFontSize=8,
    )


def numbered(items: list[str], style: ParagraphStyle) -> ListFlowable:
    return ListFlowable(
        [ListItem(Paragraph(item, style), leftIndent=10) for item in items],
        bulletType="1",
        leftIndent=18,
        bulletFontName=FONT_BOLD,
        bulletFontSize=9,
    )


def kv_table(rows: list[tuple[str, str]]) -> Table:
    data = [[Paragraph(f"<b>{left}</b>", STYLES["Cell"]), Paragraph(right, STYLES["Cell"])] for left, right in rows]
    table = Table(data, colWidths=[1.65 * inch, 4.65 * inch], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#E8EEF5")),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#0F172A")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CBD5E1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return table


def step(title: str, body: str, command: str | None = None) -> list:
    flow = [p(f"<b>{title}</b>", STYLES["Body"]), p(body, STYLES["Body"])]
    if command:
        flow.extend([Spacer(1, 3), code(command, STYLES["Code"])])
    flow.append(Spacer(1, 7))
    return flow


def header_footer(canvas, doc) -> None:
    canvas.saveState()
    width, height = LETTER
    canvas.setFont(FONT_REGULAR, 8)
    canvas.setFillColor(colors.HexColor("#64748B"))
    canvas.drawString(inch, 0.55 * inch, "Vietnamese TableQA Demo Launch Guide")
    canvas.drawRightString(width - inch, 0.55 * inch, f"Page {doc.page}")
    canvas.restoreState()


def build() -> None:
    register_fonts()
    doc = SimpleDocTemplate(
        str(OUT),
        pagesize=LETTER,
        rightMargin=1 * inch,
        leftMargin=1 * inch,
        topMargin=0.8 * inch,
        bottomMargin=0.85 * inch,
        title="Vietnamese TableQA Demo Launch Guide",
        author="OpenViTabQA Demo Project",
    )

    content = []
    content.append(p("Vietnamese TableQA Demo Launch Guide", STYLES["Title"]))
    content.append(p("How to launch the OpenViTabQA demo application on Ubuntu/Vast.ai with real data and real local models.", STYLES["Subtitle"]))
    content.append(Spacer(1, 8))
    content.append(Rule(6.5 * inch))
    content.append(Spacer(1, 12))
    content.append(
        p(
            "This guide launches the browser demo for the Vietnamese SQL-grounded TableQA project. "
            "The application does not train models and does not use mock data. It runs on real Open-ViTabQA tables, "
            "executes SQL over SQLite evidence rows, and uses local Ollama models for schema linking, text-to-SQL, answer synthesis, and verification.",
            STYLES["Body"],
        )
    )
    content.append(kv_table(
        [
            ("Repository", "https://github.com/HoangKha1810/ChatBot-OpenViTab"),
            ("Target machine", "Ubuntu 22.04/24.04, NVIDIA RTX A5000 24GB or similar, 16GB+ RAM, 50GB+ disk."),
            ("Default models", "bge-m3, qwen2.5-coder:14b, qwen2.5:7b."),
            ("Demo URL", "http://127.0.0.1:8000 inside the Ubuntu GUI, or the public mapped/tunnel URL from the host."),
        ]
    ))

    content.append(p("1. Prerequisites", STYLES["H1"]))
    content.append(bullets(
        [
            "A fresh Ubuntu GPU instance or Vast.ai desktop instance.",
            "Terminal access inside the Ubuntu GUI or SSH shell.",
            "NVIDIA GPU visible through <b>nvidia-smi</b>.",
            "Internet access for GitHub, Python packages, Ollama, and model downloads.",
            "At least 15-17GB available for model files, plus project/data space.",
        ],
        STYLES["Body"],
    ))
    content.append(code("nvidia-smi", STYLES["Code"]))
    content.append(p("The command should show the GPU name, memory, driver, and CUDA version. For the current demo target, RTX A5000 24GB is sufficient.", STYLES["Body"]))

    content.append(p("2. Install System Packages", STYLES["H1"]))
    content.extend(step(
        "Install Git, Python, venv, pip, curl, and build tools.",
        "Run this once on a clean Ubuntu machine:",
        "sudo apt update\nsudo apt install -y git curl python3 python3-venv python3-pip \\\n  build-essential wget openssh-client",
    ))

    content.append(p("3. Clone The Project", STYLES["H1"]))
    content.extend(step(
        "Clone the GitHub repository and enter the project folder.",
        "Use the main branch that contains the latest GPU demo launcher and progress UI.",
        "cd ~\ngit clone https://github.com/HoangKha1810/ChatBot-OpenViTab.git\ncd ChatBot-OpenViTab",
    ))

    content.append(p("4. Create The Python Environment", STYLES["H1"]))
    content.extend(step(
        "Create and activate a virtual environment.",
        "Install the FastAPI backend dependencies from requirements.txt.",
        "python3 -m venv .venv\nsource .venv/bin/activate\npython -m pip install --upgrade pip\npip install -r requirements.txt",
    ))

    content.append(p("5. Install Ollama", STYLES["H1"]))
    content.extend(step(
        "Install Ollama on Linux.",
        "The installer may warn that systemd is not running inside a container. That is fine on Vast.ai; the project launcher can start Ollama manually.",
        "curl -fsSL https://ollama.com/install.sh | sh",
    ))
    content.append(p("<b>Do not rely on systemctl inside a Docker/Vast desktop container.</b> If systemctl reports that systemd is not PID 1, continue with the project launcher below.", STYLES["Note"]))

    content.append(PageBreak())
    content.append(p("6. Launch With GPU Checks", STYLES["H1"]))
    content.extend(step(
        "Run the all-in-one GPU demo launcher.",
        "This script checks NVIDIA GPU access, starts Ollama if needed, downloads missing models, warms up embedding/chat calls, verifies Ollama is using GPU, and then starts Uvicorn.",
        "cd ~/ChatBot-OpenViTab\nsource .venv/bin/activate\npython3 scripts/run_gpu_demo.py",
    ))
    content.append(p("Expected startup output includes these signals:", STYLES["Body"]))
    content.append(code(
        "[TableQA] Checking NVIDIA GPU with nvidia-smi...\n"
        "[TableQA] GPU OK: NVIDIA RTX A5000, ...\n"
        "[TableQA] Checking Ollama server at http://127.0.0.1:11434...\n"
        "[TableQA] Checking required models...\n"
        "[TableQA] Warming up embedding model bge-m3...\n"
        "[TableQA] Warming up chat model qwen2.5-coder:14b...\n"
        "[TableQA] Warming up chat model qwen2.5:7b...\n"
        "[TableQA] Current Ollama loaded models:\n"
        "NAME                  PROCESSOR\n"
        "qwen2.5:7b            100% GPU\n"
        "[TableQA] Starting FastAPI on http://0.0.0.0:8000",
        STYLES["Code"],
    ))

    content.append(p("7. Open The Demo Application", STYLES["H1"]))
    content.append(numbered(
        [
            "Inside the Ubuntu desktop browser, open <b>http://127.0.0.1:8000</b>.",
            "If opening from your own laptop, use the public mapped port from Vast.ai or a tunnel URL.",
            "Confirm the status pill shows the table count and <b>models ok</b>.",
            "Select a QA example from the left sidebar and press <b>Chạy pipeline</b>.",
            "Watch the answer panel, Progress tab, Models tab, SQL tab, Evidence tab, and Verifier tab.",
        ],
        STYLES["Body"],
    ))

    content.append(p("8. Vast.ai Port Access Options", STYLES["H1"]))
    content.append(p("If the Ubuntu browser can open the app but your laptop cannot, the issue is usually port mapping, not the application.", STYLES["Body"]))
    content.append(kv_table(
        [
            ("Inside GUI", "Use http://127.0.0.1:8000. This is the simplest option for recording a video inside the remote desktop."),
            ("Mapped port", "Check Vast.ai instance ports. Internal port 8000 may be exposed as a random external port, not necessarily :8000."),
            ("New instance option", "Use Docker options such as -p 8000:8000 -e OPEN_BUTTON_PORT=8000 when creating a new instance."),
            ("Tunnel fallback", "Use SSH reverse tunnel or another tunnel tool if ports are not exposed."),
        ]
    ))

    content.append(p("9. Recommended Demo Flow", STYLES["H1"]))
    content.append(numbered(
        [
            "Show the browser at the demo app home page.",
            "Show that the status pill reports real tables and models ok.",
            "Pick QA ID <b>56_3_238</b>: \"Tòa nhà có chiều cao cao nhất có bao nhiêu tầng?\"",
            "Click <b>Chạy pipeline</b> and keep the Progress tab visible.",
            "Point out each stage: load_table, models, schema_linking, text_to_sql, execute_sql, answer, verifier, confidence.",
            "Show SQL and evidence rows to prove the answer is grounded in the real table.",
            "Show the final answer and compare with the expected answer.",
        ],
        STYLES["Body"],
    ))

    content.append(PageBreak())
    content.append(p("10. Useful Commands", STYLES["H1"]))
    content.append(code(
        "# Pull latest code\n"
        "cd ~/ChatBot-OpenViTab\n"
        "git pull\n\n"
        "# Activate Python environment\n"
        "source .venv/bin/activate\n\n"
        "# Check models\n"
        "ollama list\n\n"
        "# Check loaded model placement\n"
        "ollama ps\n\n"
        "# Run deterministic smoke test without model calls\n"
        "TABLEQA_USE_MODELS=0 TABLEQA_REQUIRE_MODELS=0 \\\n  python3 scripts/check_demo_cases.py\n\n"
        "# Start the full GPU demo\n"
        "python3 scripts/run_gpu_demo.py",
        STYLES["Code"],
    ))

    content.append(p("11. Troubleshooting", STYLES["H1"]))
    content.append(kv_table(
        [
            ("systemctl error", "Containers often do not run systemd. Ignore systemctl and run python3 scripts/run_gpu_demo.py; it starts Ollama manually if needed."),
            ("No module named app", "Run git pull. The script now fixes its import path. You can also run commands from ~/ChatBot-OpenViTab."),
            ("Port not reachable", "Open http://127.0.0.1:8000 inside the remote Ubuntu browser, or expose/map port 8000 in Vast.ai."),
            ("UI says blank error", "Run git pull and hard reload the browser with Ctrl+Shift+R. The UI can recover results by request_id after transient network drops."),
            ("Models missing", "Run python3 scripts/run_gpu_demo.py or python3 scripts/setup_ollama_models.py while Ollama is running."),
            ("GPU not used", "Check nvidia-smi and ollama ps. The launcher fails if TABLEQA_REQUIRE_GPU=1 and Ollama does not report GPU."),
            ("Slow first request", "First load warms models and may be slower. Subsequent requests should be faster because keep_alive is enabled."),
        ]
    ))

    content.append(p("12. What Success Looks Like", STYLES["H1"]))
    content.append(bullets(
        [
            "Terminal shows <b>[TableQA] Starting FastAPI on http://0.0.0.0:8000</b>.",
            "Browser loads the Vietnamese TableQA interface.",
            "Status pill shows real dataset count and <b>models ok</b>.",
            "Clicking <b>Chạy pipeline</b> produces a final answer, confidence, SQL trace, evidence rows, and model traces.",
            "Terminal logs finish with <b>confidence Cao</b> or another confidence label and <b>done Answer ready.</b>",
        ],
        STYLES["Body"],
    ))

    doc.build(content, onFirstPage=header_footer, onLaterPages=header_footer)


BASE = getSampleStyleSheet()
STYLES = {
    "Title": ParagraphStyle(
        "GuideTitle",
        parent=BASE["Title"],
        fontName=FONT_BOLD,
        fontSize=24,
        leading=28,
        textColor=colors.HexColor("#0F172A"),
        spaceAfter=4,
        alignment=TA_LEFT,
    ),
    "Subtitle": ParagraphStyle(
        "GuideSubtitle",
        parent=BASE["BodyText"],
        fontName=FONT_REGULAR,
        fontSize=10.5,
        leading=14,
        textColor=colors.HexColor("#475569"),
        spaceAfter=8,
    ),
    "H1": ParagraphStyle(
        "GuideH1",
        parent=BASE["Heading1"],
        fontName=FONT_BOLD,
        fontSize=16,
        leading=20,
        textColor=colors.HexColor("#2E74B5"),
        spaceBefore=14,
        spaceAfter=8,
    ),
    "Body": ParagraphStyle(
        "GuideBody",
        parent=BASE["BodyText"],
        fontName=FONT_REGULAR,
        fontSize=10.2,
        leading=13.2,
        textColor=colors.HexColor("#0F172A"),
        spaceAfter=6,
    ),
    "Cell": ParagraphStyle(
        "GuideCell",
        parent=BASE["BodyText"],
        fontName=FONT_REGULAR,
        fontSize=8.8,
        leading=11.5,
        textColor=colors.HexColor("#0F172A"),
    ),
    "Code": ParagraphStyle(
        "GuideCode",
        parent=BASE["Code"],
        fontName=FONT_MONO,
        fontSize=7.5,
        leading=9.4,
        textColor=colors.white,
        leftIndent=0,
        rightIndent=0,
        spaceBefore=3,
        spaceAfter=9,
        wordWrap="CJK",
    ),
    "Note": ParagraphStyle(
        "GuideNote",
        parent=BASE["BodyText"],
        fontName=FONT_BOLD,
        fontSize=9.5,
        leading=12.5,
        textColor=colors.HexColor("#7A5A00"),
        backColor=colors.HexColor("#FFF7D6"),
        borderPadding=7,
        borderColor=colors.HexColor("#EAB308"),
        borderWidth=0.5,
        spaceBefore=3,
        spaceAfter=9,
    ),
}


if __name__ == "__main__":
    build()
    print(OUT)
