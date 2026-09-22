from pathlib import Path

import pandas as pd

from psfce.reporting_v4 import build_final_report


def test_complete_report_uses_dataset_as_unit(tmp_path: Path):
    methods = ["PSF-CE", "CEHM", "YACHT", "RANGE"]
    rows = []
    for d in range(53):
        for pool in range(3):
            for j, method in enumerate(methods):
                score = 0.8 - 0.01 * j + 0.0001 * d
                rows.append({
                    "dataset": f"D{d:02d}", "pool": str(pool), "method": method,
                    "status": "ok", "ACC": score, "NMI": score - 0.1,
                    "ARI": score - 0.2, "F1": score - 0.05,
                    "runtime_seconds": 1.0 + j,
                })
    source = tmp_path / "merged.csv"
    pd.DataFrame(rows).to_csv(source, index=False)
    result = build_final_report(source, tmp_path / "report")
    assert set(result["methods"]) == set(methods)
    pairwise = pd.read_csv(tmp_path / "report" / "pairwise_wtl.csv")
    assert pairwise.n.eq(53).all()
    assert len(pairwise) == 3
    assert (tmp_path / "report" / "latex" / "table2_dataset_acc.tex").exists()
    assert (tmp_path / "report" / "fig1_rank_runtime.pdf").exists()
