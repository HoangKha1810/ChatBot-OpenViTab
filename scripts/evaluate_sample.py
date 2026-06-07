from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.data_loader import load_qas
from app.pipeline import answer_qa
from app.text_utils import normalize_key


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a quick deterministic evaluation on real Open-ViTabQA items.")
    parser.add_argument("--split", default="dev", choices=["train", "dev", "test"])
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--out", default="data/processed/sample_eval.json")
    args = parser.parse_args()

    qas = load_qas(args.split)[: args.limit]
    records = []
    exact = 0
    for qa in qas:
        result = answer_qa(qa.qa_id, args.split)
        expected = qa.answer or ""
        is_exact = normalize_key(result.answer) == normalize_key(expected)
        exact += int(is_exact)
        records.append(
            {
                "qa_id": qa.qa_id,
                "table_id": qa.table_id,
                "question": qa.question,
                "expected": expected,
                "predicted": result.answer,
                "exact": is_exact,
                "confidence": result.confidence.label,
                "sql": result.sql_trace.sql,
            }
        )

    output = {
        "split": args.split,
        "limit": len(qas),
        "exact_match": round(exact / max(len(qas), 1), 4),
        "records": records,
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in output.items() if k != "records"}, ensure_ascii=False, indent=2))
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
