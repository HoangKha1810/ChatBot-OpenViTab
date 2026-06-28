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
OLLAMA_LOG_PATH = ROOT / "data" / "processed" / "ollama.log"

BASE_DEFAULT_ENV = {
    "TABLEQA_REQUIRE_GPU": "1",
    "TABLEQA_REQUIRE_MODELS": "1",
    "TABLEQA_USE_MODELS": "1",
    "TABLEQA_STARTUP_CHECKS": "1",
    "TABLEQA_STRICT_WARMUP": "0",
    "TABLEQA_SCHEMA_EMBED_MODEL": "nomic-embed-text",
    "TABLEQA_SCHEMA_EMBED_FALLBACK_MODEL": "nomic-embed-text",
    "TABLEQA_TOP_P": "0.75",
    "TABLEQA_TEMPERATURE": "0",
    "TABLEQA_OLLAMA_KEEP_ALIVE": "3m",
    "OLLAMA_TIMEOUT_SECONDS": "300",
    "OLLAMA_NUM_PARALLEL": "1",
    "OLLAMA_MAX_LOADED_MODELS": "1",
    "OLLAMA_KEEP_ALIVE": "3m",
}

RTX_3090_ENV = {
    "TABLEQA_NUM_CTX": "6144",
    "TABLEQA_NUM_PREDICT": "512",
    "OLLAMA_KV_CACHE_TYPE": "q8_0",
    "OLLAMA_FLASH_ATTENTION": "1",
}

V100_ENV = {
    "TABLEQA_NUM_CTX": "4096",
    "TABLEQA_NUM_PREDICT": "384",
    "OLLAMA_KV_CACHE_TYPE": "f16",
    "OLLAMA_FLASH_ATTENTION": "0",
}


def main() -> int:
    print("[TableQA] GPU demo launcher")
    apply_base_defaults()
    ensure_command("git")
    ensure_command("python3")
    ensure_command("ollama")
    gpu_info = check_gpu()
    gpu_profile = apply_gpu_profile(gpu_info)
    ensure_ollama_server(force_restart=gpu_profile == "v100")
    check_ollama_version(gpu_profile)
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


def apply_base_defaults() -> None:
    print("[TableQA] Applying base demo defaults:")
    for key, value in BASE_DEFAULT_ENV.items():
        os.environ.setdefault(key, value)
        print(f"[TableQA]   {key}={os.environ[key]}")
    print("[TableQA] Override any value by exporting it before running this script.")


def apply_gpu_profile(gpu_info: dict[str, str]) -> str:
    requested = os.getenv("TABLEQA_GPU_PROFILE", "auto").strip().lower()
    name = gpu_info["name"].lower()
    if requested == "auto":
        profile = "v100" if "v100" in name else "rtx3090"
    else:
        profile = requested

    if profile == "v100":
        print("[TableQA] Applying V100/Volta-safe Ollama profile.")
        print("[TableQA]   V100 requires Flash Attention off to avoid CUDA kernel image errors.")
        apply_profile_env(V100_ENV, force=True)
    elif profile in {"rtx3090", "3090", "a5000", "rtx_a5000"}:
        print("[TableQA] Applying RTX 3090/A5000 24GB profile.")
        apply_profile_env(RTX_3090_ENV, force=False)
        profile = "rtx3090"
    else:
        print(f"[TableQA] Unknown TABLEQA_GPU_PROFILE={requested}; using V100-safe profile.")
        apply_profile_env(V100_ENV, force=True)
        profile = "v100"

    os.environ["TABLEQA_GPU_PROFILE"] = profile
    return profile


def apply_profile_env(values: dict[str, str], force: bool) -> None:
    for key, value in values.items():
        if force:
            os.environ[key] = value
        else:
            os.environ.setdefault(key, value)
        print(f"[TableQA]   {key}={os.environ[key]}")


def ensure_command(command: str) -> None:
    if shutil.which(command) is None:
        raise SystemExit(f"[TableQA] Missing command: {command}")


def check_gpu() -> dict[str, str]:
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
    first_gpu = output.splitlines()[0]
    print(f"[TableQA] GPU OK: {first_gpu}")
    parts = [part.strip() for part in first_gpu.split(",")]
    return {
        "name": parts[0] if parts else "",
        "memory_total": parts[1] if len(parts) > 1 else "",
        "driver_version": parts[2] if len(parts) > 2 else "",
    }


def ensure_ollama_server(force_restart: bool = False) -> None:
    print(f"[TableQA] Checking Ollama server at {OLLAMA_BASE_URL}...")
    if force_restart:
        stop_ollama_server()
    if ollama_ready():
        print("[TableQA] Ollama server is already running.")
        return
    print("[TableQA] Starting `ollama serve` in background...")
    OLLAMA_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.setdefault("OLLAMA_HOST", "127.0.0.1:11434")
    with OLLAMA_LOG_PATH.open("ab") as log_file:
        subprocess.Popen(["ollama", "serve"], stdout=log_file, stderr=subprocess.STDOUT, cwd=ROOT, env=env)
    for _ in range(30):
        if ollama_ready():
            print(f"[TableQA] Ollama server ready. Log: {OLLAMA_LOG_PATH}")
            return
        time.sleep(1)
    raise SystemExit(f"[TableQA] Ollama did not become ready. Check {OLLAMA_LOG_PATH}")


def stop_ollama_server() -> None:
    print("[TableQA] Restarting Ollama because inference returned an error...")
    subprocess.run(["pkill", "-x", "ollama"], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    subprocess.run(["pkill", "-f", "ollama_llama_server"], cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    time.sleep(2)


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


def check_ollama_version(gpu_profile: str) -> None:
    try:
        output = subprocess.check_output(["ollama", "--version"], cwd=ROOT, text=True, stderr=subprocess.STDOUT).strip()
    except Exception as exc:
        print(f"[TableQA] WARNING: could not read Ollama version: {exc}")
        return
    print(f"[TableQA] {output}")
    if gpu_profile == "v100":
        print("[TableQA] V100 note: if Ollama still reports `device kernel image is invalid`, install an older Ollama build with V100 CUDA support.")
        print("[TableQA] See README section: V100 / device kernel image is invalid.")


def warmup_ollama() -> None:
    active_embed_model, embed_ok = warmup_embedding_model()
    os.environ["TABLEQA_SCHEMA_EMBED_MODEL"] = active_embed_model

    warmup_failed = not embed_ok
    for model in dict.fromkeys([TEXT_TO_SQL_MODEL, ANSWER_MODEL, VERIFIER_MODEL]):
        if not warmup_chat_model(model):
            warmup_failed = True

    if warmup_failed:
        os.environ["TABLEQA_STARTUP_CHECKS"] = "0"
        print("[TableQA] WARNING: one or more warm-ups failed.")
        print("[TableQA] The web app will still start; model calls will retry when you press `Run pipeline`.")
        print(f"[TableQA] If it still fails, inspect Ollama log: {OLLAMA_LOG_PATH}")


def warmup_chat_model(model: str) -> bool:
    payload = {
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
    }
    for attempt in range(1, 3):
        print(f"[TableQA] Warming up chat model {model} (attempt {attempt}/2)...")
        try:
            response = requests.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload, timeout=240)
            response.raise_for_status()
            print(f"[TableQA] Chat warm-up OK: {model}.")
            return True
        except Exception as exc:
            print(f"[TableQA] WARNING: chat warm-up failed for {model}: {describe_http_error(exc)}")
            print_ollama_log_tail()
            if attempt == 1:
                ensure_ollama_server(force_restart=True)
    print(f"[TableQA] WARNING: continuing without successful chat warm-up for {model}.")
    return False


def warmup_embedding_model() -> tuple[str, bool]:
    candidates = list(dict.fromkeys([os.environ["TABLEQA_SCHEMA_EMBED_MODEL"], os.environ["TABLEQA_SCHEMA_EMBED_FALLBACK_MODEL"]]))
    last_error = None
    for model in candidates:
        print(f"[TableQA] Warming up embedding model {model}...")
        try:
            response = requests.post(
                f"{OLLAMA_BASE_URL}/api/embed",
                json={
                    "model": model,
                    "input": ["GPU check for Vietnamese TableQA"],
                    "keep_alive": os.environ["TABLEQA_OLLAMA_KEEP_ALIVE"],
                },
                timeout=240,
            )
            response.raise_for_status()
            print(f"[TableQA] Embedding warm-up OK: {model}.")
            return model, True
        except Exception as exc:
            last_error = exc
            print(f"[TableQA] WARNING: embedding warm-up failed for {model}: {describe_http_error(exc)}")
            print_ollama_log_tail()
    print(f"[TableQA] WARNING: all embedding warm-ups failed; startup will continue and retry during requests. Last error: {last_error}")
    os.environ["TABLEQA_STARTUP_CHECKS"] = "0"
    return candidates[-1], False


def print_ollama_ps() -> None:
    print("[TableQA] Current Ollama loaded models:")
    try:
        output = subprocess.check_output(["ollama", "ps"], cwd=ROOT, text=True)
        print(output.rstrip())
        if "gpu" not in output.lower():
            print("[TableQA] WARNING: `ollama ps` did not report GPU. If no model is loaded, this is normal after failed warm-up.")
    except Exception as exc:
        print(f"[TableQA] WARNING: Could not verify `ollama ps`: {exc}")


def describe_http_error(exc: Exception) -> str:
    response = getattr(exc, "response", None)
    if response is None:
        return str(exc)
    body = (response.text or "").strip().replace("\n", " ")
    if len(body) > 700:
        body = f"{body[:700]}..."
    return f"{exc}; body={body or '<empty>'}"


def print_ollama_log_tail(lines: int = 25) -> None:
    if not OLLAMA_LOG_PATH.exists():
        return
    print(f"[TableQA] Last {lines} lines from {OLLAMA_LOG_PATH}:")
    try:
        output = subprocess.check_output(["tail", "-n", str(lines), str(OLLAMA_LOG_PATH)], text=True)
    except Exception as exc:
        print(f"[TableQA] Could not read Ollama log: {exc}")
        return
    for line in output.rstrip().splitlines():
        print(f"[ollama.log] {line}")


if __name__ == "__main__":
    raise SystemExit(main())
