# Vietnamese SQL-Grounded TableQA Demo

This project implements the demo artefact described in `Vietnamese_TableQA_Final_Report.docx`: a SQL-grounded Vietnamese TableQA pipeline over real Open-ViTabQA data. It does not train models and does not use mock data. By default it requires real lightweight local models through Ollama.

## What Is Included

- Real Open-ViTabQA downloader from `DuzDao/Open-ViTabQA`
- Table normalisation with merged-header handling
- SQLite table generation per `table_id`
- Vietnamese schema linker with `bge-m3` embeddings
- Text-to-SQL agent with `qwen2.5-coder:1.5b`
- Answer synthesis and verifier agents with `qwen2.5:1.5b`
- SQL execution with evidence rows, verifier, and confidence score
- FastAPI backend plus a browser demo UI
- Sample evaluation and demo regression tests

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/download_open_vitabqa.py
python scripts/setup_ollama_models.py
python scripts/run_demo.py
```

Open:

```text
http://127.0.0.1:8000
```

## Run Tests

```bash
TABLEQA_REQUIRE_MODELS=0 TABLEQA_USE_MODELS=0 python -m pytest tests
```

You can also run the dependency-light demo check:

```bash
TABLEQA_REQUIRE_MODELS=0 TABLEQA_USE_MODELS=0 python scripts/check_demo_cases.py
```

If `pytest` is not installed outside the provided requirements:

```bash
pip install pytest
python -m pytest tests
```

## Run A Quick Evaluation

```bash
python scripts/evaluate_sample.py --split dev --limit 50
```

The output JSON is written to `data/processed/sample_eval.json`.

## API

Health:

```bash
curl http://127.0.0.1:8000/api/health
```

Ask using a known real QA:

```bash
curl -X POST "http://127.0.0.1:8000/api/ask/56_3_238?split=dev"
```

Ask a custom question against a real table:

```bash
curl -X POST http://127.0.0.1:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{"table_id":"56_3","question":"Tòa nhà có chiều cao cao nhất có bao nhiêu tầng?"}'
```

## Model Setup

Default task models:

| Task | Model | Why |
| --- | --- | --- |
| Schema linking | `bge-m3` | Multilingual embedding model, good for Vietnamese headers and aliases. |
| Text-to-SQL | `qwen2.5-coder:1.5b` | Small, stable code/SQL model. |
| Answer synthesis | `qwen2.5:1.5b` | Small multilingual instruction model. |
| Evidence verifier | `qwen2.5:1.5b` | Same small multilingual model, guarded by deterministic verifier. |

Install on macOS:

```bash
brew install ollama
ollama serve
python scripts/setup_ollama_models.py
```

The app defaults to requiring real models. If Ollama or a model is missing, API calls return `503` with the missing model list instead of producing mock output.

For deterministic regression tests only:

```bash
TABLEQA_USE_MODELS=0 TABLEQA_REQUIRE_MODELS=0 python scripts/check_demo_cases.py
```

## Notes

The included code performs real table-to-SQL execution and evidence verification. Model outputs are guarded: unsafe SQL is rejected, model answers must pass evidence verification, and unsupported answers fall back to extractive evidence-safe values rather than invented text.

See machine rental guidance in `docs/MACHINE_SPECS.md` and a recording flow in `docs/VIDEO_DEMO_SCRIPT.md`.
