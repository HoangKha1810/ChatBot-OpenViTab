# Machine Specs To Rent

This demo runs without training and without mock data. The default app uses real lightweight local models through Ollama plus real SQL execution over Open-ViTabQA tables.

## For Video Demo, No Training

Recommended rental:

- CPU: 4 vCPU or better
- RAM: 16 GB comfortable, 8 GB minimum
- Disk: 30 GB SSD
- GPU: not required
- OS: Ubuntu 22.04 LTS
- Python: 3.11

Good low-cost choices:

- Hetzner CX32 or equivalent: 4 vCPU, 8 GB RAM
- DigitalOcean Basic: 4 vCPU, 8 GB RAM
- AWS EC2 `t3.xlarge` or `t3a.xlarge`

Expected behavior:

- First run downloads about 13 MB of real Open-ViTabQA JSON plus about 2-3 GB of Ollama models.
- SQLite cache is generated on demand in `data/processed/sqlite`.
- Typical single-query latency depends on CPU. On Apple Silicon or a good 4-8 vCPU VPS, expect several seconds for the full model pipeline.

## For LLM Inference Add-On

If you want faster local inference or larger models:

- GPU: NVIDIA L4 24 GB, RTX 4090 24 GB, A10G 24 GB, or A100 40 GB
- CPU: 8 vCPU
- RAM: 32 GB
- Disk: 80 GB SSD
- CUDA image: Ubuntu 22.04 + CUDA 12.x

Default lightweight models:

- Schema linking: `bge-m3`
- Text-to-SQL: `qwen2.5-coder:1.5b`
- Answer synthesis/verifier: `qwen2.5:1.5b`

Optional larger model swaps:

- Text-to-SQL: `qwen2.5-coder:3b` or `qwen2.5-coder:7b`
- Answer synthesis: `qwen2.5:3b`, `qwen2.5:7b`, or Llama 3.1/3.2 8B Instruct

Practical rental choices:

- RunPod Secure Cloud: RTX 4090 24 GB, 8 vCPU, 32 GB RAM
- Lambda Cloud: NVIDIA L4 or A10
- AWS EC2 `g6.xlarge` for L4 24 GB
- AWS EC2 `g5.xlarge` for A10G 24 GB

## For Training Or Fine-Tuning

The user request says no training is needed. If you later fine-tune LoRA/QLoRA baselines:

- Minimum: 1x A100 40 GB, 8 vCPU, 64 GB RAM, 200 GB SSD
- Better: 1x A100 80 GB or 2x A100 40 GB
- For QLoRA 8B: 24 GB can work for small batch sizes, but A100 40 GB is less painful.

Budget note: rent the CPU box for the demo. Rent the GPU box only for recording an LLM-enhanced version or running fine-tuning experiments.
