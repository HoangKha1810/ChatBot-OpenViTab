from __future__ import annotations

from app.models import EvidenceRow, QueryPlan, VerificationResult
from app.text_utils import normalize_key


def verify_answer(answer: str, plan: QueryPlan, evidence: list[EvidenceRow]) -> VerificationResult:
    checks: list[str] = []
    reasons: list[str] = []

    if plan.intent in {"lookup", "superlative"}:
        if evidence:
            checks.append("Có evidence row trả về từ SQLite.")
        else:
            reasons.append("Không có dòng evidence để chứng minh câu trả lời.")

        answer_key = normalize_key(answer)
        if answer_key and any(answer_key in normalize_key(value) for row in evidence for value in row.values.values()):
            checks.append("Chuỗi trả lời xuất hiện trong evidence.")
        elif answer.startswith("Không tìm thấy"):
            reasons.append("Pipeline không tìm được câu trả lời có bằng chứng.")
        else:
            reasons.append("Chuỗi trả lời chưa khớp trực tiếp với evidence.")

    elif plan.intent == "count":
        checks.append("Câu trả lời được tính bằng số dòng evidence sau khi execute SQL.")
        if answer.isdigit():
            checks.append("Định dạng count hợp lệ.")
        else:
            reasons.append("Count không phải số nguyên.")

    elif plan.intent == "yes_no":
        checks.append("Câu trả lời yes/no được suy ra từ sự tồn tại của evidence.")
        if normalize_key(answer) in {"co", "khong"}:
            checks.append("Định dạng yes/no hợp lệ.")
        else:
            reasons.append("Câu trả lời yes/no không hợp lệ.")

    if plan.filter_value and evidence:
        needle = normalize_key(plan.filter_value)
        if any(needle in normalize_key(value) for row in evidence for value in row.values.values()):
            checks.append("Điều kiện lọc xuất hiện trong evidence.")
        else:
            reasons.append("Evidence không chứa giá trị lọc đã lập kế hoạch.")

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
        label = "Cao"
    elif score >= 0.55:
        label = "Trung bình"
    else:
        label = "Thấp"
    return round(score, 3), label, factors
