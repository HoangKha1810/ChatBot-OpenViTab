from __future__ import annotations

import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
STATIC_DIR = BASE_DIR / "app" / "static"

OPEN_VITABQA_BASE_URL = "https://raw.githubusercontent.com/DuzDao/Open-ViTabQA/main"
DATA_FILES = ("table.json", "qas_train.json", "qas_dev.json", "qas_test.json")

DEFAULT_SPLIT = "dev"
MAX_TABLE_PREVIEW_ROWS = 80

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
TABLEQA_USE_MODELS = os.getenv("TABLEQA_USE_MODELS", "1").strip().lower() not in {"0", "false", "no", "off"}
TABLEQA_REQUIRE_MODELS = os.getenv("TABLEQA_REQUIRE_MODELS", "1").strip().lower() not in {"0", "false", "no", "off"}
TABLEQA_REQUIRE_GPU = os.getenv("TABLEQA_REQUIRE_GPU", "0").strip().lower() in {"1", "true", "yes", "on"}
TABLEQA_STARTUP_CHECKS = os.getenv("TABLEQA_STARTUP_CHECKS", "0").strip().lower() in {"1", "true", "yes", "on"}

SCHEMA_EMBED_MODEL = os.getenv("TABLEQA_SCHEMA_EMBED_MODEL", "bge-m3")
TEXT_TO_SQL_MODEL = os.getenv("TABLEQA_TEXT_TO_SQL_MODEL", "qwen2.5-coder:1.5b")
ANSWER_MODEL = os.getenv("TABLEQA_ANSWER_MODEL", "qwen2.5:1.5b")
VERIFIER_MODEL = os.getenv("TABLEQA_VERIFIER_MODEL", "qwen2.5:1.5b")
OLLAMA_TIMEOUT_SECONDS = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "60"))
