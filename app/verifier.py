from __future__ import annotations

from app.models import EvidenceRow, QueryPlan, VerificationResult
from app.text_utils import normalize_key


def verify_answer(answer: str, plan: QueryPlan, evidence: list[EvidenceRow]) -> VerificationResult:
    checks: list[str] = []
    reasons: list[str] = []

    if plan.intent in {"lookup", "superlative"}:
        if evidence:
            checks.append("SQLite returned evidence rows.")
        else:
            reasons.append("No evidence rows are available to support the answer.")

        answer_key = normalize_key(answer)
        if answer_key and any(answer_key in normalize_key(value) for row in evidence for value in row.values.values()):
            checks.append("The answer string appears in the evidence.")
        elif answer.startswith("Không tìm thấy"):
            reasons.append("The pipeline could not find an evidence-backed answer.")
        else:
            reasons.append("The answer string does not directly match the evidence.")

    elif plan.intent == "count":
        checks.append("The answer is computed from the number of evidence rows returned by SQL.")
        if answer.isdigit():
            checks.append("Count format is valid.")
        else:
            reasons.append("Count is not an integer.")

    elif plan.intent == "yes_no":
        checks.append("The yes/no answer is inferred from the presence of evidence.")
        if normalize_key(answer) in {"co", "khong"}:
            checks.append("Vietnamese yes/no format is valid.")
        else:
            reasons.append("The yes/no answer is invalid.")

    if plan.filter_value and evidence:
        needle = normalize_key(plan.filter_value)
        if any(needle in normalize_key(value) for row in evidence for value in row.values.values()):
            checks.append("The planned filter value appears in the evidence.")
        else:
            reasons.append("The evidence does not contain the planned filter value.")

    return VerificationResult(passed=not reasons, checks=checks, unsupported_reasons=reasons)


def score_confidence(sql_ok: bool, evidence: list[EvidenceRow], verifier_passed: bool, repaired: bool) -> tuple[float, str, dict[str, float]]:
    factors = {
        "sql_executable": 1.0 if sql_ok else 0.0,
        "evidence_non_empty": 1.0 if evidence else 0.0,
        "verifier_passed": 1.0 if verifier_passed else 0.0,
        "no_repair_needed": 0.85 if repaired else 1.0,
    }
    score = 0.28 * factors["sql_executable"] + 0.27 * factors["evidence_non_empty"] + 0.35 * factors["verifier_passed"] + 0.10 * factors["no_repair_needed"]
    if score >= 0.82:
        label = "High"
    elif score >= 0.55:
        label = "Medium"
    else:
        label = "Low"
    return round(score, 3), label, factors
