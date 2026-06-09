from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Run selected notebooks with nbconvert when jupyter is available.")
    parser.add_argument("notebooks", nargs="*", help="Notebook paths. Defaults to notebooks/colab_ready/*.ipynb")
    parser.add_argument("--timeout", type=int, default=1800)
    parser.add_argument("--out", default="reports/execution_check_results.json")
    args = parser.parse_args()

    root = Path.cwd()
    notebooks = [Path(p) for p in args.notebooks] or sorted((root / "notebooks" / "colab_ready").glob("*.ipynb"))
    results = []
    for nb in notebooks:
        print(f"Running {nb} ...")
        cmd = [
            sys.executable,
            "-m",
            "jupyter",
            "nbconvert",
            "--to",
            "notebook",
            "--execute",
            "--ExecutePreprocessor.timeout",
            str(args.timeout),
            "--output",
            str(nb.with_suffix(".executed.ipynb")),
            str(nb),
        ]
        proc = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        results.append({"notebook": str(nb), "returncode": proc.returncode, "output_tail": proc.stdout[-4000:]})
    out = root / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if all(item["returncode"] == 0 for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
