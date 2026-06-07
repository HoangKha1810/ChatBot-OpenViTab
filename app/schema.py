from __future__ import annotations

import re

from app.models import ColumnInfo, TableInfo
from app.text_utils import jaccard, normalize_key, token_set


HEADER_ALIASES: dict[str, list[str]] = {
    "ten": ["ten", "ai", "nguoi nao", "doi nao", "quoc gia nao", "noi nao", "toa nha nao", "phim nao"],
    "ho va ten": ["ai", "nguoi nao", "ten", "ho ten"],
    "nhan vat": ["ai", "nguoi nao", "nhan vat"],
    "thanh pho": ["thanh pho", "noi nao", "o dau", "dia diem"],
    "khu vuc": ["khu vuc", "noi nao", "o dau"],
    "quoc gia": ["quoc gia", "nuoc nao", "noi nao", "o dau"],
    "dia diem": ["dia diem", "o dau", "noi nao", "thanh pho nao"],
    "que quan": ["que quan", "o dau", "noi nao"],
    "nam": ["nam nao", "khi nao", "thoi gian nao"],
    "thoi gian": ["khi nao", "thoi gian nao", "ngay nao", "nam nao"],
    "ngay": ["ngay nao", "khi nao"],
    "tuoi": ["bao nhieu tuoi", "tuoi"],
    "chieu cao": ["cao", "chieu cao", "cao nhat", "thap nhat"],
    "so tang": ["bao nhieu tang", "tang", "so tang"],
    "hang": ["hang", "thu hang", "xep hang", "rank"],
    "thu hang": ["hang", "thu hang", "xep hang"],
    "dan so": ["dan so", "bao nhieu nguoi"],
    "dan so do thi": ["dan so thanh thi", "dan so do thi"],
    "dan so nong thon": ["dan so nong thon"],
    "luong nguoi xem": ["luong nguoi xem", "nguoi xem", "rating"],
    "trung binh": ["trung binh", "binh quan"],
    "vi tri": ["vi tri", "choi o vi tri"],
    "chu tich": ["chu tich", "president"],
}


STOPWORDS = {
    "la",
    "cua",
    "co",
    "khong",
    "phai",
    "dung",
    "hay",
    "hoac",
    "va",
    "voi",
    "duoc",
    "nhung",
    "cac",
    "mot",
    "trong",
    "o",
    "tai",
    "cho",
    "biet",
    "bao",
    "nhieu",
    "nao",
    "gi",
    "ai",
    "khi",
    "thoi",
    "gian",
}


def sql_column_name(index: int) -> str:
    return f"c{index}"


def build_columns(table: TableInfo, question: str = "") -> list[ColumnInfo]:
    q_key = normalize_key(question)
    q_tokens = token_set(question) - STOPWORDS
    columns: list[ColumnInfo] = []
    for index, header in enumerate(table.headers):
        h_key = normalize_key(header)
        aliases = _aliases_for_header(h_key)
        alias_tokens = set()
        for alias in aliases:
            alias_tokens.update(token_set(alias))
        score = 0.0
        if h_key and h_key in q_key:
            score += 2.0
        score += jaccard(q_tokens, token_set(header) - STOPWORDS)
        if aliases:
            score += max((1.4 if alias in q_key else 0.0) for alias in aliases)
            score += 0.5 * jaccard(q_tokens, alias_tokens - STOPWORDS)
        columns.append(
            ColumnInfo(
                index=index,
                sql_name=sql_column_name(index),
                header=header,
                aliases=aliases[:6],
                question_score=round(score, 4),
            )
        )
    return columns


def best_column(table: TableInfo, question: str, candidates: list[str] | None = None) -> ColumnInfo:
    columns = build_columns(table, question)
    if candidates:
        candidate_keys = [normalize_key(item) for item in candidates]
        for column in columns:
            h_key = normalize_key(column.header)
            for key in candidate_keys:
                if not key:
                    continue
                if h_key == key:
                    column.question_score += 3.2
                elif h_key.endswith(key) or key in set(h_key.split()):
                    column.question_score += 2.2
                elif key in h_key or h_key in key:
                    column.question_score += 0.8
            if any(alias in candidate_keys for alias in column.aliases):
                column.question_score += 1.5
            column.question_score += _column_quality_score(table, column.index)
    return max(columns, key=lambda col: (col.question_score, -col.index))


def first_text_column(table: TableInfo) -> ColumnInfo:
    return ColumnInfo(index=0, sql_name=sql_column_name(0), header=table.headers[0])


def column_at(table: TableInfo, index: int) -> ColumnInfo:
    return ColumnInfo(index=index, sql_name=sql_column_name(index), header=table.headers[index])


def numeric_columns(table: TableInfo) -> list[ColumnInfo]:
    from app.text_utils import parse_number

    columns = build_columns(table)
    result: list[ColumnInfo] = []
    for column in columns:
        values = [row[column.index] for row in table.rows if column.index < len(row)]
        non_empty = [value for value in values if value]
        if not non_empty:
            continue
        numeric_values = [parse_number(value) for value in non_empty]
        numeric_count = sum(1 for value in numeric_values if value is not None)
        short_numeric_count = sum(
            1
            for value in non_empty
            if parse_number(value) is not None and len(str(value)) <= 28
        )
        if numeric_count / max(len(non_empty), 1) >= 0.70 and short_numeric_count / max(numeric_count, 1) >= 0.70:
            result.append(column)
    return result


def slug_header(header: str) -> str:
    key = normalize_key(header)
    slug = re.sub(r"[^a-z0-9]+", "_", key).strip("_")
    return slug or "cot"


def _column_quality_score(table: TableInfo, index: int) -> float:
    values = [row[index] for row in table.rows if index < len(row)]
    if not values:
        return -1.0
    non_empty_ratio = sum(1 for value in values if normalize_key(value)) / len(values)
    header_len = len(normalize_key(table.headers[index]))
    score = 0.8 * non_empty_ratio
    if non_empty_ratio < 0.2:
        score -= 1.4
    if header_len > 45:
        score -= 0.45
    if header_len <= 18:
        score += 0.25
    return score


def _aliases_for_header(header_key: str) -> list[str]:
    aliases: list[str] = []
    for key, values in HEADER_ALIASES.items():
        if key and (key in header_key or header_key in key):
            aliases.extend(values)
    return list(dict.fromkeys(aliases))
