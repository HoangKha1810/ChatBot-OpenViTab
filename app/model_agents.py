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


def link_schema_with_model(runtime: OllamaRuntime, table: TableInfo, question: str) -> tuple[list[dict[str, Any]], ModelTrace]:
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
        column_texts.append(f"Cột {col.sql_name}: {col.header}. Alias: {aliases}. Ví dụ: {' | '.join(samples)}")

    embeddings, latency = runtime.embed(settings.schema_embed_model, [question] + column_texts)
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
        "Bạn là text-to-SQL agent cho SQLite. Chỉ trả JSON hợp lệ. "
        "Không giải thích ngoài JSON. Chỉ dùng bảng `rows`, cột row_index và các cột c0, c1... "
        "Dùng cN_key cho LIKE, cN_num cho so sánh số. Không dùng INSERT/UPDATE/DELETE/DROP."
    )
    user = json.dumps(
        {
            "task": "Sửa hoặc xác nhận SQL cho câu hỏi tiếng Việt.",
            "question": question,
            "table_title": table.table_title,
            "schema": schema,
            "schema_embedding_top": schema_rank[:6],
            "candidate": candidate_payload,
            "rules": [
                "Nếu candidate_sql đã đúng, giữ nguyên.",
                "SQL phải bắt đầu bằng SELECT và trả về row_index, * FROM rows.",
                "params phải là array; nếu SQL tự chứa literal thì params rỗng.",
                "Không được invent cột ngoài schema.",
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
                "explanation": "ngắn gọn bằng tiếng Việt",
            },
        },
        ensure_ascii=False,
    )

    parsed, latency, _ = runtime.chat_json(settings.text_to_sql_model, system, user)
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
            if model_evidence or not candidate_evidence:
                selected = PlannedSQL(plan=plan, trace=trace)
            else:
                status = "repaired"
                note = "Model SQL chạy được nhưng rỗng; giữ candidate SQL đã có evidence."
                candidate.trace.repaired = True
                candidate.trace.repair_notes.append(note)
        except Exception as exc:
            status = "repaired"
            note = f"Model SQL không execute được ({exc}); giữ candidate SQL."
            candidate.trace.repaired = True
            candidate.trace.repair_notes.append(note)
    else:
        status = "repaired"
        note = "Model không trả SELECT an toàn; giữ candidate SQL."
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
) -> tuple[str, ModelTrace]:
    settings = runtime.settings
    extractive = synthesize_answer(table, question, plan, evidence)
    system = (
        "Bạn là answer synthesis agent cho Vietnamese TableQA. "
        "Chỉ trả JSON. Câu trả lời phải ngắn, đúng theo evidence, không thêm thông tin ngoài bảng. "
        "Nếu extractive_answer là giá trị ô đúng thì giữ nguyên giá trị đó."
    )
    user = json.dumps(
        {
            "question": question,
            "table_title": table.table_title,
            "plan": plan.model_dump(),
            "extractive_answer": extractive,
            "evidence": [row.model_dump() for row in evidence[:8]],
            "return_json": {"answer": extractive, "rationale": "một câu ngắn"},
        },
        ensure_ascii=False,
    )
    parsed, latency, _ = runtime.chat_json(settings.answer_model, system, user)
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
) -> tuple[VerificationResult, ModelTrace]:
    settings = runtime.settings
    system = (
        "Bạn là evidence verifier cho Vietnamese TableQA. Chỉ trả JSON. "
        "Kiểm tra câu trả lời có được chứng minh trực tiếp bởi evidence không."
    )
    user = json.dumps(
        {
            "question": question,
            "answer": answer,
            "plan": plan.model_dump(),
            "evidence": [row.model_dump() for row in evidence[:8]],
            "deterministic_verifier": deterministic.model_dump(),
            "return_json": {
                "passed": deterministic.passed,
                "checks": ["..."],
                "unsupported_reasons": [],
            },
        },
        ensure_ascii=False,
    )
    parsed, latency, _ = runtime.chat_json(settings.verifier_model, system, user)
    model_passed = bool(parsed.get("passed"))
    model_checks = [str(item) for item in parsed.get("checks", []) if str(item).strip()] if isinstance(parsed.get("checks"), list) else []
    model_reasons = (
        [str(item) for item in parsed.get("unsupported_reasons", []) if str(item).strip()]
        if isinstance(parsed.get("unsupported_reasons"), list)
        else []
    )

    checks = deterministic.checks + [f"Model verifier: {item}" for item in model_checks[:4]]
    reasons = list(deterministic.unsupported_reasons)
    if not model_passed:
        reasons.extend(model_reasons or ["Model verifier không xác nhận evidence support."])

    return VerificationResult(
        passed=deterministic.passed and model_passed,
        checks=checks,
        unsupported_reasons=reasons,
    ), ModelTrace(
        task="verification",
        backend=settings.backend,
        model=settings.verifier_model,
        status="ok" if model_passed else "failed",
        latency_ms=latency,
        note="Model verifier combined with deterministic evidence checks.",
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
