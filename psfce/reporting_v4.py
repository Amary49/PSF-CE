from __future__ import annotations

from pathlib import Path
import json
import math

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import friedmanchisquare, studentized_range

from .metrics import bootstrap_mean_ci, holm_adjust, paired_wilcoxon
from .reporting import dataset_method_means


RECENT = ["CEHM", "YACHT", "RANGE", "AWEC"]
PRIMARY = "PSF-CE"


def merge_main_csv(psf_main, recent_main, output_csv):
    frames = []
    for path in (psf_main, recent_main):
        if path and Path(path).exists():
            frames.append(pd.read_csv(path))
    if not frames:
        raise FileNotFoundError("no main result CSV found")
    merged = pd.concat(frames, ignore_index=True, sort=False)
    keys = [c for c in ["dataset", "pool", "method", "params"] if c in merged.columns]
    if keys:
        merged = merged.drop_duplicates(keys, keep="last")
    Path(output_csv).parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(output_csv, index=False)
    return merged


def method_completion(frame: pd.DataFrame, expected_datasets=53, expected_pools=159) -> pd.DataFrame:
    rows = []
    for method in [PRIMARY] + RECENT:
        data = frame[frame.method == method]
        ok = data[data.status == "ok"] if "status" in data else data
        pairs = ok[["dataset", "pool"]].drop_duplicates() if {"dataset", "pool"} <= set(ok) else pd.DataFrame()
        datasets = ok.dataset.nunique() if "dataset" in ok else 0
        complete = datasets == expected_datasets and len(pairs) == expected_pools
        rows.append({
            "method": method,
            "complete": complete,
            "successful_rows": len(pairs),
            "expected_rows": expected_pools,
            "datasets": datasets,
            "reason": "" if complete else "未完成，不得参与比较",
        })
    return pd.DataFrame(rows)


def eligible_methods(frame: pd.DataFrame) -> tuple[list[str], pd.DataFrame]:
    completion = method_completion(frame)
    eligible = completion.loc[completion.complete, "method"].tolist()
    if PRIMARY not in eligible:
        raise ValueError("PSF-CE does not have complete 53x3 formal results")
    return eligible, completion


def rank_summary(frame: pd.DataFrame, methods: list[str]) -> pd.DataFrame:
    dm = dataset_method_means(frame)
    rows = []
    for metric in ["ACC", "NMI", "ARI", "F1"]:
        pivot = dm[dm.method.isin(methods)].pivot(index="dataset", columns="method", values=metric)
        if pivot.isna().any().any() or len(pivot) != 53:
            raise ValueError(f"{metric}: incomplete block for rank analysis")
        ranks = pivot.rank(axis=1, ascending=False, method="average")
        for method, value in ranks.mean().items():
            rows.append({"metric": metric, "method": method, "avg_rank": float(value), "n": len(pivot)})
    return pd.DataFrame(rows)


def friedman_nemenyi(frame: pd.DataFrame, methods: list[str], metric: str, alpha=0.05) -> dict:
    dm = dataset_method_means(frame)
    pivot = dm[dm.method.isin(methods)].pivot(index="dataset", columns="method", values=metric)
    if pivot.isna().any().any() or len(pivot) != 53 or len(methods) < 3:
        return {"appropriate": False, "reason": "requires complete 53-dataset blocks and at least three methods"}
    statistic, pvalue = friedmanchisquare(*[pivot[m].values for m in pivot.columns])
    k = pivot.shape[1]
    n = pivot.shape[0]
    q_alpha = float(studentized_range.ppf(1 - alpha, k, np.inf) / math.sqrt(2.0))
    cd = q_alpha * math.sqrt(k * (k + 1) / (6.0 * n))
    return {
        "appropriate": True,
        "n": n,
        "k": k,
        "methods": list(pivot.columns),
        "friedman_stat": float(statistic),
        "friedman_p": float(pvalue),
        "nemenyi_cd": float(cd),
        "alpha": alpha,
    }


def paired_acc(frame: pd.DataFrame, methods: list[str], tie_pp=0.05) -> pd.DataFrame:
    dm = dataset_method_means(frame)
    primary = dm[dm.method == PRIMARY].set_index("dataset")
    rows = []
    pvalues = []
    for method in methods:
        if method == PRIMARY:
            continue
        baseline = dm[dm.method == method].set_index("dataset")
        common = primary.index.intersection(baseline.index)
        if len(common) != 53:
            raise ValueError(f"{method}: paired comparison requires 53 common datasets")
        delta = (primary.loc[common, "ACC"] - baseline.loc[common, "ACC"]) * 100
        pvalue = paired_wilcoxon(primary.loc[common, "ACC"], baseline.loc[common, "ACC"])
        lo, hi = bootstrap_mean_ci(delta.values, n_boot=5000)
        rows.append({
            "baseline": method,
            "n": 53,
            "W": int((delta > tie_pp).sum()),
            "T": int((delta.abs() <= tie_pp).sum()),
            "L": int((delta < -tie_pp).sum()),
            "mean_delta_pp": float(delta.mean()),
            "median_delta_pp": float(delta.median()),
            "ci95_lo_pp": float(lo),
            "ci95_hi_pp": float(hi),
            "p_raw": float(pvalue),
        })
        pvalues.append(pvalue)
    adjusted = holm_adjust(pvalues) if pvalues else []
    for row, value in zip(rows, adjusted):
        row["p_holm"] = float(value)
    return pd.DataFrame(rows)


def aggregate_summary(frame: pd.DataFrame, methods: list[str], ranks: pd.DataFrame) -> pd.DataFrame:
    dm = dataset_method_means(frame)
    summary = dm[dm.method.isin(methods)].groupby("method")[["ACC", "NMI", "ARI", "F1"]].mean() * 100
    acc_rank = ranks[ranks.metric == "ACC"].set_index("method").avg_rank
    runtime = dm[dm.method.isin(methods)].groupby("method").runtime_seconds.agg(["mean", "median"])
    summary["ACC_rank"] = acc_rank
    summary["runtime_mean_s"] = runtime["mean"]
    summary["runtime_median_s"] = runtime["median"]
    psf_runtime = float(summary.loc[PRIMARY, "runtime_mean_s"])
    summary["speedup_vs_PSFCE"] = psf_runtime / summary.runtime_mean_s
    return summary.reset_index().sort_values("ACC", ascending=False)


def _tex(value) -> str:
    replacements = {"&": r"\&", "%": r"\%", "_": r"\_", "#": r"\#"}
    return "".join(replacements.get(ch, ch) for ch in str(value))


def _write_latex(summary, dataset_acc, pairwise, latex_dir: Path):
    lines = [
        r"\begin{table}[t]", r"\centering",
        r"\caption{Frozen comparison with successfully completed recent ensemble baselines.}",
        r"\small", r"\begin{tabular}{lrrrrrr}", r"\toprule",
        "Method & ACC & NMI & ARI & F1 & Rank & Time (s) \\\\", r"\midrule",
    ]
    for row in summary.itertuples(index=False):
        name = r"\textbf{" + _tex(row.method) + "}" if row.method == PRIMARY else _tex(row.method)
        lines.append(f"{name} & {row.ACC:.2f} & {row.NMI:.2f} & {row.ARI:.2f} & {row.F1:.2f} & {row.ACC_rank:.2f} & {row.runtime_mean_s:.2f} \\\\")
    lines += [r"\bottomrule", r"\end{tabular}", r"\label{tab:recent_baselines}", r"\end{table}"]
    (latex_dir / "table1_recent_baselines.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")

    columns = list(dataset_acc.columns)
    col_spec = "l" + "r" * len(columns)
    lines = [
        r"\begin{table*}[t]", r"\centering",
        r"\caption{Dataset-level ACC (\%) averaged over the three frozen pools.}",
        r"\scriptsize", r"\setlength{\tabcolsep}{3.2pt}",
        f"\\begin{{tabular}}{{{col_spec}}}", r"\toprule",
        "Dataset & " + " & ".join(_tex(c) for c in columns) + " \\\\", r"\midrule",
    ]
    for dataset, row in dataset_acc.iterrows():
        lines.append(_tex(dataset) + " & " + " & ".join(f"{100*row[c]:.2f}" for c in columns) + " \\\\")
    lines += [r"\bottomrule", r"\end{tabular}", r"\label{tab:recent_dataset_acc}", r"\end{table*}"]
    (latex_dir / "table2_dataset_acc.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")

    lines = [
        r"\begin{table}[t]", r"\centering",
        r"\caption{Dataset-level paired ACC comparison against PSF-CE.}",
        r"\small", r"\begin{tabular}{lrrrr}", r"\toprule",
        "Baseline & W/T/L & $\\Delta$ (pp) & Median & $p_{\\mathrm{Holm}}$ \\\\", r"\midrule",
    ]
    for row in pairwise.itertuples(index=False):
        lines.append(f"{_tex(row.baseline)} & {row.W}/{row.T}/{row.L} & {row.mean_delta_pp:.2f} & {row.median_delta_pp:.2f} & {row.p_holm:.3g} \\\\")
    lines += [r"\bottomrule", r"\end{tabular}", r"\label{tab:recent_pairwise}", r"\end{table}"]
    (latex_dir / "table3_pairwise.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_figure(summary: pd.DataFrame, output_dir: Path):
    ordered = summary.sort_values("ACC_rank")
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.6))
    axes[0].barh(ordered.method, ordered.ACC_rank, color="#2878B5")
    axes[0].invert_yaxis()
    axes[0].set_xlabel("Average ACC rank (lower is better)")
    runtime_order = summary.sort_values("runtime_mean_s")
    axes[1].barh(runtime_order.method, runtime_order.runtime_mean_s, color="#F28E2B")
    axes[1].set_xscale("log")
    axes[1].invert_yaxis()
    axes[1].set_xlabel("Mean runtime per dataset/pool (s, log scale)")
    for axis in axes:
        axis.spines[["top", "right"]].set_visible(False)
        axis.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    fig.savefig(output_dir / "fig1_rank_runtime.pdf", bbox_inches="tight")
    fig.savefig(output_dir / "fig1_rank_runtime.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def build_final_report(merged_csv, output_dir):
    output = Path(output_dir)
    latex = output / "latex"
    output.mkdir(parents=True, exist_ok=True)
    latex.mkdir(parents=True, exist_ok=True)
    frame = pd.read_csv(merged_csv)
    methods, completion = eligible_methods(frame)
    completion.to_csv(output / "method_completion.csv", index=False)
    eligible_frame = frame[(frame.method.isin(methods)) & (frame.status == "ok")].copy()
    ranks = rank_summary(eligible_frame, methods)
    ranks.to_csv(output / "average_ranks.csv", index=False)
    pairwise = paired_acc(eligible_frame, methods)
    pairwise.to_csv(output / "pairwise_wtl.csv", index=False)
    summary = aggregate_summary(eligible_frame, methods, ranks)
    summary.to_csv(output / "table1_recent_baselines.csv", index=False)
    dm = dataset_method_means(eligible_frame)
    dm.to_csv(output / "dataset_method_complete_metrics.csv", index=False)
    dataset_acc = dm.pivot(index="dataset", columns="method", values="ACC")[methods]
    dataset_acc.to_csv(output / "table2_dataset_acc.csv")
    omnibus = {metric: friedman_nemenyi(eligible_frame, methods, metric) for metric in ["ACC", "NMI", "ARI", "F1"]}
    (output / "friedman_nemenyi.json").write_text(json.dumps(omnibus, indent=2), encoding="utf-8")
    _write_latex(summary, dataset_acc, pairwise, latex)
    _write_figure(summary, output)

    failed = completion[~completion.complete]
    lines = ["# PSF-CE V4 final recent-baseline report", "", "## Eligible completed methods"]
    for row in summary.itertuples(index=False):
        lines.append(f"- {row.method}: ACC={row.ACC:.2f}, NMI={row.NMI:.2f}, ARI={row.ARI:.2f}, rank={row.ACC_rank:.2f}, mean runtime={row.runtime_mean_s:.3f}s")
    lines += ["", "## Incomplete methods"]
    if failed.empty:
        lines.append("- None.")
    else:
        for row in failed.itertuples(index=False):
            lines.append(f"- {row.method}: 未完成，不得参与比较 ({row.successful_rows}/{row.expected_rows} rows).")
    lines += ["", "## Statistical scope", "- Dataset is the statistical unit; the three frozen pools are averaged within each dataset.", "- Wilcoxon tests are paired and two-sided; Holm correction is applied across completed recent baselines only.", "- Friedman and Nemenyi results are produced only for complete 53-dataset blocks."]
    (output / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"methods": methods, "completion": completion, "summary": summary}
