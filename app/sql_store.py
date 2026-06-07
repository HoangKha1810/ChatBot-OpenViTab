from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Sequence

from app.config import PROCESSED_DATA_DIR
from app.models import EvidenceRow, TableInfo
from app.schema import sql_column_name
from app.text_utils import normalize_key, parse_number


def table_db_path(table_id: str) -> Path:
    safe = "".join(ch for ch in table_id if ch.isalnum() or ch in {"_", "-"})
    return PROCESSED_DATA_DIR / "sqlite" / f"{safe}.sqlite"


def ensure_table_db(table: TableInfo) -> Path:
    path = table_db_path(table.table_id)
    if path.exists():
        return path

    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        cols = []
        for index in range(len(table.headers)):
            cols.append(f"{sql_column_name(index)} TEXT")
            cols.append(f"{sql_column_name(index)}_num REAL")
            cols.append(f"{sql_column_name(index)}_key TEXT")
        conn.execute(
            "CREATE TABLE rows (row_index INTEGER PRIMARY KEY, "
            + ", ".join(cols)
            + ")"
        )
        placeholders = ", ".join(["?"] * (1 + len(cols)))
        col_names = ["row_index"]
        for index in range(len(table.headers)):
            col_names.extend([sql_column_name(index), f"{sql_column_name(index)}_num", f"{sql_column_name(index)}_key"])
        sql = f"INSERT INTO rows ({', '.join(col_names)}) VALUES ({placeholders})"
        for row_index, row in enumerate(table.rows, start=1):
            values: list[object] = [row_index]
            for index in range(len(table.headers)):
                cell = row[index] if index < len(row) else ""
                values.extend([cell, parse_number(cell), normalize_key(cell)])
            conn.execute(sql, values)
        for index in range(len(table.headers)):
            conn.execute(f"CREATE INDEX idx_rows_c{index}_key ON rows ({sql_column_name(index)}_key)")
            conn.execute(f"CREATE INDEX idx_rows_c{index}_num ON rows ({sql_column_name(index)}_num)")
        conn.commit()
    return path


@contextmanager
def connect_table(table: TableInfo) -> Iterator[sqlite3.Connection]:
    path = ensure_table_db(table)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def execute_sql(table: TableInfo, sql: str, params: Sequence[object] = ()) -> list[EvidenceRow]:
    with connect_table(table) as conn:
        cursor = conn.execute(sql, list(params))
        rows = cursor.fetchall()
    evidence: list[EvidenceRow] = []
    for raw in rows:
        values = {}
        for index, header in enumerate(table.headers):
            key = sql_column_name(index)
            if key in raw.keys():
                values[header] = "" if raw[key] is None else str(raw[key])
        row_index = int(raw["row_index"]) if "row_index" in raw.keys() else 0
        evidence.append(EvidenceRow(row_index=row_index, values=values))
    return evidence
