#!/usr/bin/env python
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.datasets import make_blobs

from psfce.external_baselines import load_external_registry, run_external_baseline
from psfce.metrics import evaluate_clustering


DEFAULTS = {
    "CEHM": {},
    "YACHT": {"theta": 0.4, "walk_order": 20, "anchor_offset": -1, "alpha": 0.95, "kmeans_replicates": 3},
    "RANGE": {"alpha": 0.8, "fuzzy_threshold": 0.8, "lambda": 0.5, "anchor_offset": -1, "kmeans_replicates": 3},
}


def heterogeneous_fixture():
    X, y = make_blobs(n_samples=300, centers=5, n_features=12, cluster_std=2.2, random_state=2027)
    ks = [4, 5, 6, 8, 10] * 4
    parts = []
    for index, k in enumerate(ks):
        parts.append(KMeans(n_clusters=k, n_init=3, random_state=1000 + index).fit_predict(X))
    return y, parts, ks


def main():
    parser = argparse.ArgumentParser(description="Run author-code smoke tests on a heterogeneous-k frozen BP fixture.")
    parser.add_argument("--registry", default="configs/recent_baselines_registry.json")
    parser.add_argument("--output", default="results/smoke/recent_baseline_smoke.csv")
    parser.add_argument("--cache-dir", default="results/smoke/cache")
    args = parser.parse_args()
    registry = load_external_registry(args.registry)
    y, parts, ks = heterogeneous_fixture()
    rows = []
    for method, params in DEFAULTS.items():
        result = run_external_baseline(
            registry[method], parts, 5, params, 2027, "heterogeneous_smoke", "0",
            cache_dir=args.cache_dir,
        )
        row = {
            "method": method,
            "status": result["status"],
            "runtime_seconds": result["runtime"],
            "error": result["error"],
            "n": 300,
            "c": 5,
            "M": 20,
            "k_values": json.dumps(ks),
            "bp_sha256": result["bp_sha256"],
            "commit": result["commit"],
        }
        if result["status"] == "ok":
            row.update(evaluate_clustering(y, result["labels"]))
        rows.append(row)
        print(method, row["status"], row["error"])
    frame = pd.DataFrame(rows)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output, index=False)
    passed = len(frame) == 3 and frame.status.eq("ok").all()
    report = {
        "schema": "psfce-release-v1-official-smoke",
        "passed": bool(passed),
        "fixture": {"n": 300, "c": 5, "M": 20, "k_values": ks},
        "csv": str(output),
    }
    output.with_suffix(".json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    raise SystemExit(0 if passed else 2)


if __name__ == "__main__":
    main()
