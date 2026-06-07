from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    data_file = ROOT / "data" / "raw" / "table.json"
    if not data_file.exists():
        subprocess.check_call([sys.executable, str(ROOT / "scripts" / "download_open_vitabqa.py")], cwd=ROOT)
    print("Starting demo at http://127.0.0.1:8000")
    return subprocess.call(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
            "--reload",
        ],
        cwd=ROOT,
    )


if __name__ == "__main__":
    raise SystemExit(main())
