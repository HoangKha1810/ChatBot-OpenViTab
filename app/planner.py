from __future__ import annotations

import re
from dataclasses import dataclass

from app.models import QueryPlan, SQLTrace, TableInfo
from app.schema import best_column, column_at, first_text_column, numeric_columns
from app.text_utils import normalize_key, normalize_text, parse_number, token_set


@dataclass
class PlannedSQL:
    plan: QueryPlan
    trace: SQLTrace


QUESTION_WORD_TARGETS = {
    "ai": ["ten", "ho va ten", "nhan vat", "nguoi"],
    "nguoi nao": ["ten", "ho va ten", "nhan vat", "nguoi"],
    "quoc gia nao": ["quoc gia", "nuoc", "ten"],
    "nuoc nao": ["quoc gia", "nuoc"],
    "noi nao": ["thanh pho", "dia diem", "que quan", "noi", "khu vuc", "quoc gia"],
    "o dau": ["thanh pho", "dia diem", "que quan", "noi", "khu vuc", "quoc gia"],
    "khi nao": ["nam", "ngay", "thoi gian"],
    "nam nao": ["nam", "thoi gian", "ngay"],
}


def plan_sql(table: TableInfo, question: str) -> PlannedSQL:
    q_key = normalize_key(question)

    if _asks_max(q_key) or _asks_min(q_key):
        return _plan_extreme(table, question, q_key)

    if _is_yes_no(q_key):
        return _plan_yes_no(table, question, q_key)

    if _asks_count(q_key):
        return _plan_count(table, question, q_key)

    return _plan_lookup(table, question, q_key)


def _plan_lookup(table: TableInfo, question: str, q_key: str) -> PlannedSQL:
    answer_column = _infer_answer_column(table, question, q_key)
    filter_column, filter_value = _infer_filter(table, question, answer_column.index)

    numeric_value = _extract_number_constraint(q_key, question)
    if numeric_value is not None and (filter_column is None or filter_value is None):
        numeric_column = _infer_numeric_target_column(table, question, exclude_indexes={answer_column.index})
        sql = f"SELECT row_index, * FROM rows WHERE {numeric_column.sql_name}_num = ? LIMIT 12"
        plan = QueryPlan(
            intent="lookup",
            operation="numeric_filter_project",
            answer_column=answer_column.header,
            filter_column=numeric_column.header,
            filter_value=_format_filter_number(numeric_value),
            numeric_value=numeric_value,
            explanation=f"Tìm dòng có '{numeric_column.header}' bằng {numeric_value:g} rồi lấy cột '{answer_column.header}'.",
        )
        return PlannedSQL(plan=plan, trace=SQLTrace(sql=sql, params=[numeric_value]))

    if filter_column is None or filter_value is None:
        sql = "SELECT row_index, * FROM rows LIMIT 8"
        plan = QueryPlan(
            intent="lookup",
            operation="table_preview",
            answer_column=answer_column.header,
            explanation="Không tìm được điều kiện lọc chắc chắn, trả về các dòng đầu để tổng hợp có kiểm chứng.",
        )
        return PlannedSQL(plan=plan, trace=SQLTrace(sql=sql))

    sql = f"SELECT row_index, * FROM rows WHERE {filter_column.sql_name}_key LIKE ? LIMIT 12"
    params = [f"%{normalize_key(filter_value)}%"]
    plan = QueryPlan(
        intent="lookup",
        operation="filter_project",
        answer_column=answer_column.header,
        filter_column=filter_column.header,
        filter_value=filter_value,
        explanation=f"Tìm dòng chứa '{filter_value}' rồi lấy cột '{answer_column.header}'.",
    )
    return PlannedSQL(plan=plan, trace=SQLTrace(sql=sql, params=params))


def _plan_count(table: TableInfo, question: str, q_key: str) -> PlannedSQL:
    numeric_value = _extract_number_constraint(q_key)
    target_column = _infer_numeric_target_column(table, question)
    filter_column, filter_value = _infer_filter(table, question, target_column.index)

    where = []
    params: list[str | float] = []
    explanation_bits = []
    if numeric_value is not None:
        op = _infer_comparison_operator(q_key)
        where.append(f"{target_column.sql_name}_num {op} ?")
        params.append(numeric_value)
        explanation_bits.append(f"{target_column.header} {op} {numeric_value:g}")
    if filter_column is not None and filter_value is not None:
        where.append(f"{filter_column.sql_name}_key LIKE ?")
        params.append(f"%{normalize_key(filter_value)}%")
        explanation_bits.append(f"{filter_column.header} chứa '{filter_value}'")

    sql = "SELECT row_index, * FROM rows"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " LIMIT 200"
    plan = QueryPlan(
        intent="count",
        operation="count_rows",
        answer_column="COUNT(*)",
        filter_column=filter_column.header if filter_column else target_column.header if numeric_value is not None else None,
        filter_value=filter_value,
        numeric_value=numeric_value,
        explanation="Đếm các dòng thỏa điều kiện: " + (", ".join(explanation_bits) if explanation_bits else "toàn bộ bảng."),
    )
    return PlannedSQL(plan=plan, trace=SQLTrace(sql=sql, params=params))


def _plan_extreme(table: TableInfo, question: str, q_key: str) -> PlannedSQL:
    is_max = _asks_max(q_key)
    sort_column = _infer_sort_column_for_extreme(table, question, q_key)
    answer_column = _infer_answer_column(table, question, q_key, fallback=sort_column.index)

    sql = (
        "SELECT row_index, * FROM rows "
        f"WHERE {sort_column.sql_name}_num IS NOT NULL "
        f"ORDER BY {sort_column.sql_name}_num {'DESC' if is_max else 'ASC'} LIMIT 1"
    )
    plan = QueryPlan(
        intent="superlative",
        operation="max" if is_max else "min",
        answer_column=answer_column.header,
        sort_column=sort_column.header,
        sort_direction="DESC" if is_max else "ASC",
        explanation=f"Sắp xếp theo cột '{sort_column.header}' để lấy giá trị {'lớn nhất' if is_max else 'nhỏ nhất'}.",
    )
    return PlannedSQL(plan=plan, trace=SQLTrace(sql=sql))


def _plan_yes_no(table: TableInfo, question: str, q_key: str) -> PlannedSQL:
    numbers = _numbers_in_question(question)
    if len(numbers) >= 2 and "nam" in q_key and any(term in q_key for term in ["duoi", "nho hon", "tren", "lon hon", "hon", "bang"]):
        year_column = best_column(table, question, ["nam"])
        target_column = _infer_numeric_target_column(table, question, exclude_indexes={year_column.index})
        op = _infer_comparison_operator(q_key)
        year_value = numbers[0]
        compare_value = numbers[-1]
        sql = (
            "SELECT row_index, * FROM rows "
            f"WHERE {year_column.sql_name}_num = ? AND {target_column.sql_name}_num {op} ? LIMIT 20"
        )
        plan = QueryPlan(
            intent="yes_no",
            operation="compound_numeric_check",
            answer_column="Có/Không",
            filter_column=f"{year_column.header}; {target_column.header}",
            numeric_value=compare_value,
            explanation=f"Kiểm tra dòng năm {year_value:g} có '{target_column.header}' {op} {compare_value:g}.",
        )
        return PlannedSQL(plan=plan, trace=SQLTrace(sql=sql, params=[year_value, compare_value]))

    if len(numbers) >= 2 and any(term in q_key for term in ["cao tu", "tu", "tro len"]):
        threshold = numbers[-1]
        count_value = numbers[0]
        threshold_col = _column_with_number_in_header(table, threshold)
        if threshold_col is not None:
            sql = f"SELECT row_index, * FROM rows WHERE {threshold_col.sql_name}_num = ? LIMIT 20"
            plan = QueryPlan(
                intent="yes_no",
                operation="header_threshold_count_check",
                answer_column="Có/Không",
                filter_column=threshold_col.header,
                numeric_value=count_value,
                explanation=f"Cột '{threshold_col.header}' đã mã hóa ngưỡng {threshold:g}; kiểm tra giá trị bằng {count_value:g}.",
            )
            return PlannedSQL(plan=plan, trace=SQLTrace(sql=sql, params=[count_value]))

    numeric_value = _extract_number_constraint(q_key, question)
    if numeric_value is not None:
        target_column = _infer_numeric_target_column(table, question)
        op = _infer_comparison_operator(q_key)
        sql = f"SELECT row_index, * FROM rows WHERE {target_column.sql_name}_num {op} ? LIMIT 200"
        plan = QueryPlan(
            intent="yes_no",
            operation="existence_numeric",
            answer_column="Có/Không",
            filter_column=target_column.header,
            numeric_value=numeric_value,
            explanation=f"Kiểm tra có dòng nào có '{target_column.header}' {op} {numeric_value:g}.",
        )
        return PlannedSQL(plan=plan, trace=SQLTrace(sql=sql, params=[numeric_value]))

    filter_column, filter_value = _infer_filter(table, question, None)
    if filter_column is not None and filter_value is not None:
        sql = f"SELECT row_index, * FROM rows WHERE {filter_column.sql_name}_key LIKE ? LIMIT 20"
        plan = QueryPlan(
            intent="yes_no",
            operation="existence_text",
            answer_column="Có/Không",
            filter_column=filter_column.header,
            filter_value=filter_value,
            explanation=f"Kiểm tra bảng có bằng chứng chứa '{filter_value}' ở cột '{filter_column.header}'.",
        )
        return PlannedSQL(plan=plan, trace=SQLTrace(sql=sql, params=[f"%{normalize_key(filter_value)}%"]))

    sql = "SELECT row_index, * FROM rows LIMIT 20"
    plan = QueryPlan(
        intent="yes_no",
        operation="weak_existence",
        answer_column="Có/Không",
        explanation="Không tách được điều kiện yes/no rõ ràng, dùng preview bảng để trả lời thận trọng.",
    )
    return PlannedSQL(plan=plan, trace=SQLTrace(sql=sql))


def _infer_answer_column(table: TableInfo, question: str, q_key: str, fallback: int | None = None):
    candidates: list[str] = []
    if "noi nao" in q_key or "o dau" in q_key:
        candidates.extend(["thanh pho", "dia diem", "que quan", "quoc gia", "khu vuc"])
    if "thu hang trong khung gio" in q_key or "xep hang trong khung gio" in q_key:
        candidates.extend(["xep hang trong khung gio", "thu hang", "hang"])
    if "bao nhieu tang" in q_key or "so tang" in q_key:
        candidates.extend(["so tang", "tang"])
    if "cao bao nhieu" in q_key:
        candidates.extend(["chieu cao", "cao"])
    for phrase, targets in QUESTION_WORD_TARGETS.items():
        if phrase in q_key:
            candidates.extend(targets)
    if candidates:
        return best_column(table, question, candidates)
    if fallback is not None:
        return best_column(table, question, [table.headers[fallback]])
    return first_text_column(table)


def _infer_numeric_target_column(table: TableInfo, question: str, exclude_indexes: set[int] | None = None):
    excluded = exclude_indexes or set()
    numerics = [column for column in numeric_columns(table) if column.index not in excluded]
    if not numerics:
        return best_column(table, question)
    scored = []
    q_tokens = token_set(question)
    for column in numerics:
        overlap = len((token_set(column.header) | set(column.aliases)) & q_tokens)
        scored.append((column.question_score + overlap, -column.index, column))
    return max(scored, key=lambda item: item[:2])[2]


def _infer_sort_column_for_extreme(table: TableInfo, question: str, q_key: str):
    if "chieu cao" in q_key or "cao nhat" in q_key or "cao hon" in q_key:
        return best_column(table, question, ["chieu cao", "cao"])
    if "tuoi" in q_key:
        return best_column(table, question, ["tuoi"])
    if "can nang" in q_key or "nang nhat" in q_key:
        return best_column(table, question, ["can nang", "nang"])
    if "dan so" in q_key or "dong nhat" in q_key:
        return best_column(table, question, ["dan so"])
    if "do am" in q_key:
        return best_column(table, question, ["do am", "% do am"])
    return _infer_numeric_target_column(table, question)


def _infer_filter(table: TableInfo, question: str, answer_col_index: int | None):
    q_key = normalize_key(question)
    best = None
    ignored = {answer_col_index} if answer_col_index is not None else set()
    for row in table.rows:
        for col_index, cell in enumerate(row):
            if col_index in ignored:
                continue
            cell_key = normalize_key(cell)
            if len(cell_key) < 2:
                continue
            if cell_key in q_key:
                score = len(cell_key)
                if best is None or score > best[0]:
                    best = (score, col_index, cell)
    if best:
        _, col_index, cell = best
        return column_at(table, col_index), cell

    q_compact = re.sub(r"\s+", "", q_key)
    for row in table.rows:
        for col_index, cell in enumerate(row):
            if col_index in ignored:
                continue
            cell_key = normalize_key(cell)
            if len(cell_key) < 4:
                continue
            compact_cell = re.sub(r"\s+", "", cell_key)
            if compact_cell and compact_cell in q_compact:
                return column_at(table, col_index), cell

    quoted = re.findall(r"[\"'“”‘’]([^\"'“”‘’]{2,})[\"'“”‘’]", question)
    if quoted:
        return first_text_column(table), quoted[0]
    return None, None


def _extract_number_constraint(q_key: str, question: str | None = None) -> float | None:
    if question:
        numbers = _numbers_in_question(question)
        if numbers:
            if "duoi" in q_key or "nho hon" in q_key:
                return numbers[-1]
            return numbers[0]

    patterns = [
        r"(-?\d(?:[\d.,]|\s(?=\d{3}\b))*)\s*nghin",
        r"(?:tu|tren|duoi|hon|kem|bang|dat|nam|hang|cao|thap)\s+(-?\d[\d.,]*)",
        r"(-?\d[\d.,]*)\s*(?:nam|tuoi|tang|m|nguoi|%|quoc gia|toa nha)",
    ]
    for pattern in patterns:
        match = re.search(pattern, q_key)
        if match:
            return parse_number(match.group(1))
    return None


def _numbers_in_question(question: str) -> list[float]:
    values: list[float] = []
    text = normalize_text(question)
    for match in re.finditer(r"-?\d[\d.,]*(?:\s?\d{3})*", text):
        value = parse_number(match.group(0))
        if value is not None:
            values.append(value)
    return values


def _column_with_number_in_header(table: TableInfo, number: float):
    wanted = str(int(number)) if abs(number - int(number)) < 1e-9 else str(number)
    for index, header in enumerate(table.headers):
        if wanted in normalize_key(header):
            return column_at(table, index)
    return None


def _format_filter_number(value: float) -> str:
    return str(int(value)) if abs(value - int(value)) < 1e-9 else str(value)


def _infer_comparison_operator(q_key: str) -> str:
    if any(term in q_key for term in ["duoi", "nho hon", "thap hon", "duoi muc"]):
        return "<"
    if any(term in q_key for term in ["khong qua", "toi da", "cao nhat la"]):
        return "<="
    if any(term in q_key for term in ["tu ", "tro len", "lon hon hoac bang", "cao tu", ">= "]):
        return ">="
    if any(term in q_key for term in ["tren", "lon hon", "cao hon", "hon"]):
        return ">"
    return "="


def _asks_count(q_key: str) -> bool:
    return "bao nhieu" in q_key or q_key.startswith("co bao nhieu") or "dem" in q_key


def _asks_max(q_key: str) -> bool:
    return any(term in q_key for term in ["cao nhat", "lon nhat", "nhieu nhat", "nang nhat", "top 1", "hang 1"])


def _asks_min(q_key: str) -> bool:
    return any(term in q_key for term in ["thap nhat", "nho nhat", "it nhat", "nhe nhat"])


def _is_yes_no(q_key: str) -> bool:
    return any(term in q_key for term in ["co phai", "dung khong", "phai khong", "co ", "khong?"]) and not _asks_count(q_key)
