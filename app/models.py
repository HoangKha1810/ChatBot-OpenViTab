from __future__ import annotations

from pydantic import BaseModel, Field


class QAItem(BaseModel):
    qa_id: str
    table_id: str
    question: str
    answer: str | None = None
    hints: list[str] = Field(default_factory=list)


class TableInfo(BaseModel):
    table_id: str
    table_title: str = ""
    table_domain: str = ""
    table_type: list[str] = Field(default_factory=list)
    headers: list[str]
    rows: list[list[str]]


class ColumnInfo(BaseModel):
    index: int
    sql_name: str
    header: str
    aliases: list[str] = Field(default_factory=list)
    question_score: float = 0.0


class QueryPlan(BaseModel):
    intent: str
    operation: str
    answer_column: str | None = None
    filter_column: str | None = None
    filter_value: str | None = None
    sort_column: str | None = None
    sort_direction: str | None = None
    numeric_value: float | None = None
    explanation: str = ""


class SQLTrace(BaseModel):
    sql: str
    params: list[str | float | int] = Field(default_factory=list)
    repaired: bool = False
    repair_notes: list[str] = Field(default_factory=list)


class EvidenceRow(BaseModel):
    row_index: int
    values: dict[str, str]


class VerificationResult(BaseModel):
    passed: bool
    checks: list[str]
    unsupported_reasons: list[str] = Field(default_factory=list)


class ConfidenceResult(BaseModel):
    score: float
    label: str
    factors: dict[str, float]


class ModelTrace(BaseModel):
    task: str
    backend: str
    model: str
    status: str
    latency_ms: float = 0.0
    note: str = ""


class AnswerResult(BaseModel):
    qa_id: str | None = None
    table_id: str
    question: str
    expected_answer: str | None = None
    answer: str
    table_title: str
    table_domain: str
    plan: QueryPlan
    sql_trace: SQLTrace
    evidence: list[EvidenceRow]
    verifier: VerificationResult
    confidence: ConfidenceResult
    model_trace: list[ModelTrace] = Field(default_factory=list)
    latency_ms: float
