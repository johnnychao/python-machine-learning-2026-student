from __future__ import annotations

import ast
import json
import re
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
NOTEBOOK_DIR = REPO / "notebooks" / "day6_ai_solution_lab"
REPORT_PATH = REPO / "reports" / "day6_ai_solution_lab_validation.json"

NOTEBOOKS = [
    "00_preflight.ipynb",
    "01_cnn_pet_router.ipynb",
    "02_rnn_disaster_triage.ipynb",
    "03_gan_monet_studio.ipynb",
    "04_rl_connectx_agent.ipynb",
]

REQUIRED_FILES = [
    "DAY6_AI_SOLUTION_LAB.md",
    "data/ai_solution_lab/datasets.json",
    "docs/index.html",
    "docs/assets/styles.css",
    "docs/assets/app.js",
    "docs/assets/course-manifest.js",
    "practice/day6_ai_solution_lab/experiment_card.md",
    "practice/day6_ai_solution_lab/project_canvas.md",
]

EXPECTED_HANDLES = {
    "samuelcortinhas/cats-and-dogs-image-classification",
    "vstepanenko/disaster-tweets",
    "balraj98/monet2photo",
}


def result(check: str, status: str, detail: str) -> dict:
    return {"check": check, "status": status, "detail": detail}


def sanitized_python(source: str) -> tuple[str, list[str]]:
    kept: list[str] = []
    problems: list[str] = []
    for line_number, line in enumerate(source.splitlines(), start=1):
        stripped = line.lstrip()
        indent = len(line) - len(stripped)
        if stripped.startswith(("%", "!")):
            if indent:
                problems.append(f"indented IPython magic at line {line_number}: {stripped[:30]}")
            continue
        kept.append(line)
    return "\n".join(kept), problems


def validate_notebook(path: Path) -> list[dict]:
    checks: list[dict] = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [result(f"notebook:{path.name}:json", "fail", f"{type(exc).__name__}: {exc}")]

    structural_ok = (
        data.get("nbformat") == 4
        and isinstance(data.get("cells"), list)
        and data.get("metadata", {}).get("kernelspec", {}).get("name") == "python3"
    )
    checks.append(
        result(
            f"notebook:{path.name}:structure",
            "pass" if structural_ok else "fail",
            f"cells={len(data.get('cells', []))}, nbformat={data.get('nbformat')}",
        )
    )

    syntax_errors: list[str] = []
    all_text: list[str] = []
    for index, cell in enumerate(data.get("cells", [])):
        source = cell.get("source", "")
        if isinstance(source, list):
            source = "".join(source)
        all_text.append(source)
        if cell.get("cell_type") != "code":
            continue
        python_source, magic_problems = sanitized_python(source)
        syntax_errors.extend(f"cell {index}: {problem}" for problem in magic_problems)
        try:
            ast.parse(python_source)
        except SyntaxError as exc:
            syntax_errors.append(f"cell {index}: line {exc.lineno}: {exc.msg}")

    checks.append(
        result(
            f"notebook:{path.name}:python_syntax",
            "pass" if not syntax_errors else "fail",
            "all code cells compile after top-level magic removal"
            if not syntax_errors
            else "; ".join(syntax_errors),
        )
    )

    text = "\n".join(all_text)
    todo_count = text.count("TODO(學員必改)")
    expected_todos = 0 if path.name.startswith("00_") else 1
    checks.append(
        result(
            f"notebook:{path.name}:required_todo",
            "pass" if todo_count == expected_todos else "fail",
            f"expected={expected_todos}, found={todo_count}",
        )
    )

    has_seed = path.name.startswith("00_") or "SEED = 20260719" in text
    has_kaggle = "kaggle" in text.lower()
    has_limit = any(term in text for term in ["限制", "不能", "不可", "不是"])
    checks.extend(
        [
            result(f"notebook:{path.name}:fixed_seed", "pass" if has_seed else "fail", "fixed classroom seed"),
            result(f"notebook:{path.name}:kaggle_source", "pass" if has_kaggle else "fail", "Kaggle source/context present"),
            result(f"notebook:{path.name}:limitations", "pass" if has_limit else "fail", "limitations are explicit"),
        ]
    )

    outputs_empty = all(not cell.get("outputs") for cell in data.get("cells", []) if cell.get("cell_type") == "code")
    checks.append(
        result(
            f"notebook:{path.name}:clean_outputs",
            "pass" if outputs_empty else "fail",
            "student notebook does not ship stale execution output",
        )
    )
    return checks


def main() -> int:
    checks: list[dict] = []

    for relative in REQUIRED_FILES:
        path = REPO / relative
        checks.append(result(f"required_file:{relative}", "pass" if path.is_file() else "fail", str(path)))

    for filename in NOTEBOOKS:
        path = NOTEBOOK_DIR / filename
        if not path.is_file():
            checks.append(result(f"notebook:{filename}:exists", "fail", str(path)))
            continue
        checks.append(result(f"notebook:{filename}:exists", "pass", str(path)))
        checks.extend(validate_notebook(path))

    manifest_path = REPO / "data" / "ai_solution_lab" / "datasets.json"
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        handles = {source.get("handle") for source in manifest.get("sources", []) if source.get("handle")}
        checks.append(
            result(
                "dataset_manifest:handles",
                "pass" if handles == EXPECTED_HANDLES else "fail",
                f"handles={sorted(handles)}",
            )
        )
        license_ok = all(source.get("license_as_listed") for source in manifest.get("sources", []))
        checks.append(result("dataset_manifest:licenses", "pass" if license_ok else "fail", "all sources include listed license/terms"))

    searchable_paths = [
        REPO / ".gitignore",
        REPO / "DAY6_AI_SOLUTION_LAB.md",
        REPO / "docs" / "index.html",
        REPO / "docs" / "assets" / "app.js",
        REPO / "docs" / "assets" / "course-manifest.js",
    ] + [NOTEBOOK_DIR / filename for filename in NOTEBOOKS]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in searchable_paths if path.is_file())
    secret_patterns = [
        r'KAGGLE_USERNAME\s*=\s*["\'][^"\']+["\']',
        r'KAGGLE_KEY\s*=\s*["\'][^"\']+["\']',
        r'KAGGLE_API_TOKEN\s*=\s*["\'][A-Za-z0-9_-]{20,}["\']',
    ]
    secret_hits = [pattern for pattern in secret_patterns if re.search(pattern, combined)]
    checks.append(
        result(
            "security:no_hardcoded_kaggle_credentials",
            "pass" if not secret_hits else "fail",
            "no credential-shaped literals" if not secret_hits else f"matched patterns: {secret_hits}",
        )
    )
    gitignore_text = (REPO / ".gitignore").read_text(encoding="utf-8")
    ignores_ok = all(term in gitignore_text for term in ["kaggle.json", ".kaggle/", ".cache/kagglehub/"])
    checks.append(result("security:kaggle_ignored", "pass" if ignores_ok else "fail", "credential/cache ignore rules present"))

    html_path = REPO / "docs" / "index.html"
    if html_path.is_file():
        html = html_path.read_text(encoding="utf-8")
        accessibility_ok = all(term in html for term in ["lang=\"zh-Hant\"", "<main", "<nav", "aria-"])
        checks.append(result("website:semantic_accessibility", "pass" if accessibility_ok else "fail", "Traditional Chinese language and semantic landmarks"))
        no_inline_secret = "KAGGLE_API_TOKEN=" not in html and "kaggle.json" not in html.lower()
        checks.append(result("website:no_credentials", "pass" if no_inline_secret else "fail", "website contains no credential material"))

    failures = [check for check in checks if check["status"] == "fail"]
    report = {
        "status": "pass" if not failures else "fail",
        "checked_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "scope": "Static local validation only; does not prove fresh Google Colab execution or remote publication.",
        "summary": {"total": len(checks), "passed": len(checks) - len(failures), "failed": len(failures)},
        "checks": checks,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(report["summary"], ensure_ascii=False))
    if failures:
        for failure in failures:
            print("FAIL", failure["check"], "-", failure["detail"])
        print("Report:", REPORT_PATH)
        return 1
    print("PASS - static Day 6 package validation")
    print("Report:", REPORT_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
