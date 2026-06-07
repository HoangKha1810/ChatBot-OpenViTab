from __future__ import annotations

import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
BASE_URL = "https://raw.githubusercontent.com/DuzDao/Open-ViTabQA/main"
FILES = ("table.json", "qas_train.json", "qas_dev.json", "qas_test.json", "README.md", "LICENSE")


def main() -> int:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        url = f"{BASE_URL}/{name}"
        target = RAW_DIR / name
        if target.exists() and target.stat().st_size > 0:
            print(f"ok   {name} already exists")
            continue
        print(f"get  {url}")
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        target.write_bytes(response.content)
        print(f"save {target.relative_to(ROOT)} ({target.stat().st_size:,} bytes)")
    print("Open-ViTabQA data is ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
