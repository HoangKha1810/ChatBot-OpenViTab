from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODELS = ["bge-m3", "qwen2.5-coder:1.5b", "qwen2.5:1.5b"]


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
