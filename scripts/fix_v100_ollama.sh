#!/usr/bin/env bash
set -euo pipefail

OLLAMA_VERSION="${OLLAMA_VERSION:-0.24.0}"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT_DIR/data/processed"
LOG_FILE="$LOG_DIR/ollama.log"

mkdir -p "$LOG_DIR"

echo "[TableQA] Fixing Ollama for Tesla V100 / Volta GPUs"
echo "[TableQA] Target Ollama version: $OLLAMA_VERSION"

pkill -x ollama 2>/dev/null || true
pkill -f ollama_llama_server 2>/dev/null || true
sleep 2

echo "[TableQA] Installing Ollama $OLLAMA_VERSION..."
curl -fsSL https://ollama.com/install.sh | OLLAMA_VERSION="$OLLAMA_VERSION" sh

echo "[TableQA] Starting Ollama with V100-safe environment..."
OLLAMA_HOST=127.0.0.1:11434 \
OLLAMA_NUM_PARALLEL=1 \
OLLAMA_MAX_LOADED_MODELS=1 \
OLLAMA_KV_CACHE_TYPE=f16 \
OLLAMA_FLASH_ATTENTION=0 \
nohup ollama serve > "$LOG_FILE" 2>&1 &

sleep 5
ollama --version || true
curl -fsS http://127.0.0.1:11434/api/tags >/dev/null

echo "[TableQA] Ollama is ready. Log: $LOG_FILE"
echo "[TableQA] Now run: TABLEQA_GPU_PROFILE=v100 python3 scripts/run_gpu_demo.py"
