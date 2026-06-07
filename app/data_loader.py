from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Literal

from app.config import RAW_DATA_DIR
from app.models import QAItem, TableInfo
from app.text_utils import normalize_key, normalize_text, parse_number

SplitName = Literal["train", "dev", "test"]


class DatasetNotFoundError(RuntimeError):
    pass


def _raw_file(name: str) -> Path:
    return RAW_DATA_DIR / name


def ensure_dataset_available() -> None:
    missing = [name for name in ("table.json", "qas_train.json", "qas_dev.json", "qas_test.json") if not _raw_file(name).exists()]
    if missing:
        raise DatasetNotFoundError(
            "Missing Open-ViTabQA files: "
            + ", ".join(missing)
            + ". Run `python scripts/download_open_vitabqa.py` first."
        )


@lru_cache(maxsize=1)
def load_tables() -> dict[str, TableInfo]:
    ensure_dataset_available()
    payload = json.loads(_raw_file("table.json").read_text(encoding="utf-8"))
    tables: dict[str, TableInfo] = {}
    for raw in payload.get("table", []):
        table_rows = (raw.get("table_dict") or {}).get("table_rows") or []
        if not table_rows:
            continue

        max_cols = max(len(row) for row in table_rows)
        padded = [[normalize_text(cell) for cell in row] + [""] * (max_cols - len(row)) for row in table_rows]
        headers, rows = _extract_headers_and_rows(padded, list(raw.get("table_type") or []))
        tables[raw["table_id"]] = TableInfo(
            table_id=raw["table_id"],
            table_title=normalize_text(raw.get("table_title") or ""),
            table_domain=normalize_text(raw.get("table_domain") or ""),
            table_type=list(raw.get("table_type") or []),
            headers=headers,
            rows=rows,
        )
    return tables


@lru_cache(maxsize=3)
def load_qas(split: SplitName = "dev") -> list[QAItem]:
    ensure_dataset_available()
    payload = json.loads(_raw_file(f"qas_{split}.json").read_text(encoding="utf-8"))
    return [QAItem(**item) for item in payload.get("qas", [])]


def get_table(table_id: str) -> TableInfo:
    tables = load_tables()
    if table_id not in tables:
        raise KeyError(f"Unknown table_id: {table_id}")
    return tables[table_id]


def get_qa(qa_id: str, split: SplitName = "dev") -> QAItem:
    for qa in load_qas(split):
        if qa.qa_id == qa_id:
            return qa
    raise KeyError(f"Unknown qa_id in {split}: {qa_id}")


def dataset_stats() -> dict[str, object]:
    tables = load_tables()
    return {
        "tables": len(tables),
        "qas": {split: len(load_qas(split)) for split in ("train", "dev", "test")},
        "domains": sorted({table.table_domain for table in tables.values() if table.table_domain}),
    }


def _dedupe_headers(headers: list[str]) -> list[str]:
    seen: dict[str, int] = {}
    output: list[str] = []
    for index, header in enumerate(headers):
        base = normalize_text(header) or f"Cột {index + 1}"
        count = seen.get(base, 0) + 1
        seen[base] = count
        output.append(base if count == 1 else f"{base} ({count})")
    return output


def _extract_headers_and_rows(table_rows: list[list[str]], table_type: list[str]) -> tuple[list[str], list[list[str]]]:
    if not table_rows:
        return [], []

    headers = table_rows[0]
    rows = table_rows[1:]
    if "contain_merged_header" not in table_type or not rows:
        return _dedupe_headers(headers), rows

    header_depth = _detect_extra_header_depth(headers, rows)
    if header_depth <= 0:
        return _dedupe_headers(headers), rows

    extra_headers = rows[:header_depth]
    data_rows = rows[header_depth:]
    base_counts: dict[str, int] = {}
    for header in headers:
        key = normalize_key(header)
        if key:
            base_counts[key] = base_counts.get(key, 0) + 1

    merged: list[str] = []
    for index, base in enumerate(headers):
        parts = [base]
        for extra in extra_headers:
            value = extra[index] if index < len(extra) else ""
            if value and normalize_key(value) not in {normalize_key(part) for part in parts if part}:
                parts.append(value)
        base_is_caption = base_counts.get(normalize_key(base), 0) >= max(2, len(headers) // 2)
        cleaned_parts = _drop_redundant_header_parts(parts, base_is_caption=base_is_caption)
        merged.append(" / ".join(cleaned_parts) if cleaned_parts else f"Cột {index + 1}")
    return _dedupe_headers(merged), data_rows


def _detect_extra_header_depth(headers: list[str], rows: list[list[str]]) -> int:
    depth = 0
    for row in rows[:3]:
        if _looks_like_header_row(headers, row):
            depth += 1
        else:
            break
    return depth


def _looks_like_header_row(headers: list[str], row: list[str]) -> bool:
    non_empty = [cell for cell in row if cell]
    if not non_empty:
        return False
    numeric_ratio = sum(parse_number(cell) is not None for cell in non_empty) / len(non_empty)
    repeated_ratio = sum(
        1
        for index, cell in enumerate(row)
        if index < len(headers) and normalize_key(cell) and normalize_key(cell) == normalize_key(headers[index])
    ) / max(len(non_empty), 1)
    unique_ratio = len({normalize_key(cell) for cell in non_empty}) / len(non_empty)
    return numeric_ratio < 0.35 and (repeated_ratio >= 0.25 or unique_ratio < 0.85)


def _drop_redundant_header_parts(parts: list[str], base_is_caption: bool = False) -> list[str]:
    if base_is_caption and len(parts) > 1:
        parts = parts[1:]

    output: list[str] = []
    for part in parts:
        key = normalize_key(part)
        if not key:
            continue
        if any(key == normalize_key(existing) or key in normalize_key(existing) or normalize_key(existing) in key for existing in output):
            if len(key) > max((len(normalize_key(existing)) for existing in output), default=0):
                output = [existing for existing in output if not normalize_key(existing) in key]
                output.append(part)
            continue
        output.append(part)
    return output
