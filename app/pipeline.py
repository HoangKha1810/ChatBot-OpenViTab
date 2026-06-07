from __future__ import annotations

import time
import uuid

from app.answerer import synthesize_answer
from app.data_loader import get_qa, get_table
from app.model_agents import (
    generate_sql_with_model,
    link_schema_with_model,
    synthesize_answer_with_model,
    verify_with_model,
)
from app.model_runtime import get_runtime
from app.models import AnswerResult, ConfidenceResult
from app.planner import plan_sql
from app.progress import add_progress
from app.sql_store import execute_sql
from app.verifier import score_confidence, verify_answer


def answer_question(
    table_id: str,
    question: str,
    qa_id: str | None = None,
    expected_answer: str | None = None,
    request_id: str | None = None,
) -> AnswerResult:
    progress_id = request_id or f"qa-{uuid.uuid4().hex[:8]}"
    started = time.perf_counter()
    add_progress(progress_id, "load_table", f"Loading real table {table_id}.")
    table = get_table(table_id)
    runtime = get_runtime()
    runtime.ensure_gpu(progress_id)
    runtime.ensure_ready(progress_id)
    model_trace = []

    add_progress(progress_id, "planner", "Building deterministic SQL candidate.")
    planned = plan_sql(table, question)
    if runtime.settings.enabled:
        add_progress(progress_id, "schema_linking", f"Embedding question and schema with {runtime.settings.schema_embed_model}.")
        schema_rank, trace = link_schema_with_model(runtime, table, question, request_id=progress_id)
        model_trace.append(trace)
        add_progress(progress_id, "schema_linking", trace.note)
        add_progress(progress_id, "text_to_sql", f"Calling {runtime.settings.text_to_sql_model} to validate SQL.")
        planned, trace = generate_sql_with_model(runtime, table, question, planned, schema_rank, request_id=progress_id)
        model_trace.append(trace)
        add_progress(progress_id, "text_to_sql", f"{trace.status}: {trace.note}")

    sql_ok = True
    try:
        add_progress(progress_id, "execute_sql", f"Executing SQL: {planned.trace.sql}")
        evidence = execute_sql(table, planned.trace.sql, planned.trace.params)
        add_progress(progress_id, "execute_sql", f"SQL returned {len(evidence)} evidence row(s).")
    except Exception as exc:
        sql_ok = False
        add_progress(progress_id, "execute_sql", f"SQL failed: {exc}. Falling back to table preview.")
        planned.trace.repaired = True
        planned.trace.repair_notes.append(f"SQL lỗi: {exc}. Fallback sang preview bảng.")
        planned.trace.sql = "SELECT row_index, * FROM rows LIMIT 8"
        planned.trace.params = []
        evidence = execute_sql(table, planned.trace.sql, planned.trace.params)
        add_progress(progress_id, "execute_sql", f"Fallback SQL returned {len(evidence)} row(s).")

    if runtime.settings.enabled:
        add_progress(progress_id, "answer", f"Calling {runtime.settings.answer_model} for evidence-grounded answer.")
        answer, trace = synthesize_answer_with_model(runtime, table, question, planned.plan, evidence, request_id=progress_id)
        model_trace.append(trace)
        add_progress(progress_id, "answer", f"{trace.status}: {trace.note}")
    else:
        add_progress(progress_id, "answer", "Using deterministic extractive answer mode.")
        answer = synthesize_answer(table, question, planned.plan, evidence)

    add_progress(progress_id, "verifier", "Running deterministic evidence verifier.")
    deterministic_verifier = verify_answer(answer, planned.plan, evidence)
    if runtime.settings.enabled:
        add_progress(progress_id, "verifier", f"Calling {runtime.settings.verifier_model} for model verification.")
        verifier, trace = verify_with_model(
            runtime,
            question,
            answer,
            planned.plan,
            evidence,
            deterministic_verifier,
            request_id=progress_id,
        )
        model_trace.append(trace)
        add_progress(progress_id, "verifier", f"{trace.status}: {trace.note}")
        add_progress(progress_id, "verifier", f"Deterministic evidence verifier passed={verifier.passed}.")
    else:
        verifier = deterministic_verifier

    score, label, factors = score_confidence(sql_ok, evidence, verifier.passed, planned.trace.repaired)
    add_progress(progress_id, "confidence", f"Confidence {label} = {score}.")

    return AnswerResult(
        qa_id=qa_id,
        table_id=table_id,
        question=question,
        expected_answer=expected_answer,
        answer=answer,
        table_title=table.table_title,
        table_domain=table.table_domain,
        plan=planned.plan,
        sql_trace=planned.trace,
        evidence=evidence[:20],
        verifier=verifier,
        confidence=ConfidenceResult(score=score, label=label, factors=factors),
        model_trace=model_trace,
        latency_ms=round((time.perf_counter() - started) * 1000, 2),
    )


def answer_qa(qa_id: str, split: str = "dev", request_id: str | None = None) -> AnswerResult:
    qa = get_qa(qa_id, split)  # type: ignore[arg-type]
    return answer_question(
        table_id=qa.table_id,
        question=qa.question,
        qa_id=qa.qa_id,
        expected_answer=qa.answer,
        request_id=request_id,
    )
