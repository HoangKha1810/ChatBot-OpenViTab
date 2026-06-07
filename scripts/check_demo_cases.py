from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.pipeline import answer_qa
from app.text_utils import normalize_key


CASES = [
    ("dev", "56_3_238", "110"),
    ("dev", "23_4_88", "#1"),
    ("test", "99932_2_90", "Guatemala"),
    ("test", "99921_1_43", "Phoenix"),
    ("test", "9990_2_27", "Có"),
    ("test", "99917_3_67", "Có"),
]


def main() -> int:
    failures = []
    for split, qa_id, expected in CASES:
        result = answer_qa(qa_id, split)
        ok = normalize_key(result.answer) == normalize_key(expected) and bool(result.evidence) and result.verifier.passed
        print(f"{'ok' if ok else 'fail'} {split}/{qa_id}: {result.answer!r} expected {expected!r}")
        if not ok:
            failures.append((split, qa_id, result.answer, expected))
    if failures:
        print(f"{len(failures)} demo case(s) failed", file=sys.stderr)
        return 1
    print("All demo cases passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
