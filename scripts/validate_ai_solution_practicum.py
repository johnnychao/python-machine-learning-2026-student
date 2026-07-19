from __future__ import annotations

import ast
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[1]
NOTEBOOK_DIR = REPO / "notebooks" / "ai_solution_practicum"
MANIFEST_PATH = REPO / "data" / "ai_solution_practicum" / "datasets.json"
PRACTICE_DIR = REPO / "practice" / "ai_solution_practicum"
PUBLIC_PAGE = REPO / "docs" / "index.html"
PUBLIC_STYLE = REPO / "docs" / "assets" / "styles.css"
PUBLIC_APP = REPO / "docs" / "assets" / "app.js"
PUBLIC_AUDIO = REPO / "docs" / "assets" / "cinematic-audio.js"
PUBLIC_SCORE = REPO / "docs" / "assets" / "audio" / "snow-globe-bobjt-cc0-v1.mp3"
PUBLIC_SCORE_LICENSE = REPO / "docs" / "assets" / "audio" / "SNOW_GLOBE_LICENSE.txt"
REPORT_PATH = REPO / "reports" / "ai_solution_practicum_validation.json"
EXPECTED_SCORE_SHA256 = "5061c178b57c54ae0e5741290fce101a1164851b71d6d6ca6f8b08d44d07aaf5"

EXPECTED_NOTEBOOKS = [
    "00_colab_ready.ipynb",
    "01_cnn_pet_story.ipynb",
    "02_rnn_message_story.ipynb",
    "03_style_transfer_story.ipynb",
    "04_rl_strategy_story.ipynb",
]

REQUIRED_FILES = [
    REPO / "AI_SOLUTION_PRACTICUM.md",
    MANIFEST_PATH,
    PUBLIC_PAGE,
    PUBLIC_STYLE,
    PUBLIC_APP,
    PUBLIC_AUDIO,
    PUBLIC_SCORE,
    PUBLIC_SCORE_LICENSE,
]

BANNED_CODE_PATTERNS = {
    "kagglehub": re.compile(r"\bkagglehub\b", re.IGNORECASE),
    "dataset_download": re.compile(r"\bdataset_download\b", re.IGNORECASE),
    "competition_download": re.compile(r"\bcompetition_download\b", re.IGNORECASE),
    "KAGGLE_API_TOKEN": re.compile(r"\bKAGGLE_API_TOKEN\b", re.IGNORECASE),
    "kaggle_environments": re.compile(r"\bkaggle[_-]environments\b", re.IGNORECASE),
    "gradio": re.compile(r"\bgradio\b|\bimport\s+gradio\b|\bfrom\s+gradio\b", re.IGNORECASE),
}

KAGGLE_URL_PATTERN = re.compile(r"https?://(?:www\.)?kaggle\.com/", re.IGNORECASE)
DAY_MARKERS = [
    re.compile(r"\bday[\s_-]*0?6\b", re.IGNORECASE),
    re.compile(r"\bd6\b", re.IGNORECASE),
]
LOGIN_INSTRUCTION_PATTERNS = {
    "Kaggle token": re.compile(r"KAGGLE_API_TOKEN|kaggle\.json", re.IGNORECASE),
    "login command": re.compile(r"\b(?:kaggle|gh)\s+auth\s+login\b|\blog\s*in\b|\bsign\s*in\b", re.IGNORECASE),
    "Kaggle login instruction": re.compile(
        r"(?:請|先|需要|必須).{0,12}(?:登入|註冊).{0,12}Kaggle|"
        r"(?:登入|註冊).{0,12}Kaggle|建立.{0,12}Kaggle.{0,12}帳號|"
        r"Kaggle.{0,12}(?:Token|Secret)",
        re.IGNORECASE,
    ),
}
PROHIBITED_WEB_FONTS = re.compile(r"DFKai-SB|BiauKai|KaiTi|標楷體", re.IGNORECASE)

ALLOWED_KAGGLE_PROVENANCE_KEYS = {
    "provenance_url",
    "project_origin_url",
    "kaggle_url",
    "source_url",
    "canonical_task_url",
}


def result(check: str, passed: bool, detail: str) -> dict[str, str]:
    return {"check": check, "status": "pass" if passed else "fail", "detail": detail}


def source_text(cell: dict[str, Any]) -> str:
    source = cell.get("source", "")
    return "".join(source) if isinstance(source, list) else str(source)


def sanitized_python(source: str) -> tuple[str, list[str]]:
    kept: list[str] = []
    problems: list[str] = []
    for line_number, line in enumerate(source.splitlines(), start=1):
        stripped = line.lstrip()
        indent = len(line) - len(stripped)
        if stripped.startswith(("%", "!")):
            if indent:
                problems.append(f"indented IPython magic at line {line_number}: {stripped[:40]}")
            continue
        kept.append(line)
    return "\n".join(kept), problems


def contains_day_marker(text: str) -> bool:
    return any(pattern.search(text) for pattern in DAY_MARKERS)


def validate_notebook(path: Path) -> list[dict[str, str]]:
    checks: list[dict[str, str]] = []
    try:
        notebook = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return [result(f"notebook:{path.name}:json", False, f"{type(exc).__name__}: {exc}")]

    structural_ok = (
        notebook.get("nbformat") == 4
        and isinstance(notebook.get("cells"), list)
        and notebook.get("metadata", {}).get("kernelspec", {}).get("name") == "python3"
    )
    checks.append(
        result(
            f"notebook:{path.name}:structure",
            structural_ok,
            f"cells={len(notebook.get('cells', []))}, nbformat={notebook.get('nbformat')}",
        )
    )

    all_text: list[str] = []
    code_text: list[str] = []
    syntax_errors: list[str] = []
    forbidden_hits: list[str] = []
    kaggle_code_cells: list[int] = []
    credential_tags: list[int] = []

    for index, cell in enumerate(notebook.get("cells", [])):
        text = source_text(cell)
        all_text.append(text)
        tags = {str(tag).lower() for tag in cell.get("metadata", {}).get("tags", [])}
        if "credentials" in tags:
            credential_tags.append(index)

        if cell.get("cell_type") != "code":
            continue

        code_text.append(text)
        if KAGGLE_URL_PATTERN.search(text):
            kaggle_code_cells.append(index)
        for label, pattern in BANNED_CODE_PATTERNS.items():
            if pattern.search(text):
                forbidden_hits.append(f"cell {index}: {label}")

        python_source, magic_problems = sanitized_python(text)
        syntax_errors.extend(f"cell {index}: {problem}" for problem in magic_problems)
        try:
            ast.parse(python_source)
        except SyntaxError as exc:
            syntax_errors.append(f"cell {index}: line {exc.lineno}: {exc.msg}")

    checks.append(
        result(
            f"notebook:{path.name}:python_syntax",
            not syntax_errors,
            "all code cells compile after top-level magic removal"
            if not syntax_errors
            else "; ".join(syntax_errors),
        )
    )
    checks.append(
        result(
            f"notebook:{path.name}:no_forbidden_runtime_dependency",
            not forbidden_hits and not credential_tags,
            "no Kaggle runtime, credential, or Gradio dependency"
            if not forbidden_hits and not credential_tags
            else "; ".join(forbidden_hits + [f"cell {i}: credentials tag" for i in credential_tags]),
        )
    )
    checks.append(
        result(
            f"notebook:{path.name}:kaggle_urls_markdown_only",
            not kaggle_code_cells,
            "Kaggle URLs appear only as provenance in markdown"
            if not kaggle_code_cells
            else f"Kaggle URL found in code cells {kaggle_code_cells}",
        )
    )

    joined_text = "\n".join(all_text)
    checks.append(
        result(
            f"notebook:{path.name}:no_day_marker",
            not contains_day_marker(joined_text),
            "no extra-day marker",
        )
    )

    code_joined = "\n".join(code_text).lower()
    if path.name.startswith("01_"):
        scheme_ok = (
            "tf.keras.datasets.cifar10" in code_joined
            and "load_data" in code_joined
        )
        scheme_detail = "Keras CIFAR-10 download filtered to cat and dog classes"
    elif path.name.startswith("02_"):
        scheme_ok = (
            "startificial/twitter-nlp" in code_joined
            and "bb1c6925112f570ea0ca94c723ff8818cc642eed" in code_joined
            and ("read_csv" in code_joined or "get_file" in code_joined)
        )
        scheme_detail = "pinned Hugging Face disaster-tweet CSV"
    elif path.name.startswith("03_"):
        public_asset_markers = ("raw.githubusercontent.com", "github.io", "data/ai_solution_practicum/assets")
        scheme_ok = any(marker in code_joined for marker in public_asset_markers)
        scheme_detail = "course-created ImageGen assets loaded from a public project URL"
    elif path.name.startswith("04_"):
        scheme_ok = "valid_columns" in code_joined and "drop_piece" in code_joined and "kaggle" not in code_joined
        scheme_detail = "pure-Python Connect X simulator with no external data"
    else:
        scheme_ok = True
        scheme_detail = "preflight has no station data source"

    checks.append(result(f"notebook:{path.name}:runtime_data_scheme", scheme_ok, scheme_detail))

    outputs_empty = all(
        not cell.get("outputs")
        for cell in notebook.get("cells", [])
        if cell.get("cell_type") == "code"
    )
    checks.append(
        result(
            f"notebook:{path.name}:clean_outputs",
            outputs_empty,
            "student notebook ships without stale output",
        )
    )
    return checks


def manifest_sources(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    raw = manifest.get("datasets", manifest.get("sources", []))
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, dict)]
    if isinstance(raw, dict):
        return [dict(value, station=key) if isinstance(value, dict) else {"station": key} for key, value in raw.items()]
    return []


def kaggle_url_key_violations(value: Any, path: str = "") -> list[str]:
    violations: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            if isinstance(child, str) and KAGGLE_URL_PATTERN.search(child):
                if str(key).lower() not in ALLOWED_KAGGLE_PROVENANCE_KEYS:
                    violations.append(child_path)
            else:
                violations.extend(kaggle_url_key_violations(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            violations.extend(kaggle_url_key_violations(child, f"{path}[{index}]"))
    return violations


def validate_manifest() -> list[dict[str, str]]:
    checks: list[dict[str, str]] = []
    try:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        return [result("manifest:json", False, f"{type(exc).__name__}: {exc}")]

    sources = manifest_sources(manifest)
    by_station: dict[str, dict[str, Any]] = {}
    station_aliases = {
        "cnn": ("cnn",),
        "rnn": ("rnn",),
        "style": ("style", "gan"),
        "rl": ("rl",),
    }
    for source in sources:
        source_id = str(source.get("id", source.get("station", ""))).lower()
        for station, aliases in station_aliases.items():
            if any(source_id == alias or source_id.startswith(f"{alias}_") or alias in source_id for alias in aliases):
                by_station[station] = source
                break
    expected_stations = {"cnn", "rnn", "style", "rl"}
    checks.append(
        result(
            "manifest:four_stations",
            set(by_station) == expected_stations,
            f"stations={sorted(by_station)}",
        )
    )

    delivery_auth = manifest.get("delivery", {}).get("credentials_required") is False
    source_auth = bool(sources) and all(
        source.get("credentials_required", source.get("auth_required")) is False for source in sources
    )
    auth_ok = delivery_auth and source_auth
    checks.append(
        result(
            "manifest:no_auth_required",
            auth_ok,
            "delivery and every station declare credentials_required=false",
        )
    )

    provenance_ok = bool(sources) and all(str(source.get("project_origin", "")).strip() for source in sources)
    kaggle_role = str(manifest.get("delivery", {}).get("kaggle_role", ""))
    provenance_ok = provenance_ok and any(term in kaggle_role for term in ["出處", "脈絡", "來源"])
    checks.append(
        result(
            "manifest:kaggle_provenance",
            provenance_ok,
            "every station names its project origin and delivery limits Kaggle to provenance",
        )
    )

    key_violations = kaggle_url_key_violations(manifest)
    checks.append(
        result(
            "manifest:kaggle_urls_provenance_only",
            not key_violations,
            "Kaggle URLs are confined to provenance fields"
            if not key_violations
            else f"invalid fields={key_violations}",
        )
    )

    cnn_text = json.dumps(by_station.get("cnn", {}), ensure_ascii=False).lower()
    rnn_text = json.dumps(by_station.get("rnn", {}), ensure_ascii=False).lower()
    style_text = json.dumps(by_station.get("style", {}), ensure_ascii=False).lower()
    rl_text = json.dumps(by_station.get("rl", {}), ensure_ascii=False).lower()

    scheme_checks = {
        "cnn": (
            "keras.datasets.cifar10" in cnn_text
            and "cs.toronto.edu/~kriz/cifar-10-python.tar.gz" in cnn_text
        ),
        "rnn": (
            "startificial/twitter-nlp" in rnn_text
            and "bb1c6925112f570ea0ca94c723ff8818cc642eed" in rnn_text
        ),
        "style": (
            "kind\": \"course_asset" in style_text
            and "data/ai_solution_practicum/assets/style-content-coast.png" in style_text
            and "data/ai_solution_practicum/assets/style-reference-sea-wind.png" in style_text
            and "tfhub.dev/google/magenta/arbitrary-image-stylization-v1-256/2" in style_text
        ),
        "rl": (
            by_station.get("rl", {}).get("runtime_sources") == []
            and any(term in rl_text for term in ["純 python", "即時產生", "沒有外部資料集"])
        ),
    }
    for station, passed in scheme_checks.items():
        checks.append(result(f"manifest:{station}:runtime_scheme", passed, f"{station} no-login runtime source"))
    return checks


def validate_public_page() -> list[dict[str, str]]:
    if not PUBLIC_PAGE.is_file():
        return [result("public_page:exists", False, str(PUBLIC_PAGE))]

    html = PUBLIC_PAGE.read_text(encoding="utf-8")
    css = PUBLIC_STYLE.read_text(encoding="utf-8") if PUBLIC_STYLE.is_file() else ""
    app_js = PUBLIC_APP.read_text(encoding="utf-8") if PUBLIC_APP.is_file() else ""
    audio_js = PUBLIC_AUDIO.read_text(encoding="utf-8") if PUBLIC_AUDIO.is_file() else ""
    score_license = PUBLIC_SCORE_LICENSE.read_text(encoding="utf-8") if PUBLIC_SCORE_LICENSE.is_file() else ""
    public_source = "\n".join([html, css, app_js, audio_js])
    checks = [result("public_page:exists", True, str(PUBLIC_PAGE))]
    checks.append(
        result(
            "public_page:no_day_marker",
            not contains_day_marker(html),
            "public page contains no extra-day marker",
        )
    )
    login_hits = [label for label, pattern in LOGIN_INSTRUCTION_PATTERNS.items() if pattern.search(html)]
    checks.append(
        result(
            "public_page:no_login_instruction",
            not login_hits,
            "public page contains no account, token, secret, or login instruction"
            if not login_hits
            else f"matched={login_hits}",
        )
    )
    checks.append(
        result(
            "public_page:cinematic_structure",
            all(marker in html for marker in ["cinematic-site", "cinema-atmosphere", "data-scene=", "film-progress"]),
            "cinematic opening, scenes, atmosphere, and progress markers are present",
        )
    )
    checks.append(
        result(
            "public_page:no_prohibited_font",
            not PROHIBITED_WEB_FONTS.search(public_source),
            "web source contains no prohibited calligraphic font fallback",
        )
    )
    checks.append(
        result(
            "public_page:audio_opt_in",
            (
                html.count("data-sound-toggle") >= 2
                and "cinematic-audio.js" in html
                and '<audio id="cinematic-score" preload="none" loop hidden>' in html
                and "assets/audio/snow-globe-bobjt-cc0-v1.mp3" in html
                and "autoplay" not in public_source.lower()
                and 'data-sound="off"' in html
                and 'setUi("off"' in audio_js
                and "await audio.play()" in audio_js
                and 'addEventListener("click", handleToggle)' in audio_js
            ),
            "the local CC0 soundtrack defaults off and starts only from an explicit click",
        )
    )
    score_hash = hashlib.sha256(PUBLIC_SCORE.read_bytes()).hexdigest() if PUBLIC_SCORE.is_file() else "missing"
    checks.append(
        result(
            "public_page:score_asset_integrity",
            PUBLIC_SCORE.is_file()
            and PUBLIC_SCORE.stat().st_size == 1_735_492
            and score_hash == EXPECTED_SCORE_SHA256,
            f"size={PUBLIC_SCORE.stat().st_size if PUBLIC_SCORE.is_file() else 0}; sha256={score_hash}",
        )
    )
    checks.append(
        result(
            "public_page:score_license",
            all(
                marker in score_license
                for marker in [
                    "Track: Snow Globe",
                    "Author: Bobjt",
                    "License: Creative Commons CC0 1.0 Universal",
                    "https://opengameart.org/content/snow-globe",
                    EXPECTED_SCORE_SHA256,
                ]
            ),
            "track, author, source, CC0 license, and checksum are recorded",
        )
    )
    checks.append(
        result(
            "public_page:reduced_motion",
            "prefers-reduced-motion: reduce" in css
            and "animation: none !important" in css
            and "scroll-behavior: auto" in css,
            "cinematic effects expose a reduced-motion mode",
        )
    )
    return checks


def main() -> int:
    checks: list[dict[str, str]] = []

    for path in REQUIRED_FILES:
        checks.append(result(f"required_file:{path.relative_to(REPO).as_posix()}", path.is_file(), str(path)))

    for filename in EXPECTED_NOTEBOOKS:
        path = NOTEBOOK_DIR / filename
        checks.append(result(f"notebook:{filename}:exists", path.is_file(), str(path)))
        if path.is_file():
            checks.extend(validate_notebook(path))

    practice_files = sorted(path for path in PRACTICE_DIR.glob("*") if path.is_file()) if PRACTICE_DIR.is_dir() else []
    practice_ok = len(practice_files) >= 2 and all(path.stat().st_size > 0 for path in practice_files)
    checks.append(
        result(
            "practice:student_files",
            practice_ok,
            f"files={[path.name for path in practice_files]}; expected at least two non-empty files",
        )
    )

    if MANIFEST_PATH.is_file():
        checks.extend(validate_manifest())
    checks.extend(validate_public_page())

    failures = [check for check in checks if check["status"] == "fail"]
    report = {
        "status": "pass" if not failures else "fail",
        "checked_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "scope": "Static practicum validation; fresh Colab execution and remote URL availability remain separate checks.",
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
        print("Report:", REPORT_PATH)
        return 1

    print("PASS - AI solution practicum static validation")
    print("Report:", REPORT_PATH)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
