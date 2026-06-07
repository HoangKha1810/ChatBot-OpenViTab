from __future__ import annotations

from app.models import EvidenceRow, QueryPlan, TableInfo
from app.schema import best_column
from app.text_utils import format_number, normalize_key, parse_number


def synthesize_answer(table: TableInfo, question: str, plan: QueryPlan, evidence: list[EvidenceRow]) -> str:
    if plan.intent == "count":
        return str(len(evidence))

    if plan.intent == "yes_no":
        return "Có" if evidence else "Không"

    if not evidence:
        return "Không tìm thấy bằng chứng phù hợp trong bảng."

    if plan.operation in {"max", "min"}:
        answer = _value_from_column(table, question, plan.answer_column, evidence[0])
        sort_value = _value_from_column(table, question, plan.sort_column, evidence[0])
        if plan.answer_column and plan.sort_column and normalize_key(plan.answer_column) != normalize_key(plan.sort_column):
            return answer
        numeric = parse_number(sort_value)
        return format_number(numeric) if numeric is not None else sort_value

    answer = _value_from_column(table, question, plan.answer_column, evidence[0])
    return answer or next(iter(evidence[0].values.values()), "")


def _value_from_column(table: TableInfo, question: str, column_header: str | None, row: EvidenceRow) -> str:
    if column_header and column_header in row.values:
        return row.values[column_header]
    column = best_column(table, question, [column_header] if column_header else None)
    return row.values.get(column.header, "")
