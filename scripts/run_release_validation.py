#!/usr/bin/env python3
"""Validate the curated release without rerunning the 53 x 3 algorithms."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_HASHES = {
    "artifacts/paper_v1/scores/main_five_methods_pool_scores.csv": "d858fe4d28f36f750113dbdff35432159b81e539cd1541c442d3db3f459bad9b",
    "artifacts/paper_v1/scores/recent_three_methods_pool_scores.csv": "206d81898d43cc65086b7e41ab1e95af174196409d20d60bf8fc54ff7cfdfc36",
    "artifacts/paper_v1/scores/fixed_strength_ablation_pool_scores.csv": "f67da40439f9715f73ae8c07ec1f349f8baf847611df07e2ef6473c2f9fab1f0",
    "configs/frozen/main_methods.json": "0ce099c475abba98b932bf9d4ad64489a8918557e780c79d4accb0fdaf14c2be",
    "configs/frozen/recent_baselines.json": "ab21598e0d880523f64fefc4f29984dfeaaf94d462764fdb7703dda8dcdc4606",
    "figures/data/plotted_grid_acc_nmi.csv": "433fd500fa5e34b49e3ebe188eba5cf093de9b8afe927c88781ac573f4764591",
}
TEXT_SUFFIXES = {".py", ".md", ".json", ".toml", ".txt", ".csv", ".yml", ".yaml", ".m"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command: list[str], cwd: Path) -> dict:
    env = dict(os.environ)
    env["MPLBACKEND"] = "Agg"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run(command, cwd=cwd, text=True, capture_output=True, env=env)
    python_env = Path(sys.executable).resolve().parents[1]
    def sanitize(value: str) -> str:
        return value.replace(str(ROOT), "<RELEASE_ROOT>").replace(str(python_env), "<PYTHON_ENV>")
    return {
        "returncode": completed.returncode,
        "stdout_tail": sanitize(completed.stdout[-3000:]),
        "stderr_tail": sanitize(completed.stderr[-3000:]),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "VALIDATION_REPORT.json")
    parser.add_argument("--portable-extraction-check", action="store_true")
    args = parser.parse_args()

    pytest_result = run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"], ROOT)
    import_result = run([sys.executable, "-c", "import psfce; assert psfce.__version__ == '1.0.0'"], ROOT)

    with tempfile.TemporaryDirectory(prefix="psfce-rebuild-") as directory:
        rebuild_dir = Path(directory)
        rebuild_result = run(
            [sys.executable, "scripts/rebuild_paper_artifacts.py", "--output", str(rebuild_dir)],
            ROOT,
        )
        table_outputs = [
            rebuild_dir / "main_summary_53datasets.csv",
            rebuild_dir / "main_dataset_means_53x8.csv",
            rebuild_dir / "ablation_summary.csv",
            rebuild_dir / "main_summary.tex",
        ]
        figure_output = rebuild_dir / "psf_acc_nmi_rebuilt.pdf"
        tables_ok = rebuild_result["returncode"] == 0 and all(path.is_file() for path in table_outputs)
        figure_ok = rebuild_result["returncode"] == 0 and figure_output.is_file() and figure_output.stat().st_size > 0

    main_scores = pd.read_csv(ROOT / "artifacts/paper_v1/scores/main_five_methods_pool_scores.csv")
    recent_scores = pd.read_csv(ROOT / "artifacts/paper_v1/scores/recent_three_methods_pool_scores.csv")
    ablation = pd.read_csv(ROOT / "artifacts/paper_v1/scores/fixed_strength_ablation_pool_scores.csv")
    main_methods = json.loads((ROOT / "configs/frozen/main_methods.json").read_text(encoding="utf-8"))
    registry = json.loads((ROOT / "configs/recent_baselines_registry.json").read_text(encoding="utf-8"))["methods"]
    repo_config = json.loads((ROOT / "configs/official_repositories.json").read_text(encoding="utf-8"))

    main_coverage = (
        set(main_scores.method) == {"CA", "Poly2", "LinearPair", "AggregatePower", "PSF-CE"}
        and main_scores.groupby("method").size().eq(159).all()
        and not main_scores.duplicated(["dataset", "pool", "method"]).any()
    )
    recent_coverage = (
        set(recent_scores.method) == {"CEHM", "YACHT", "RANGE"}
        and recent_scores.groupby("method").size().eq(159).all()
        and not recent_scores.duplicated(["dataset", "pool", "method"]).any()
    )
    ablation_coverage = (
        len(ablation) == 477
        and ablation.variant.nunique() == 3
        and ablation.groupby("variant").size().eq(159).all()
        and not ablation.duplicated(["dataset", "pool", "variant"]).any()
    )
    frozen_psf = main_methods["methods"]["PSF-CE"]
    frozen_ok = frozen_psf == {"lambda": 0.665, "q": 0.72}
    defaults_ok = set(registry) == {"CEHM", "YACHT", "RANGE"} == set(repo_config)
    hash_results = {path: sha256(ROOT / path) for path in EXPECTED_HASHES}
    hashes_ok = hash_results == EXPECTED_HASHES

    forbidden_names = {".git", ".venv", "__pycache__", ".pytest_cache", "runtime_results", "vendor"}
    forbidden_paths = [
        path.relative_to(ROOT).as_posix()
        for path in ROOT.rglob("*")
        if path.name in forbidden_names
    ]
    secret_patterns = [
        re.compile(r"ghp_[A-Za-z0-9]{20,}"),
        re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
        re.compile(r"AKIA[0-9A-Z]{16}"),
        re.compile(r"C:\\Users\\[^\\\s]+", re.IGNORECASE),
    ]
    sensitive_files: set[str] = set()
    historical_names: set[str] = set()
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if path.name in {"RELEASE_MANIFEST.json", "SHA256SUMS.txt", "VALIDATION_REPORT.json"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        relative = path.relative_to(ROOT).as_posix()
        if any(pattern.search(text) for pattern in secret_patterns):
            sensitive_files.add(relative)
        if ("SA-" + "CSI") in text or ("DC" + "KL") in text:
            historical_names.add(relative)
    security_ok = not forbidden_paths and not sensitive_files
    sanitation_ok = not historical_names

    report = {
        "schema": "psfce-release-validation-v2",
        "release_version": "1.0.0",
        "scope_statement": "Packaging and recorded-score reconstruction only; the 53x3 algorithms were not rerun.",
        "packaging_checks": {
            "status": "PASS" if security_ok and sanitation_ok else "FAIL",
            "forbidden_paths": sorted(forbidden_paths),
            "sensitive_file_count": len(sensitive_files),
            "sensitive_files": sorted(sensitive_files),
            "historical_public_name_hits": sorted(historical_names),
            "portable_extraction": "PASS" if args.portable_extraction_check else "NOT_VERIFIED",
        },
        "python_tests": {
            "status": "PASS" if pytest_result["returncode"] == 0 else "FAIL",
            "command": "python -m pytest -q -p no:cacheprovider",
            "result": pytest_result,
            "import_status": "PASS" if import_result["returncode"] == 0 else "FAIL",
        },
        "table_rebuild": {
            "status": "PASS" if tables_ok else "FAIL",
            "recorded_score_rows": {"main_internal": len(main_scores), "recent": len(recent_scores), "ablation": len(ablation)},
            "algorithm_executed": False,
            "metrics_recomputed_from_labels": False,
            "result": rebuild_result,
        },
        "figure_rebuild": {
            "status": "PASS" if figure_ok else "FAIL",
            "source": "archived aggregated parameter-grid values",
            "vector_pdf_created": figure_ok,
        },
        "frozen_config_checks": {
            "status": "PASS" if frozen_ok and defaults_ok else "FAIL",
            "psfce": frozen_psf,
            "paper_default_recent_baselines": sorted(registry),
            "bootstrap_default_repositories": sorted(repo_config),
            "main_score_coverage": "PASS" if main_coverage else "FAIL",
            "recent_score_coverage": "PASS" if recent_coverage else "FAIL",
            "fixed_strength_ablation_coverage": "PASS" if ablation_coverage else "FAIL",
            "archived_hashes": hash_results,
            "archived_hash_status": "PASS" if hashes_ok else "FAIL",
        },
        "data_provenance_checks": {
            "status": "NOT_VERIFIED",
            "detail": "Portable manifests and archived hashes were checked, but data/BP redistribution rights and historical input identity remain author-review items.",
        },
        "third_party_license_checks": {
            "status": "NOT_VERIFIED",
            "detail": "Pinned repositories are documented as NOASSERTION and are not vendored; redistribution permission still requires confirmation.",
        },
        "matlab_execution_verified": {
            "status": "NOT_VERIFIED",
            "detail": "No MATLAB baseline or 53x3 algorithm was rerun during release sanitation.",
        },
        "skipped_checks": [
            "fresh 53x3 PSF-CE rerun",
            "fresh CEHM/YACHT/RANGE MATLAB rerun",
            "metric recomputation from raw labels and predictions",
            "dataset and BP redistribution license adjudication",
        ],
        "blockers": [
            "project license and contributor authorization are not selected",
            "public author/publication metadata are not finalized",
            "data and BP redistribution rights are not confirmed",
            "third-party repositories remain NOASSERTION",
        ],
        "release_status": {
            "private_repository": "READY_FOR_PRIVATE_REPOSITORY",
            "public_release": "NOT_READY_FOR_PUBLIC_RELEASE",
        },
    }
    required_passes = [
        report["packaging_checks"]["status"],
        report["python_tests"]["status"],
        report["python_tests"]["import_status"],
        report["table_rebuild"]["status"],
        report["figure_rebuild"]["status"],
        report["frozen_config_checks"]["status"],
    ]
    report["validation_status"] = "PASS" if set(required_passes) == {"PASS"} else "FAIL"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    raise SystemExit(0 if report["validation_status"] == "PASS" else 2)


if __name__ == "__main__":
    main()
