#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np

from psfce.dataio import load_manifest, load_pool_npz, validate_manifest
from psfce.external_baselines import find_matlab_executable, load_external_registry, verify_repository


REQUIRED = {"CEHM", "YACHT", "RANGE"}
RUNNABLE = set(REQUIRED)


def check(condition, code, detail, checks):
    checks.append({"code": code, "passed": bool(condition), "detail": str(detail)})


def main():
    parser = argparse.ArgumentParser(description="Submission hard gate for official recent baselines.")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--registry", default="configs/recent_baselines_registry.json")
    parser.add_argument("--output", default="results/preflight/BASELINE_PREFLIGHT.json")
    parser.add_argument("--require-formal-53x3", action="store_true")
    args = parser.parse_args()
    checks = []

    records = load_manifest(args.manifest)
    try:
        validate_manifest(records, require_disjoint=True, expected_M=20)
        check(True, "manifest_contract", "disjoint dev/formal; every pool has M=20", checks)
    except Exception as exc:
        check(False, "manifest_contract", exc, checks)

    formal = [r for r in records if r.split.lower() in {"formal", "test", "heldout"}]
    formal_names = {r.name for r in formal}
    pool_counts = {name: sum(r.name == name for r in formal) for name in formal_names}
    shape_ok = len(formal) == 159 and len(formal_names) == 53 and set(pool_counts.values()) == {3}
    check(shape_ok or not args.require_formal_53x3, "formal_shape", f"rows={len(formal)}, datasets={len(formal_names)}, pool_counts={sorted(set(pool_counts.values()))}", checks)

    registry = load_external_registry(args.registry)
    check(set(registry) == REQUIRED, "registry_method_set", sorted(registry), checks)
    check(all(spec.status == "enabled" for spec in registry.values()), "paper_default_enabled", "default registry contains enabled completed baselines only", checks)

    for name in sorted(RUNNABLE):
        spec = registry.get(name)
        if spec is None:
            check(False, f"repo_{name}", "missing registry entry", checks)
            continue
        try:
            info = verify_repository(spec)
            check(True, f"repo_{name}", f"commit={info['commit']}", checks)
        except Exception as exc:
            check(False, f"repo_{name}", exc, checks)

    try:
        matlab = find_matlab_executable()
        check(True, "matlab_available", matlab, checks)
    except Exception as exc:
        check(False, "matlab_available", exc, checks)

    # Inspect representative data without exporting y. Heterogeneous k_m is allowed and recorded.
    if records:
        y, parts = load_pool_npz(records[0].path)
        ks = [len(np.unique(p)) for p in parts]
        check(len(parts) == 20 and len(y) == len(parts[0]), "representative_pool", f"n={len(y)}, c={len(np.unique(y))}, M={len(parts)}, k_range=[{min(ks)},{max(ks)}]", checks)

    passed = all(item["passed"] for item in checks)
    payload = {
        "schema": "psfce-release-v1-baseline-preflight",
        "passed": passed,
        "manifest": str(Path(args.manifest).resolve()),
        "registry": str(Path(args.registry).resolve()),
        "checks": checks,
        "formal_execution_authorized": passed,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    md = ["# Baseline preflight", "", f"Overall: **{'PASS' if passed else 'BLOCKED'}**", ""]
    for item in checks:
        md.append(f"- [{'x' if item['passed'] else ' '}] `{item['code']}`: {item['detail']}")
    output.with_suffix(".md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))
    raise SystemExit(0 if passed else 2)


if __name__ == "__main__":
    main()
