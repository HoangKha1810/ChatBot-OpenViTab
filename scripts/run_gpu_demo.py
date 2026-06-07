from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import requests

from app.config import ANSWER_MODEL, SCHEMA_EMBED_MODEL, TEXT_TO_SQL_MODEL, VERIFIER_MODEL


ROOT = Path(__file__).resolve().parents[1]
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
MODELS = list(dict.fromkeys([SCHEMA_EMBED_MODEL, TEXT_TO_SQL_MODEL, ANSWER_MODEL, VERIFIER_MODEL]))


def main() -> int:
    print("[TableQA] GPU demo launcher")
    ensure_command("git")
    ensure_command("python3")
    ensure_command("ollama")
    check_gpu()
    ensure_ollama_server()
    ensure_models()
    warmup_ollama()
    print_ollama_ps()
    print("[TableQA] Starting FastAPI on http://0.0.0.0:8000")
    env = os.environ.copy()
    env["TABLEQA_REQUIRE_GPU"] = "1"
    env["TABLEQA_STARTUP_CHECKS"] = "1"
    env.setdefault("OLLAMA_NUM_PARALLEL", "1")
    env.setdefault("OLLAMA_KEEP_ALIVE", "10m")
    env.setdefault("OLLAMA_KV_CACHE_TYPE", "q8_0")
    return subprocess.call(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "0.0.0.0",
            "--port",
            "8000",
            "--log-level",
            "info",
        ],
        cwd=ROOT,
        env=env,
    )


def ensure_command(command: str) -> None:
    if shutil.which(command) is None:
        raise SystemExit(f"[TableQA] Missing command: {command}")


def check_gpu() -> None:
    print("[TableQA] Checking NVIDIA GPU with nvidia-smi...")
    ensure_command("nvidia-smi")
    output = subprocess.check_output(
        [
            "nvidia-smi",
            "--query-gpu=name,memory.total,driver_version",
            "--format=csv,noheader",
        ],
        text=True,
    ).strip()
    if not output:
        raise SystemExit("[TableQA] nvidia-smi did not return any GPU.")
    print(f"[TableQA] GPU OK: {output.splitlines()[0]}")


def ensure_ollama_server() -> None:
    print(f"[TableQA] Checking Ollama server at {OLLAMA_BASE_URL}...")
    if ollama_ready():
        print("[TableQA] Ollama server is already running.")
        return
    print("[TableQA] Starting `ollama serve` in background...")
    log_path = ROOT / "data" / "processed" / "ollama.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.setdefault("OLLAMA_NUM_PARALLEL", "1")
    env.setdefault("OLLAMA_KEEP_ALIVE", "10m")
    env.setdefault("OLLAMA_KV_CACHE_TYPE", "q8_0")
    with log_path.open("ab") as log_file:
        subprocess.Popen(["ollama", "serve"], stdout=log_file, stderr=subprocess.STDOUT, cwd=ROOT, env=env)
    for _ in range(30):
        if ollama_ready():
            print(f"[TableQA] Ollama server ready. Log: {log_path}")
            return
        time.sleep(1)
    raise SystemExit(f"[TableQA] Ollama did not become ready. Check {log_path}")


def ollama_ready() -> bool:
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=3)
        return response.ok
    except requests.RequestException:
        return False


def ensure_models() -> None:
    print("[TableQA] Checking required models...")
    available = set(list_models())
    missing = []
    for model in MODELS:
        aliases = {model, f"{model}:latest"} if ":" not in model else {model}
        if not (available & aliases):
            missing.append(model)
    if not missing:
        print("[TableQA] Models already available.")
        return
    for model in missing:
        print(f"[TableQA] Pulling model: {model}")
        subprocess.check_call(["ollama", "pull", model], cwd=ROOT)
    print("[TableQA] Model download complete.")


def list_models() -> list[str]:
    response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=10)
    response.raise_for_status()
    return sorted(item.get("name", "") for item in response.json().get("models", []) if item.get("name"))


def warmup_ollama() -> None:
    print(f"[TableQA] Warming up embedding model {SCHEMA_EMBED_MODEL}...")
    response = requests.post(
        f"{OLLAMA_BASE_URL}/api/embed",
        json={"model": SCHEMA_EMBED_MODEL, "input": ["kiểm tra GPU cho Vietnamese TableQA"], "keep_alive": "10m"},
        timeout=240,
    )
    response.raise_for_status()
    print("[TableQA] Embedding warm-up OK.")

    for model in dict.fromkeys([TEXT_TO_SQL_MODEL, ANSWER_MODEL, VERIFIER_MODEL]):
        print(f"[TableQA] Warming up chat model {model}...")
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/chat",
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": "Return JSON only."},
                    {"role": "user", "content": '{"ok": true}'},
                ],
                "stream": False,
                "format": "json",
                "keep_alive": "10m",
                "options": {"temperature": 0, "seed": 42, "num_predict": 64},
            },
            timeout=240,
        )
        response.raise_for_status()
        print(f"[TableQA] Chat warm-up OK: {model}.")


def print_ollama_ps() -> None:
    print("[TableQA] Current Ollama loaded models:")
    try:
        output = subprocess.check_output(["ollama", "ps"], cwd=ROOT, text=True)
        print(output.rstrip())
        if "gpu" not in output.lower():
            raise SystemExit("[TableQA] Ollama did not report GPU in `ollama ps`. Check NVIDIA runtime/CUDA.")
    except Exception as exc:
        raise SystemExit(f"[TableQA] Could not verify `ollama ps`: {exc}") from exc


if __name__ == "__main__":
    raise SystemExit(main())
