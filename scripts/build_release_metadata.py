#!/usr/bin/env python3
"""Refresh the release manifest and SHA-256 list deterministically."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "RELEASE_MANIFEST.json"
SUMS = ROOT / "SHA256SUMS.txt"
EXCLUDE_FROM_MANIFEST = {"RELEASE_MANIFEST.json", "SHA256SUMS.txt"}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def default_metadata(relative: str) -> dict:
    if relative.startswith("artifacts/paper_v1/"):
        phase, role = "paper_v1", "paper_artifact"
    elif relative.startswith("tests/"):
        phase, role = "validation", "regression_test"
    elif relative.startswith("scripts/"):
        phase, role = "release_packaging", "execution_or_validation_script"
    elif relative.startswith("configs/"):
        phase, role = "release_packaging", "configuration"
    elif relative.startswith("psfce/"):
        phase, role = "implementation", "python_source"
    else:
        phase, role = "release_packaging", "release_file"
    return {
        "experiment_phase": phase,
        "role": role,
        "source_id": "RELEASE_GENERATED_OR_CURATED",
        "source_sha256": None,
        "transformation": "release_sanitation_or_byte_copy",
    }


def main() -> None:
    old = {}
    if MANIFEST.exists():
        old_payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
        old = {entry["path"]: entry for entry in old_payload.get("files", [])}
    files = []
    for path in sorted(p for p in ROOT.rglob("*") if p.is_file()):
        relative = path.relative_to(ROOT).as_posix()
        if relative in EXCLUDE_FROM_MANIFEST or any(part in {"__pycache__", ".pytest_cache"} for part in path.parts):
            continue
        metadata = {key: value for key, value in old.get(relative, default_metadata(relative)).items() if key not in {"path", "bytes", "sha256"}}
        files.append({"path": relative, "bytes": path.stat().st_size, "sha256": digest(path), **metadata})
    payload = {
        "schema": "psfce-github-release-manifest-v2",
        "release_version": "1.0.0",
        "status": "READY_FOR_PRIVATE_REPOSITORY",
        "public_release_status": "NOT_READY_FOR_PUBLIC_RELEASE",
        "algorithm_core_modified": False,
        "release_sanitation": {
            "inactive_historical_dispatch_removed": True,
            "paper_default_recent_baselines": ["CEHM", "YACHT", "RANGE"],
            "experimental_adapter_not_in_defaults": ["AWEC"],
            "bootstrap_default_config_fixed": True,
            "archived_scores_modified": False,
        },
        "paper_methods": ["CA", "Poly2", "LinearPair", "AggregatePower", "CEHM", "YACHT", "RANGE", "PSF-CE"],
        "completed_recent_baselines": ["CEHM", "YACHT", "RANGE"],
        "manifest_excludes": sorted(EXCLUDE_FROM_MANIFEST),
        "files": files,
    }
    MANIFEST.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    checksum_files = sorted(p for p in ROOT.rglob("*") if p.is_file() and p != SUMS and all(part not in {"__pycache__", ".pytest_cache"} for part in p.parts))
    lines = [f"{digest(path)}  {path.relative_to(ROOT).as_posix()}" for path in checksum_files]
    SUMS.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"manifest_files": len(files), "checksum_files": len(lines)}, indent=2))


if __name__ == "__main__":
    main()
