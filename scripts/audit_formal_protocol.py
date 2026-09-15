#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


REQUIRED_METHODS = {"CEHM", "YACHT", "RANGE"}


def main():
    parser = argparse.ArgumentParser(description="Post-run hard audit for the 53x3 frozen recent-baseline table.")
    parser.add_argument("--csv", required=True)
    parser.add_argument("--output", default="results/formal_protocol_audit.json")
    parser.add_argument("--expected-methods", nargs="+", default=sorted(REQUIRED_METHODS))
    args = parser.parse_args()
    frame = pd.read_csv(args.csv).fillna("")
    expected_methods = set(args.expected_methods)
    checks = []

    def add(code, passed, detail):
        checks.append({"code": code, "passed": bool(passed), "detail": str(detail)})

    add("methods_exact", set(frame.method) == expected_methods, sorted(set(frame.method)))
    add("all_rows_ok", len(frame) > 0 and frame.status.eq("ok").all(), frame.status.value_counts().to_dict())
    add("official_backend_only", set(frame.backend) <= {"matlab"}, sorted(set(frame.backend)))
    add("paper_default_methods_only", set(frame.method) == REQUIRED_METHODS, "formal CSV contains only completed paper-default recent baselines")
    expected_pairs = frame[["dataset", "pool"]].drop_duplicates()
    add("formal_shape", len(expected_pairs) == 159 and expected_pairs.dataset.nunique() == 53, f"pairs={len(expected_pairs)}, datasets={expected_pairs.dataset.nunique()}")
    counts = frame.groupby(["dataset", "pool"]).method.nunique()
    add("complete_method_coverage", len(counts) == 159 and counts.eq(len(expected_methods)).all(), counts.value_counts().to_dict())
    bp = frame.groupby(["dataset", "pool"]).bp_sha256.nunique()
    add("same_bp_hash", len(bp) == 159 and bp.eq(1).all(), bp.value_counts().to_dict())
    params = frame.groupby("method").params_sha256.nunique()
    add("globally_frozen_params", set(params.index) == expected_methods and params.eq(1).all(), params.to_dict())
    commits = frame.groupby("method").commit.nunique()
    add("one_commit_per_method", set(commits.index) == expected_methods and commits.eq(1).all(), commits.to_dict())
    add("provenance_complete", frame[["repo_url", "commit", "retrieval_date", "bp_sha256", "params_sha256"]].ne("").all().all(), "required provenance columns nonempty")
    duplicates = frame.duplicated(["dataset", "pool", "method"], keep=False)
    add("no_duplicate_rows", not duplicates.any(), f"duplicate_rows={int(duplicates.sum())}")

    passed = all(item["passed"] for item in checks)
    payload = {"schema": "psfce-release-v1-formal-protocol-audit", "passed": passed, "checks": checks}
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    raise SystemExit(0 if passed else 2)


if __name__ == "__main__":
    main()
