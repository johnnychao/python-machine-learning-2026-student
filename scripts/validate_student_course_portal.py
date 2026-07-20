from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


REPO = Path(__file__).resolve().parents[1]
DOCS = REPO / "docs"
CATALOG_PATH = DOCS / "assets" / "course-catalog.json"
HANDOUT_SOURCE_DIR = REPO / "handouts" / "student"
HANDOUT_PUBLIC_DIR = DOCS / "handouts"
NOTEBOOK_DIR = REPO / "notebooks" / "colab_ready"
REPORT_PATH = REPO / "reports" / "student_course_portal_validation.json"
HANDOUT_REPORT_PATH = REPO / "reports" / "student_handout_validation.json"
EXPECTED_REPO_NAME = "python-machine-learning-2026-student"
EXPECTED_REPO_SLUG = "johnnychao/python-machine-learning-2026-student"
EXPECTED_BRANCH = "main"

EXPECTED_ROUTES = [
    "index.html",
    "day-1/index.html",
    "day-2/index.html",
    "day-3/index.html",
    "day-4/index.html",
    "day-5/index.html",
    "extension/index.html",
    "practicum/index.html",
]

EXPECTED_NOTEBOOKS = [
    *(f"ch{chapter:02d}_ch{chapter:02d}_colab.ipynb" for chapter in range(1, 13)),
    "ch13_ch13_part1_colab.ipynb",
    "ch13_ch13_part2_colab.ipynb",
    "ch13_ch13_part3_colab.ipynb",
    "ch14_ch14_part1_colab.ipynb",
    "ch14_ch14_part2_colab.ipynb",
    "ch14_ch14_part3_colab.ipynb",
    "ch15_ch15_part1_colab.ipynb",
    "ch15_ch15_part2_colab.ipynb",
    "ch15_downloading-celeba_downloading-celeba_colab.ipynb",
    "ch16_ch16_part1_colab.ipynb",
    "ch16_ch16_part2_colab.ipynb",
    "ch17_ch17_part1_colab.ipynb",
    "ch17_ch17_part2_colab.ipynb",
    "ch18_ch18_colab.ipynb",
]

DAY6_PATTERN = re.compile(r"\bday[\s_-]*0?6\b|\bd6\b", re.IGNORECASE)
PROHIBITED_PATTERNS = {
    "instructor repository": re.compile(
        r"(?:github\.com/|githubusercontent\.com/)?johnnychao/"
        r"python-machine-learning-2026-instructor",
        re.IGNORECASE,
    ),
    "instructor repository slug": re.compile(
        r"python-machine-learning-2026-instructor", re.IGNORECASE
    ),
    "teacher workflow": re.compile(r"TEACHER_WORKFLOW", re.IGNORECASE),
    "local file URL": re.compile(r"file:\s*/{2,3}\s*[A-Za-z]:[/\\]", re.IGNORECASE),
    "instructor-only marker": re.compile(r"講師專用|教師專用|講師版|教師版"),
    "internal answer marker": re.compile(
        r"內部答案|內部解答|教師解答|講師解答|參考答案|解答區|標準答案\s*[:：]|"
        r"ANSWER[_ -]?KEY|INSTRUCTOR[_ -]?ONLY",
        re.IGNORECASE,
    ),
}
SUBMISSION_BOUNDARY_PATTERNS = {
    "user profile path": re.compile(r"[A-Za-z]:(?:\\+|/+)Users(?:\\+|/+)", re.IGNORECASE),
    "local file URL": re.compile(r"file:\s*/{2,3}", re.IGNORECASE),
    "private repository slug": re.compile(r"python-machine-learning-2026-instructor", re.IGNORECASE),
}
SUBMISSION_TEXT_SUFFIXES = {".json", ".html", ".js", ".cjs", ".md"}
SUBMISSION_EXCLUDED_DIRS = {".git", ".venv", "__pycache__", ".cache", "output", "outputs", "work"}


def result(check: str, passed: bool, detail: str) -> dict[str, str]:
    return {"check": check, "status": "pass" if passed else "fail", "detail": detail}


def relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def is_within_repo(path: Path) -> bool:
    try:
        path.resolve().relative_to(REPO.resolve())
        return True
    except ValueError:
        return False


def prohibited_hits(text: str) -> list[str]:
    return [label for label, pattern in PROHIBITED_PATTERNS.items() if pattern.search(text)]


def load_catalog() -> tuple[dict[str, Any] | None, list[dict[str, str]]]:
    if not CATALOG_PATH.is_file():
        return None, [result("catalog:exists", False, relative(CATALOG_PATH))]
    try:
        catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        return None, [result("catalog:json", False, f"{type(exc).__name__}: {exc}")]
    if not isinstance(catalog, dict):
        return None, [result("catalog:json", False, "top-level JSON value must be an object")]
    return catalog, [result("catalog:json", True, relative(CATALOG_PATH))]


def chapter_number(chapter: dict[str, Any]) -> int | None:
    value = chapter.get("number")
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    match = re.fullmatch(r"(?:ch)?0*(\d{1,2})", str(value or ""), re.IGNORECASE)
    return int(match.group(1)) if match else None


def extension_chapters(catalog: dict[str, Any]) -> list[dict[str, Any]]:
    extension = catalog.get("extension", {})
    if isinstance(extension, dict):
        chapters = extension.get("chapters", [])
    elif isinstance(extension, list):
        chapters = extension
    else:
        chapters = []
    return [item for item in chapters if isinstance(item, dict)] if isinstance(chapters, list) else []


def validate_catalog(catalog: dict[str, Any]) -> list[dict[str, str]]:
    checks: list[dict[str, str]] = []
    required_top_keys = {"schemaVersion", "repository", "environment", "days", "extension"}
    checks.append(
        result(
            "catalog:schema_keys",
            required_top_keys.issubset(catalog),
            f"keys={sorted(catalog)}",
        )
    )

    repository_text = json.dumps(catalog.get("repository"), ensure_ascii=False)
    checks.append(
        result(
            "catalog:public_student_repository",
            EXPECTED_REPO_SLUG in repository_text
            and EXPECTED_BRANCH in repository_text
            and "instructor" not in repository_text.lower(),
            repository_text,
        )
    )

    days = catalog.get("days", [])
    days = [day for day in days if isinstance(day, dict)] if isinstance(days, list) else []
    actual_routes = ["/" + str(day.get("route", "")).strip("/") + "/" for day in days]
    expected_day_routes = [f"/day-{index}/" for index in range(1, 6)]
    checks.append(
        result(
            "catalog:five_days",
            len(days) == 5 and actual_routes == expected_day_routes,
            f"count={len(days)}; routes={actual_routes}",
        )
    )

    daily_chapters: list[dict[str, Any]] = []
    day_mapping: dict[str, list[int | None]] = {}
    day_fields_ok = True
    for index, day in enumerate(days, start=1):
        chapters = day.get("chapters", [])
        chapters = [item for item in chapters if isinstance(item, dict)] if isinstance(chapters, list) else []
        daily_chapters.extend(chapters)
        day_mapping[f"day-{index}"] = [chapter_number(chapter) for chapter in chapters]
        day_fields_ok = day_fields_ok and all(
            bool(str(day.get(field, "")).strip()) for field in ("id", "route", "label", "title", "summary")
        )
    expected_day_mapping = {
        f"day-{day}": list(range((day - 1) * 3 + 1, day * 3 + 1)) for day in range(1, 6)
    }
    checks.append(result("catalog:day_fields", day_fields_ok, "all five day records have id/route/label/title/summary"))
    checks.append(
        result(
            "catalog:chapters_01_15_by_day",
            day_mapping == expected_day_mapping,
            json.dumps(day_mapping, ensure_ascii=False),
        )
    )

    extra_chapters = extension_chapters(catalog)
    extension_numbers = [chapter_number(chapter) for chapter in extra_chapters]
    extension_value = catalog.get("extension", {})
    raw_extension_route = extension_value.get("route") if isinstance(extension_value, dict) else None
    extension_route = "/" + str(raw_extension_route or "").strip("/") + "/"
    checks.append(
        result(
            "catalog:chapters_16_18_extension",
            extension_numbers == [16, 17, 18] and extension_route == "/extension/",
            f"route={extension_route}; chapters={extension_numbers}",
        )
    )

    all_chapters = daily_chapters + extra_chapters
    numbers = [chapter_number(chapter) for chapter in all_chapters]
    checks.append(
        result(
            "catalog:eighteen_unique_chapters",
            numbers == list(range(1, 19)) and len(set(numbers)) == 18,
            f"count={len(numbers)}; numbers={numbers}",
        )
    )

    chapter_fields_ok = True
    handouts: list[str] = []
    notebook_paths: list[str] = []
    colab_urls: list[str] = []
    for chapter in all_chapters:
        compute = chapter.get("compute", {})
        notebooks = chapter.get("notebooks", [])
        if not isinstance(compute, dict) or not isinstance(notebooks, list):
            chapter_fields_ok = False
            continue
        chapter_fields_ok = chapter_fields_ok and all(
            bool(str(chapter.get(field, "")).strip()) for field in ("title", "outcome", "handout")
        )
        chapter_fields_ok = chapter_fields_ok and all(
            bool(str(compute.get(field, "")).strip()) for field in ("runtime", "duration", "mode")
        )
        handouts.append(str(chapter.get("handout", "")))
        for notebook in notebooks:
            if not isinstance(notebook, dict):
                chapter_fields_ok = False
                continue
            chapter_fields_ok = chapter_fields_ok and all(
                bool(str(notebook.get(field, "")).strip()) for field in ("label", "path", "colab")
            )
            notebook_paths.append(str(notebook.get("path", "")))
            colab_urls.append(str(notebook.get("colab", "")))
    checks.append(result("catalog:student_facing_fields", chapter_fields_ok, "chapter, compute, and notebook fields are populated"))

    expected_handouts = [f"handouts/ch{chapter:02d}.pdf" for chapter in range(1, 19)]
    normalized_handouts = [value.lstrip("./") for value in handouts]
    checks.append(
        result(
            "catalog:eighteen_handout_links",
            normalized_handouts == expected_handouts and len(set(normalized_handouts)) == 18,
            json.dumps(normalized_handouts, ensure_ascii=False),
        )
    )

    expected_paths = [f"notebooks/colab_ready/{filename}" for filename in EXPECTED_NOTEBOOKS]
    expected_colab_urls = [
        f"https://colab.research.google.com/github/{EXPECTED_REPO_SLUG}/blob/{EXPECTED_BRANCH}/{path}"
        for path in expected_paths
    ]
    checks.append(
        result(
            "catalog:twenty_six_notebook_paths",
            notebook_paths == expected_paths and len(set(notebook_paths)) == 26,
            f"count={len(notebook_paths)}; unique={len(set(notebook_paths))}",
        )
    )
    checks.append(
        result(
            "catalog:twenty_six_public_colab_links",
            colab_urls == expected_colab_urls and len(set(colab_urls)) == 26,
            f"count={len(colab_urls)}; unique={len(set(colab_urls))}",
        )
    )

    serialized = json.dumps(catalog, ensure_ascii=False)
    checks.append(result("catalog:no_day_6", not DAY6_PATTERN.search(serialized), "catalog contains no Day 6 marker"))
    hits = prohibited_hits(serialized)
    checks.append(
        result(
            "catalog:no_private_or_teacher_markers",
            not hits,
            "no prohibited marker" if not hits else f"matched={hits}",
        )
    )
    return checks


def validate_routes() -> list[dict[str, str]]:
    return [
        result(f"route:{route}", (DOCS / route).is_file(), relative(DOCS / route))
        for route in EXPECTED_ROUTES
    ]


def validate_build_boundaries() -> list[dict[str, str]]:
    checks: list[dict[str, str]] = []
    output_targets = [DOCS, CATALOG_PATH, HANDOUT_SOURCE_DIR, HANDOUT_PUBLIC_DIR, NOTEBOOK_DIR, REPORT_PATH]
    checks.append(
        result(
            "build_target:student_repo_root",
            REPO.name == EXPECTED_REPO_NAME and (REPO / ".git").exists(),
            f"repo={REPO.name}",
        )
    )
    checks.append(
        result(
            "build_target:all_paths_contained",
            all(is_within_repo(path) for path in output_targets),
            json.dumps([relative(path) for path in output_targets], ensure_ascii=False),
        )
    )
    builder = REPO / "scripts" / "build_student_handouts.py"
    builder_text = builder.read_text(encoding="utf-8") if builder.is_file() else ""
    containment_markers = (
        EXPECTED_REPO_NAME in builder_text
        and "resolve" in builder_text
        and ("relative_to" in builder_text or "is_relative_to" in builder_text)
        and "docs" in builder_text
        and "handouts" in builder_text
        and 'REPO_ROOT.name != "python-machine-learning-2026-student"' in builder_text
    )
    checks.append(result("build_target:handout_builder_exists", builder.is_file(), relative(builder)))
    checks.append(
        result(
            "build_target:builder_containment_guard",
            containment_markers,
            "builder pins the student repo and rejects output outside it",
        )
    )
    return checks


def validate_notebook_files() -> list[dict[str, str]]:
    checks: list[dict[str, str]] = []
    actual = sorted(path.name for path in NOTEBOOK_DIR.glob("*.ipynb")) if NOTEBOOK_DIR.is_dir() else []
    expected = sorted(EXPECTED_NOTEBOOKS)
    checks.append(
        result(
            "notebooks:twenty_six_files",
            actual == expected,
            f"count={len(actual)}; missing={sorted(set(expected) - set(actual))}; extra={sorted(set(actual) - set(expected))}",
        )
    )
    valid = []
    errors = []
    for filename in EXPECTED_NOTEBOOKS:
        path = NOTEBOOK_DIR / filename
        if not path.is_file():
            continue
        try:
            notebook = json.loads(path.read_text(encoding="utf-8"))
            if notebook.get("nbformat") == 4 and isinstance(notebook.get("cells"), list):
                valid.append(filename)
            else:
                errors.append(f"{filename}: invalid nbformat/cells")
        except Exception as exc:
            errors.append(f"{filename}: {type(exc).__name__}: {exc}")
    checks.append(
        result(
            "notebooks:valid_nbformat4",
            len(valid) == 26 and not errors,
            f"valid={len(valid)}" if not errors else "; ".join(errors),
        )
    )
    return checks


def public_text_files() -> list[Path]:
    paths = [
        *DOCS.rglob("*.html"),
        *DOCS.rglob("*.json"),
        *DOCS.rglob("*.js"),
    ]
    return sorted({path.resolve() for path in paths if path.is_file()})


def validate_public_text() -> list[dict[str, str]]:
    files = public_text_files()
    private_hits: list[str] = []
    day6_hits: list[str] = []
    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        hits = prohibited_hits(text)
        if hits:
            private_hits.append(f"{relative(path)}: {', '.join(hits)}")
        if DAY6_PATTERN.search(text):
            day6_hits.append(relative(path))
    supplemental_files = [
        path
        for path in [REPO / "README.md", REPO / "COURSE_MAP.md", *HANDOUT_SOURCE_DIR.glob("*.md")]
        if path.is_file()
    ]
    boundary_labels = {
        "instructor repository",
        "instructor repository slug",
        "teacher workflow",
        "local file URL",
    }
    supplemental_hits: list[str] = []
    for path in supplemental_files:
        text = path.read_text(encoding="utf-8", errors="replace")
        hits = [
            label
            for label, pattern in PROHIBITED_PATTERNS.items()
            if label in boundary_labels and pattern.search(text)
        ]
        if hits:
            supplemental_hits.append(f"{relative(path)}: {', '.join(hits)}")
    return [
        result(
            "public_source:scanned_files",
            len(files) >= 8,
            f"files={len(files)} (public HTML/JSON/JS)",
        ),
        result(
            "public_source:no_private_or_teacher_markers",
            not private_hits,
            "no prohibited marker" if not private_hits else "; ".join(private_hits),
        ),
        result(
            "public_source:no_day_6",
            not day6_hits,
            "no Day 6 marker" if not day6_hits else f"files={day6_hits}",
        ),
        result(
            "public_docs:no_private_repo_workflow_or_local_path",
            not supplemental_hits,
            "README, course map, and student Markdown contain no private boundary leak"
            if not supplemental_hits
            else "; ".join(supplemental_hits),
        ),
    ]


def validate_submission_text_boundaries() -> list[dict[str, str]]:
    """Scan commit-facing text without copying sensitive matches into the report."""
    files = sorted(
        path
        for path in REPO.rglob("*")
        if path.is_file()
        and path.suffix.lower() in SUBMISSION_TEXT_SUFFIXES
        and not any(part in SUBMISSION_EXCLUDED_DIRS for part in path.relative_to(REPO).parts)
    )
    hits: list[str] = []
    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        for label, pattern in SUBMISSION_BOUNDARY_PATTERNS.items():
            match = pattern.search(text)
            if match:
                line_number = text.count("\n", 0, match.start()) + 1
                hits.append(f"{relative(path)}:{line_number}: {label}")
    return [
        result(
            "submission_text:no_local_or_private_paths",
            not hits,
            f"scanned={len(files)}; no user profile path, local file URL, or private repo slug"
            if not hits
            else "; ".join(hits),
        )
    ]


def load_pdf_reader() -> tuple[Callable[[str], Any] | None, str]:
    try:
        from pypdf import PdfReader

        return PdfReader, "pypdf"
    except ImportError:
        try:
            from PyPDF2 import PdfReader

            return PdfReader, "PyPDF2"
        except ImportError:
            return None, "Install scripts/build_student_handouts.requirements.txt or run with the bundled Codex Python."


def handout_report_evidence(expected_pdfs: list[Path]) -> tuple[bool, str]:
    """Accept prior extraction only when its SHA-256 rows match every current PDF."""
    if not HANDOUT_REPORT_PATH.is_file():
        return False, f"missing {relative(HANDOUT_REPORT_PATH)}"
    try:
        report = json.loads(HANDOUT_REPORT_PATH.read_text(encoding="utf-8"))
        rows = report.get("chapters", [])
        by_pdf = {str(row.get("pdf")): row for row in rows if isinstance(row, dict)}
        problems: list[str] = []
        for path in expected_pdfs:
            key = relative(path)
            row = by_pdf.get(key)
            if row is None or not path.is_file():
                problems.append(f"{key}: missing evidence")
                continue
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if row.get("pdf_sha256") != digest:
                problems.append(f"{key}: checksum changed")
            if int(row.get("extracted_chars", 0)) < 80:
                problems.append(f"{key}: extracted text too short")
        scan = report.get("scan", {})
        if report.get("status") != "PASS":
            problems.append("handout report status is not PASS")
        if scan.get("pdf_text_findings") != 0:
            problems.append("handout report has PDF text findings")
        if len(rows) != 18:
            problems.append(f"handout report rows={len(rows)}")
        return not problems, (
            "18 current PDF checksums match the pypdf extraction report"
            if not problems
            else "; ".join(problems)
        )
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"


def validate_handouts() -> list[dict[str, str]]:
    checks: list[dict[str, str]] = []
    expected_sources = [HANDOUT_SOURCE_DIR / f"ch{chapter:02d}.md" for chapter in range(1, 19)]
    expected_pdfs = [HANDOUT_PUBLIC_DIR / f"ch{chapter:02d}.pdf" for chapter in range(1, 19)]
    actual_sources = sorted(path.name for path in HANDOUT_SOURCE_DIR.glob("ch*.md")) if HANDOUT_SOURCE_DIR.is_dir() else []
    actual_pdfs = sorted(path.name for path in HANDOUT_PUBLIC_DIR.glob("ch*.pdf")) if HANDOUT_PUBLIC_DIR.is_dir() else []
    checks.append(
        result(
            "handouts:eighteen_student_sources",
            actual_sources == [path.name for path in expected_sources]
            and all(path.stat().st_size > 0 for path in expected_sources if path.is_file()),
            f"count={len(actual_sources)}",
        )
    )
    checks.append(
        result(
            "handouts:eighteen_public_pdfs",
            actual_pdfs == [path.name for path in expected_pdfs],
            f"count={len(actual_pdfs)}",
        )
    )

    header_failures: list[str] = []
    for path in expected_pdfs:
        if not path.is_file():
            header_failures.append(f"{path.name}: missing")
            continue
        if path.stat().st_size <= 1024 or path.read_bytes()[:5] != b"%PDF-":
            header_failures.append(f"{path.name}: size={path.stat().st_size}, header={path.read_bytes()[:5]!r}")
    checks.append(
        result(
            "handouts:pdf_header_and_nonzero",
            not header_failures,
            "18 PDFs have a PDF header and non-trivial size" if not header_failures else "; ".join(header_failures),
        )
    )

    reader_factory, reader_name = load_pdf_reader()
    report_evidence_ok, report_evidence_detail = handout_report_evidence(expected_pdfs)
    extractor_available = reader_factory is not None or report_evidence_ok
    extractor_detail = reader_name if reader_factory is not None else report_evidence_detail
    checks.append(result("handouts:pdf_text_extractor", extractor_available, extractor_detail))
    extraction_failures: list[str] = []
    prohibited_pdf_hits: list[str] = []
    if reader_factory is not None:
        for path in expected_pdfs:
            if not path.is_file():
                extraction_failures.append(f"{path.name}: missing")
                continue
            try:
                reader = reader_factory(str(path))
                text = "\n".join((page.extract_text() or "") for page in reader.pages)
            except Exception as exc:
                extraction_failures.append(f"{path.name}: {type(exc).__name__}: {exc}")
                continue
            if len(text.strip()) < 80:
                extraction_failures.append(f"{path.name}: extracted_chars={len(text.strip())}")
            hits = prohibited_hits(text)
            if hits:
                prohibited_pdf_hits.append(f"{path.name}: {', '.join(hits)}")
            if DAY6_PATTERN.search(text):
                prohibited_pdf_hits.append(f"{path.name}: Day 6 marker")
    extraction_ok = not extraction_failures and extractor_available
    prohibited_ok = not prohibited_pdf_hits and extractor_available
    checks.append(
        result(
            "handouts:pdf_text_extractable",
            extraction_ok,
            "18 PDFs contain extractable text"
            if extraction_ok
            else "; ".join(extraction_failures) or report_evidence_detail,
        )
    )
    checks.append(
        result(
            "handouts:pdf_no_private_teacher_or_day6_markers",
            prohibited_ok,
            "extracted PDF text contains no prohibited marker"
            if prohibited_ok
            else "; ".join(prohibited_pdf_hits) or report_evidence_detail,
        )
    )
    return checks


def main() -> int:
    checks: list[dict[str, str]] = []
    checks.extend(validate_build_boundaries())
    checks.extend(validate_routes())
    catalog, catalog_checks = load_catalog()
    checks.extend(catalog_checks)
    if catalog is not None:
        checks.extend(validate_catalog(catalog))
    checks.extend(validate_notebook_files())
    checks.extend(validate_public_text())
    checks.extend(validate_submission_text_boundaries())
    checks.extend(validate_handouts())

    failures = [check for check in checks if check["status"] == "fail"]
    report = {
        "status": "pass" if not failures else "fail",
        "checked_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "scope": (
            "Static validation of the public student course portal, catalog, Colab links, "
            "student handouts, PDF text, and repository output boundaries. Browser behavior "
            "and fresh Colab execution are separate checks."
        ),
        "summary": {
            "total": len(checks),
            "passed": len(checks) - len(failures),
            "failed": len(failures),
        },
        "checks": checks,
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(report["summary"], ensure_ascii=False))
    if failures:
        for failure in failures:
            print("FAIL", failure["check"], "-", failure["detail"])
        print("Report:", relative(REPORT_PATH))
        return 1
    print("PASS - public student course portal static validation")
    print("Report:", relative(REPORT_PATH))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
