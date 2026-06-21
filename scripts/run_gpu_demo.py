from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import requests


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import ANSWER_MODEL, SCHEMA_EMBED_FALLBACK_MODEL, SCHEMA_EMBED_MODEL, TEXT_TO_SQL_MODEL, VERIFIER_MODEL

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
MODELS = list(dict.fromkeys([SCHEMA_EMBED_MODEL, SCHEMA_EMBED_FALLBACK_MODEL, TEXT_TO_SQL_MODEL, ANSWER_MODEL, VERIFIER_MODEL]))

RTX_3090_DEFAULT_ENV = {
    "TABLEQA_REQUIRE_GPU": "1",
    "TABLEQA_REQUIRE_MODELS": "1",
    "TABLEQA_USE_MODELS": "1",
    "TABLEQA_STARTUP_CHECKS": "1",
    "TABLEQA_SCHEMA_EMBED_MODEL": "nomic-embed-text",
    "TABLEQA_SCHEMA_EMBED_FALLBACK_MODEL": "nomic-embed-text",
    "TABLEQA_NUM_CTX": "4096",
    "TABLEQA_NUM_PREDICT": "384",
    "TABLEQA_TOP_P": "0.75",
    "TABLEQA_TEMPERATURE": "0",
    "TABLEQA_OLLAMA_KEEP_ALIVE": "3m",
    "OLLAMA_TIMEOUT_SECONDS": "300",
    "OLLAMA_NUM_PARALLEL": "1",
    "OLLAMA_MAX_LOADED_MODELS": "1",
    "OLLAMA_KEEP_ALIVE": "3m",
    "OLLAMA_KV_CACHE_TYPE": "q8_0",
    "OLLAMA_FLASH_ATTENTION": "1",
}


def main() -> int:
    print("[TableQA] GPU demo launcher")
    apply_rtx_3090_defaults()
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


def apply_rtx_3090_defaults() -> None:
    print("[TableQA] Applying RTX 3090 24GB stable inference defaults:")
    for key, value in RTX_3090_DEFAULT_ENV.items():
        os.environ.setdefault(key, value)
        print(f"[TableQA]   {key}={os.environ[key]}")
    print("[TableQA] Override any value by exporting it before running this script.")


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
    active_embed_model = warmup_embedding_model()
    os.environ["TABLEQA_SCHEMA_EMBED_MODEL"] = active_embed_model

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
                "keep_alive": os.environ["TABLEQA_OLLAMA_KEEP_ALIVE"],
                "options": {
                    "temperature": float(os.environ["TABLEQA_TEMPERATURE"]),
                    "top_p": float(os.environ["TABLEQA_TOP_P"]),
                    "num_ctx": int(os.environ["TABLEQA_NUM_CTX"]),
                    "num_predict": 64,
                    "seed": 42,
                },
            },
            timeout=240,
        )
        response.raise_for_status()
        print(f"[TableQA] Chat warm-up OK: {model}.")


def warmup_embedding_model() -> str:
    candidates = list(dict.fromkeys([os.environ["TABLEQA_SCHEMA_EMBED_MODEL"], os.environ["TABLEQA_SCHEMA_EMBED_FALLBACK_MODEL"]]))
    last_error = None
    for model in candidates:
        print(f"[TableQA] Warming up embedding model {model}...")
        try:
            response = requests.post(
                f"{OLLAMA_BASE_URL}/api/embed",
                json={
                    "model": model,
                    "input": ["kiểm tra GPU cho Vietnamese TableQA"],
                    "keep_alive": os.environ["TABLEQA_OLLAMA_KEEP_ALIVE"],
                },
                timeout=240,
            )
            response.raise_for_status()
            print(f"[TableQA] Embedding warm-up OK: {model}.")
            return model
        except Exception as exc:
            last_error = exc
            print(f"[TableQA] WARNING: embedding warm-up failed for {model}: {exc}")
    print(f"[TableQA] WARNING: all embedding warm-ups failed; startup will continue and retry during requests. Last error: {last_error}")
    os.environ["TABLEQA_STARTUP_CHECKS"] = "0"
    return candidates[-1]


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
