from __future__ import annotations

import time

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
from app.sql_store import execute_sql
from app.verifier import score_confidence, verify_answer


def answer_question(table_id: str, question: str, qa_id: str | None = None, expected_answer: str | None = None) -> AnswerResult:
    started = time.perf_counter()
    table = get_table(table_id)
    runtime = get_runtime()
    runtime.ensure_ready()
    model_trace = []

    planned = plan_sql(table, question)
    if runtime.settings.enabled:
        schema_rank, trace = link_schema_with_model(runtime, table, question)
        model_trace.append(trace)
        planned, trace = generate_sql_with_model(runtime, table, question, planned, schema_rank)
        model_trace.append(trace)

    sql_ok = True
    try:
        evidence = execute_sql(table, planned.trace.sql, planned.trace.params)
    except Exception as exc:
        sql_ok = False
        planned.trace.repaired = True
        planned.trace.repair_notes.append(f"SQL lỗi: {exc}. Fallback sang preview bảng.")
        planned.trace.sql = "SELECT row_index, * FROM rows LIMIT 8"
        planned.trace.params = []
        evidence = execute_sql(table, planned.trace.sql, planned.trace.params)

    if runtime.settings.enabled:
        answer, trace = synthesize_answer_with_model(runtime, table, question, planned.plan, evidence)
        model_trace.append(trace)
    else:
        answer = synthesize_answer(table, question, planned.plan, evidence)

    deterministic_verifier = verify_answer(answer, planned.plan, evidence)
    if runtime.settings.enabled:
        verifier, trace = verify_with_model(runtime, question, answer, planned.plan, evidence, deterministic_verifier)
        model_trace.append(trace)
    else:
        verifier = deterministic_verifier

    score, label, factors = score_confidence(sql_ok, evidence, verifier.passed, planned.trace.repaired)

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


def answer_qa(qa_id: str, split: str = "dev") -> AnswerResult:
    qa = get_qa(qa_id, split)  # type: ignore[arg-type]
    return answer_question(
        table_id=qa.table_id,
        question=qa.question,
        qa_id=qa.qa_id,
        expected_answer=qa.answer,
    )
