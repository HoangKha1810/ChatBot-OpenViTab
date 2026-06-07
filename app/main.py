from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.config import MAX_TABLE_PREVIEW_ROWS, STATIC_DIR, TABLEQA_STARTUP_CHECKS
from app.data_loader import DatasetNotFoundError, dataset_stats, get_table, load_qas
from app.model_runtime import ModelUnavailableError, get_runtime
from app.pipeline import answer_qa, answer_question
from app.progress import fail_progress, finish_progress, get_progress, get_result, start_progress, store_result


@asynccontextmanager
async def lifespan(app: FastAPI):
    if TABLEQA_STARTUP_CHECKS:
        start_progress("startup", "Running startup GPU and model checks.")
        runtime = get_runtime()
        runtime.ensure_gpu("startup")
        runtime.ensure_ready("startup")
        runtime.warmup("startup")
        runtime.ensure_ollama_gpu_loaded("startup")
        finish_progress("startup", "Startup checks passed.")
    yield


app = FastAPI(
    title="Vietnamese SQL-Grounded TableQA Demo",
    description="Open-ViTabQA demo with table-to-SQL execution, evidence verification, and confidence trace.",
    version="1.0.0",
    lifespan=lifespan,
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class AskRequest(BaseModel):
    question: str
    table_id: str
    qa_id: str | None = None
    expected_answer: str | None = None
    request_id: str | None = None


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health() -> dict[str, object]:
    try:
        stats = dataset_stats()
        return {"ok": True, "dataset": stats, "models": get_runtime().status()}
    except DatasetNotFoundError as exc:
        return {"ok": False, "error": str(exc)}


@app.get("/api/models")
def models() -> dict[str, object]:
    return get_runtime().status()


@app.get("/api/progress/{request_id}")
def progress(request_id: str) -> dict[str, object]:
    return get_progress(request_id)


@app.get("/api/result/{request_id}")
def result(request_id: str) -> dict[str, object]:
    cached = get_result(request_id)
    if cached is None:
        raise HTTPException(status_code=404, detail="Result is not ready.")
    return cached


@app.get("/api/examples")
def examples(
    split: str = Query(default="dev", pattern="^(train|dev|test)$"),
    limit: int = Query(default=40, ge=1, le=200),
    domain: str | None = None,
) -> dict[str, object]:
    qas = load_qas(split)  # type: ignore[arg-type]
    items = []
    for qa in qas:
        table = get_table(qa.table_id)
        if domain and table.table_domain != domain:
            continue
        items.append(
            {
                "qa_id": qa.qa_id,
                "table_id": qa.table_id,
                "question": qa.question,
                "expected_answer": qa.answer,
                "hints": qa.hints,
                "table_title": table.table_title,
                "table_domain": table.table_domain,
            }
        )
        if len(items) >= limit:
            break
    return {"items": items}


@app.get("/api/table/{table_id}")
def table_detail(table_id: str) -> dict[str, object]:
    try:
        table = get_table(table_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {
        "table_id": table.table_id,
        "title": table.table_title,
        "domain": table.table_domain,
        "type": table.table_type,
        "headers": table.headers,
        "rows": table.rows[:MAX_TABLE_PREVIEW_ROWS],
        "row_count": len(table.rows),
    }


@app.post("/api/ask")
def ask(payload: AskRequest) -> dict[str, object]:
    request_id = payload.request_id or f"api-{payload.table_id}"
    start_progress(request_id, "Received /api/ask request.")
    try:
        result = answer_question(
            table_id=payload.table_id,
            question=payload.question,
            qa_id=payload.qa_id,
            expected_answer=payload.expected_answer,
            request_id=request_id,
        )
        payload = result.model_dump()
        store_result(request_id, payload)
        finish_progress(request_id, "Answer ready.")
        return payload
    except KeyError as exc:
        fail_progress(request_id, str(exc))
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ModelUnavailableError as exc:
        fail_progress(request_id, str(exc))
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        fail_progress(request_id, str(exc))
        raise


@app.post("/api/ask/{qa_id}")
def ask_existing(qa_id: str, split: str = Query(default="dev", pattern="^(train|dev|test)$")) -> dict[str, object]:
    request_id = f"qa-{qa_id}"
    start_progress(request_id, f"Received /api/ask/{qa_id} request.")
    try:
        result = answer_qa(qa_id, split, request_id=request_id)
        payload = result.model_dump()
        store_result(request_id, payload)
        finish_progress(request_id, "Answer ready.")
        return payload
    except KeyError as exc:
        fail_progress(request_id, str(exc))
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ModelUnavailableError as exc:
        fail_progress(request_id, str(exc))
        raise HTTPException(status_code=503, detail=str(exc)) from exc
