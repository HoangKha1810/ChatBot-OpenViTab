from __future__ import annotations

import json
import math
import re
from typing import Any

from app.answerer import synthesize_answer
from app.model_runtime import OllamaRuntime
from app.models import EvidenceRow, ModelTrace, QueryPlan, SQLTrace, TableInfo, VerificationResult
from app.planner import PlannedSQL
from app.schema import build_columns
from app.sql_store import execute_sql
from app.text_utils import normalize_key
from app.verifier import verify_answer


def link_schema_with_model(
    runtime: OllamaRuntime,
    table: TableInfo,
    question: str,
    request_id: str = "ollama",
) -> tuple[list[dict[str, Any]], ModelTrace]:
    settings = runtime.settings
    columns = build_columns(table, question)
    column_texts = []
    for col in columns:
        samples = []
        for row in table.rows[:20]:
            if col.index < len(row) and row[col.index] and row[col.index] not in samples:
                samples.append(row[col.index])
            if len(samples) >= 3:
                break
        aliases = ", ".join(col.aliases)
        column_texts.append(f"Column {col.sql_name}: {col.header}. Aliases: {aliases}. Examples: {' | '.join(samples)}")

    embeddings, latency = runtime.embed(settings.schema_embed_model, [question] + column_texts, request_id=request_id)
    q_vec = embeddings[0]
    ranked = []
    for col, emb in zip(columns, embeddings[1:]):
        ranked.append(
            {
                "index": col.index,
                "sql_name": col.sql_name,
                "header": col.header,
                "score": round(_cosine(q_vec, emb), 4),
            }
        )
    ranked.sort(key=lambda item: item["score"], reverse=True)
    top = ", ".join(f"{item['sql_name']}={item['header']} ({item['score']})" for item in ranked[:4])
    return ranked, ModelTrace(
        task="schema_linking",
        backend=settings.backend,
        model=settings.schema_embed_model,
        status="ok",
        latency_ms=latency,
        note=f"Top columns: {top}",
    )


def generate_sql_with_model(
    runtime: OllamaRuntime,
    table: TableInfo,
    question: str,
    candidate: PlannedSQL,
    schema_rank: list[dict[str, Any]],
    request_id: str = "ollama",
) -> tuple[PlannedSQL, ModelTrace]:
    settings = runtime.settings
    schema = _schema_description(table)
    candidate_payload = {
        "intent": candidate.plan.intent,
        "operation": candidate.plan.operation,
        "candidate_sql": candidate.trace.sql,
        "candidate_params": candidate.trace.params,
        "answer_column": candidate.plan.answer_column,
        "filter_column": candidate.plan.filter_column,
        "filter_value": candidate.plan.filter_value,
        "sort_column": candidate.plan.sort_column,
        "sort_direction": candidate.plan.sort_direction,
    }
    system = (
        "You are a SQLite text-to-SQL agent for Vietnamese table questions. Return valid JSON only. "
        "Do not explain outside JSON. Use only table `rows`, row_index, and c0, c1... columns. "
        "Use cN_key for LIKE and cN_num for numeric comparisons. Do not use INSERT/UPDATE/DELETE/DROP."
    )
    user = json.dumps(
        {
            "task": "Repair or confirm the SQL for the Vietnamese question.",
            "question": question,
            "table_title": table.table_title,
            "schema": schema,
            "schema_embedding_top": schema_rank[:6],
            "candidate": candidate_payload,
            "rules": [
                "If candidate_sql is already correct, keep it unchanged.",
                "SQL must start with SELECT and return row_index, * FROM rows.",
                "params must be an array; if SQL contains literals directly, params must be empty.",
                "Do not invent columns outside the schema.",
            ],
            "return_json": {
                "sql": "SELECT row_index, * FROM rows ...",
                "params": [],
                "intent": candidate.plan.intent,
                "operation": candidate.plan.operation,
                "answer_column": candidate.plan.answer_column,
                "filter_column": candidate.plan.filter_column,
                "filter_value": candidate.plan.filter_value,
                "sort_column": candidate.plan.sort_column,
                "sort_direction": candidate.plan.sort_direction,
                "explanation": "brief English UI explanation",
            },
        },
        ensure_ascii=False,
    )

    parsed, latency, _ = runtime.chat_json(settings.text_to_sql_model, system, user, request_id=request_id)
    model_sql = str(parsed.get("sql") or "").strip()
    model_params = parsed.get("params") if isinstance(parsed.get("params"), list) else []
    status = "ok"
    note = "Model text-to-SQL accepted."
    selected = candidate

    if _safe_select(model_sql):
        plan = QueryPlan(
            intent=str(parsed.get("intent") or candidate.plan.intent),
            operation=str(parsed.get("operation") or candidate.plan.operation),
            answer_column=_none_if_empty(parsed.get("answer_column")) or candidate.plan.answer_column,
            filter_column=_none_if_empty(parsed.get("filter_column")) or candidate.plan.filter_column,
            filter_value=_none_if_empty(parsed.get("filter_value")) or candidate.plan.filter_value,
            sort_column=_none_if_empty(parsed.get("sort_column")) or candidate.plan.sort_column,
            sort_direction=_none_if_empty(parsed.get("sort_direction")) or candidate.plan.sort_direction,
            numeric_value=candidate.plan.numeric_value,
            explanation=str(parsed.get("explanation") or candidate.plan.explanation),
        )
        trace = SQLTrace(sql=model_sql, params=model_params)
        try:
            model_evidence = execute_sql(table, trace.sql, trace.params)
            candidate_evidence = execute_sql(table, candidate.trace.sql, candidate.trace.params)
            if candidate_evidence:
                status = "advisory"
                note = "Model SQL checked; keeping deterministic candidate because it already has evidence."
                selected = candidate
            elif model_evidence:
                selected = PlannedSQL(plan=plan, trace=trace)
            else:
                status = "repaired"
                note = "Model SQL executed but returned no rows; keeping the evidence-backed candidate SQL."
                candidate.trace.repaired = True
                candidate.trace.repair_notes.append(note)
        except Exception as exc:
            status = "repaired"
            note = f"Model SQL could not execute ({exc}); keeping the candidate SQL."
            candidate.trace.repaired = True
            candidate.trace.repair_notes.append(note)
    else:
        status = "repaired"
        note = "Model did not return a safe SELECT statement; keeping the candidate SQL."
        candidate.trace.repaired = True
        candidate.trace.repair_notes.append(note)

    return selected, ModelTrace(
        task="text_to_sql",
        backend=settings.backend,
        model=settings.text_to_sql_model,
        status=status,
        latency_ms=latency,
        note=note,
    )


def synthesize_answer_with_model(
    runtime: OllamaRuntime,
    table: TableInfo,
    question: str,
    plan: QueryPlan,
    evidence: list[EvidenceRow],
    request_id: str = "ollama",
) -> tuple[str, ModelTrace]:
    settings = runtime.settings
    extractive = synthesize_answer(table, question, plan, evidence)
    system = (
        "You are the answer synthesis agent for Vietnamese TableQA. Return valid JSON only. "
        "The `answer` value must be concise, natural Vietnamese. Use only the supplied evidence; "
        "do not add outside-table knowledge. Preserve exact cell values, names, units, and spelling. "
        "For yes/no questions, answer exactly `Có` or `Không`. If extractive_answer is the correct "
        "cell value, keep it unchanged. If the evidence is insufficient, return extractive_answer instead of guessing."
    )
    user = json.dumps(
        {
            "question": question,
            "table_title": table.table_title,
            "plan": plan.model_dump(),
            "extractive_answer": extractive,
            "evidence": [row.model_dump() for row in evidence[:12]],
            "return_json": {"answer": extractive, "rationale": "brief evidence reason"},
        },
        ensure_ascii=False,
    )
    parsed, latency, _ = runtime.chat_json(settings.answer_model, system, user, request_id=request_id)
    proposed = str(parsed.get("answer") or "").strip()
    if not proposed:
        proposed = extractive

    verification = verify_answer(proposed, plan, evidence)
    if verification.passed:
        return proposed, ModelTrace(
            task="answer_synthesis",
            backend=settings.backend,
            model=settings.answer_model,
            status="ok",
            latency_ms=latency,
            note="Model answer accepted by evidence verifier.",
        )

    return extractive, ModelTrace(
        task="answer_synthesis",
        backend=settings.backend,
        model=settings.answer_model,
        status="guarded",
        latency_ms=latency,
        note="Model answer was not directly supported; returned evidence-safe extractive answer.",
    )


def verify_with_model(
    runtime: OllamaRuntime,
    question: str,
    answer: str,
    plan: QueryPlan,
    evidence: list[EvidenceRow],
    deterministic: VerificationResult,
    request_id: str = "ollama",
) -> tuple[VerificationResult, ModelTrace]:
    settings = runtime.settings
    system = (
        "You are the evidence verifier for Vietnamese TableQA. Return valid JSON only. "
        "Check whether the Vietnamese answer is directly supported by the evidence. "
        "Use English for checks and unsupported_reasons."
    )
    user = json.dumps(
        {
            "question": question,
            "answer": answer,
            "plan": plan.model_dump(),
            "evidence": [row.model_dump() for row in evidence[:12]],
            "deterministic_verifier": deterministic.model_dump(),
            "return_json": {
                "passed": deterministic.passed,
                "checks": ["..."],
                "unsupported_reasons": [],
            },
        },
        ensure_ascii=False,
    )
    parsed, latency, _ = runtime.chat_json(settings.verifier_model, system, user, request_id=request_id)
    model_passed = bool(parsed.get("passed"))
    model_checks = [str(item) for item in parsed.get("checks", []) if str(item).strip()] if isinstance(parsed.get("checks"), list) else []
    model_reasons = (
        [str(item) for item in parsed.get("unsupported_reasons", []) if str(item).strip()]
        if isinstance(parsed.get("unsupported_reasons"), list)
        else []
    )

    checks = deterministic.checks + [f"Model verifier: {item}" for item in model_checks[:4]]
    reasons = list(deterministic.unsupported_reasons)
    if not model_passed and not deterministic.passed:
        reasons.extend(model_reasons or ["Model verifier did not confirm evidence support."])
    elif not model_passed:
        checks.append("Model verifier did not confirm support, but the deterministic evidence verifier passed, so the evidence-safe result is kept.")

    return VerificationResult(
        passed=deterministic.passed,
        checks=checks,
        unsupported_reasons=reasons,
    ), ModelTrace(
        task="verification",
        backend=settings.backend,
        model=settings.verifier_model,
        status="ok" if model_passed else "advisory",
        latency_ms=latency,
        note="Model verifier is advisory; deterministic evidence check is authoritative for demo stability.",
    )


def _schema_description(table: TableInfo) -> list[dict[str, str]]:
    rows = []
    for index, header in enumerate(table.headers):
        examples = []
        for row in table.rows[:20]:
            if index < len(row) and row[index] and row[index] not in examples:
                examples.append(row[index])
            if len(examples) >= 3:
                break
        rows.append(
            {
                "sql_text_column": f"c{index}",
                "sql_key_column": f"c{index}_key",
                "sql_numeric_column": f"c{index}_num",
                "header": header,
                "examples": " | ".join(examples),
            }
        )
    return rows


def _safe_select(sql: str) -> bool:
    normalized = normalize_key(sql)
    if not normalized.startswith("select"):
        return False
    blocked = {"insert", "update", "delete", "drop", "alter", "create", "attach", "pragma"}
    if any(re.search(rf"\b{term}\b", normalized) for term in blocked):
        return False
    return " from rows" in f" {sql.lower()} "


def _none_if_empty(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"null", "none", "-"}:
        return None
    return text


def _cosine(left: list[float], right: list[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if not left_norm or not right_norm:
        return 0.0
    return dot / (left_norm * right_norm)
