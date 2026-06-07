from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from app.config import ANSWER_MODEL, SCHEMA_EMBED_MODEL, TEXT_TO_SQL_MODEL, VERIFIER_MODEL

ROOT = Path(__file__).resolve().parents[1]
MODELS = list(dict.fromkeys([SCHEMA_EMBED_MODEL, TEXT_TO_SQL_MODEL, ANSWER_MODEL, VERIFIER_MODEL]))


def main() -> int:
    if shutil.which("ollama") is None:
        print("Ollama is not installed.")
        print("macOS: brew install ollama")
        print("Linux: curl -fsSL https://ollama.com/install.sh | sh")
        return 1

    try:
        subprocess.check_call(["ollama", "list"], cwd=ROOT)
    except subprocess.CalledProcessError:
        print("Start Ollama first: `ollama serve`")
        return 1

    for model in MODELS:
        print(f"Pulling {model}...")
        subprocess.check_call(["ollama", "pull", model], cwd=ROOT)

    print("Models ready.")
    subprocess.check_call(["ollama", "list"], cwd=ROOT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
