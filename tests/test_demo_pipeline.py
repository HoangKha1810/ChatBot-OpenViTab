import os

os.environ.setdefault("TABLEQA_USE_MODELS", "0")
os.environ.setdefault("TABLEQA_REQUIRE_MODELS", "0")

from app.pipeline import answer_qa
from app.text_utils import normalize_key


DEMO_CASES = [
    ("dev", "56_3_238", "110"),
    ("dev", "23_4_88", "#1"),
    ("test", "99932_2_90", "Guatemala"),
    ("test", "99921_1_43", "Phoenix"),
    ("test", "9990_2_27", "Có"),
    ("test", "99917_3_67", "Có"),
]


def test_demo_cases_are_grounded():
    for split, qa_id, expected in DEMO_CASES:
        result = answer_qa(qa_id, split)
        assert normalize_key(result.answer) == normalize_key(expected)
        assert result.evidence
        assert result.sql_trace.sql.startswith("SELECT")
        assert result.verifier.passed
