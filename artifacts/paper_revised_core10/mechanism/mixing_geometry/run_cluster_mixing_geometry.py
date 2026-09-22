from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import shutil
import sys
import warnings
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import h5py
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy
from scipy.stats import ConstantInputWarning, spearmanr, wilcoxon
import sklearn
from sklearn.metrics import completeness_score, homogeneity_score, normalized_mutual_info_score


ROOT_TEXT = os.environ.get("PSFCE_PRIVATE_RESULTS_ROOT")
if not ROOT_TEXT:
    raise SystemExit(
        "Set PSFCE_PRIVATE_RESULTS_ROOT to the private full revised-Core10 results root. "
        "The public repository intentionally does not redistribute predictions or raw inputs."
    )
ROOT = Path(ROOT_TEXT).expanduser().resolve()
EXP1 = ROOT / "06_EXPERIMENT1"
EXP3 = ROOT / "14_EXPLORATORY_EXPERIMENT3_20260922"
HMIX = ROOT / "15_EXPLORATORY_HOMOGENEITY_MIXING_20260922"
OUTPUT = ROOT / "16_EXPLORATORY_CLUSTER_MIXING_GEOMETRY_20260922"
ZIP_PATH = ROOT / "PSF_CE_EXPLORATORY_CLUSTER_MIXING_GEOMETRY_20260922.zip"
PROMPT_TEXT = os.environ.get("PSFCE_MIXING_PROTOCOL_FILE")
if not PROMPT_TEXT:
    raise SystemExit("Set PSFCE_MIXING_PROTOCOL_FILE to the frozen exploratory protocol text.")
PROMPT = Path(PROMPT_TEXT).expanduser().resolve()
SCRIPT = Path(__file__).resolve()

METHODS = ["MCLA", "HBGF", "CEHM", "YACHT", "RANGE", "GPEC", "PSF-CE"]
COMPARATORS = METHODS[:-1]
OURS = "PSF-CE"
DATASETS = ["BBC News Sport", "Leukemia", "Caltech101-20", "Leukemia2", "Chameleon", "Amazon Photo", "ORL", "ACM", "Iris", "Mushroom"]
TOL = 1e-12

UNIFORM_DIRECTIONS = {
    "homogeneity": "higher", "MacroMixEntropy": "lower", "MacroPurity": "higher", "PairMixRate": "lower",
}
CONCENTRATION_DIRECTIONS = {
    "rho_size_entropy": "higher", "rho_size_pairmix": "higher", "LCMER": "higher",
    "Top1MixExcessRatio": "higher", "MixingHHI": "higher", "PurityGap": "higher",
    "EntropyGap": "higher", "PairMixGap": "higher",
}
SUPPLEMENTARY_DIRECTIONS = {
    "H_Y_given_Z": "lower", "MixingEffectiveClusters": "lower", "MixingBurdenEntropy": "lower",
    "MixingGini": "higher", "cluster_size_cv": "higher", "largest_cluster_fraction": "higher",
    "LargeClusterSampleShare": "higher", "LCMS": "higher", "LCPCS": "higher",
    "Top1CrossMixShare": "higher", "Top1PairCapacityShare": "higher",
}
ALL_DIRECTIONS = {**UNIFORM_DIRECTIONS, **CONCENTRATION_DIRECTIONS, **SUPPLEMENTARY_DIRECTIONS}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_i32(values: np.ndarray) -> str:
    return hashlib.sha256(np.asarray(values, dtype=np.int32).reshape(-1).tobytes(order="C")).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def load_vector(path: Path, key: str) -> np.ndarray:
    if path.suffix.lower() == ".npz":
        with np.load(path, allow_pickle=False) as payload:
            return np.asarray(payload[key], dtype=np.int32).reshape(-1)
    if path.suffix.lower() == ".mat":
        with h5py.File(path, "r") as handle:
            return np.asarray(handle["result"]["predicted_labels"], dtype=np.int32).ravel(order="F")
    raise ValueError(path)


def entropy(prob: np.ndarray) -> float:
    p = np.asarray(prob, dtype=float)
    p = p[p > 0]
    return float(-np.sum(p * np.log(p)))


def gini(values: np.ndarray) -> float:
    x = np.asarray(values, dtype=float)
    if len(x) == 0 or np.sum(x) <= 0:
        return math.nan
    x = np.sort(x)
    n = len(x)
    return float((2 * np.sum((np.arange(1, n + 1)) * x) / (n * np.sum(x))) - (n + 1) / n)


def safe_spearman(x: np.ndarray, y: np.ndarray) -> float:
    mask = np.isfinite(x) & np.isfinite(y)
    x, y = x[mask], y[mask]
    if len(x) < 3 or np.unique(x).size < 2 or np.unique(y).size < 2:
        return math.nan
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", ConstantInputWarning)
        return float(spearmanr(x, y).statistic)


def cluster_geometry(y: np.ndarray, z: np.ndarray) -> tuple[list[dict[str, object]], dict[str, float | int]]:
    y_values, yi = np.unique(y, return_inverse=True)
    z_values, zi = np.unique(z, return_inverse=True)
    c, k, n = len(y_values), len(z_values), len(y)
    counts = np.zeros((c, k), dtype=np.int64)
    np.add.at(counts, (yi, zi), 1)
    rows = []
    for j, label in enumerate(z_values):
        column = counts[:, j]
        size = int(column.sum())
        probs = column[column > 0] / size
        e = entropy(probs)
        capacity = size * (size - 1) / 2
        same = float(np.sum(column * (column - 1) / 2))
        cross = float(capacity - same)
        rows.append({
            "predicted_cluster_label": int(label), "cluster_size": size, "cluster_fraction": size / n,
            "cluster_entropy": e, "normalized_cluster_entropy": e / np.log(c) if c > 1 else math.nan,
            "cluster_purity": float(column.max() / size), "number_of_true_classes": int(np.count_nonzero(column)),
            "cross_class_pairs": cross, "within_cluster_pairs": capacity,
            "local_pair_mixing_rate": cross / capacity if capacity > 0 else math.nan,
        })
    frame = pd.DataFrame(rows)
    nominal = max(1, math.ceil(k / 4))
    cutoff = frame.cluster_size.sort_values(ascending=False).iloc[nominal - 1]
    frame["is_large_tie_closed"] = frame.cluster_size >= cutoff
    max_size = frame.cluster_size.max()
    frame["is_max_size_tie"] = frame.cluster_size == max_size
    total_cross = float(frame.cross_class_pairs.sum())
    total_capacity = float(frame.within_cluster_pairs.sum())
    large = frame[frame.is_large_tie_closed]
    small = frame[~frame.is_large_tie_closed]
    max_group = frame[frame.is_max_size_tie]

    lcms = float(large.cross_class_pairs.sum() / total_cross) if total_cross > 0 else math.nan
    lcpcs = float(large.within_cluster_pairs.sum() / total_capacity) if total_capacity > 0 else math.nan
    top_cross = float((max_group.cross_class_pairs / total_cross).mean()) if total_cross > 0 else math.nan
    top_capacity = float((max_group.within_cluster_pairs / total_capacity).mean()) if total_capacity > 0 else math.nan
    burden = frame.cross_class_pairs.to_numpy(float) / total_cross if total_cross > 0 else np.full(k, np.nan)
    burden_positive = burden[np.isfinite(burden) & (burden > 0)]
    hhi = float(np.sum(burden ** 2)) if total_cross > 0 else math.nan
    mix_entropy = float(-np.sum(burden_positive * np.log(burden_positive)) / np.log(k)) if total_cross > 0 and k > 1 else math.nan

    def mean_or_nan(series: pd.Series) -> float:
        return float(series.mean()) if len(series) else math.nan

    sizes = frame.cluster_size.to_numpy(float)
    summary = {
        "n": n, "target_c": c, "returned_k": k,
        "homogeneity": float(homogeneity_score(y, z)), "completeness": float(completeness_score(y, z)),
        "NMI": float(normalized_mutual_info_score(y, z, average_method="arithmetic")),
        "H_Y_given_Z": float(entropy(counts.ravel() / n) - entropy(counts.sum(axis=0) / n)),
        "H_Z": entropy(counts.sum(axis=0) / n), "effective_k": float(np.exp(entropy(counts.sum(axis=0) / n))),
        "cluster_size_cv": float(np.std(sizes, ddof=0) / np.mean(sizes)),
        "largest_cluster_fraction": float(max_size / n),
        "MacroMixEntropy": float(frame.normalized_cluster_entropy.mean()),
        "MacroPurity": float(frame.cluster_purity.mean()),
        "PairMixRate": total_cross / total_capacity if total_capacity > 0 else math.nan,
        "rho_size_entropy": safe_spearman(np.log(sizes), frame.normalized_cluster_entropy.to_numpy(float)),
        "rho_size_pairmix": safe_spearman(np.log(sizes), frame.local_pair_mixing_rate.to_numpy(float)),
        "large_nominal_count": nominal, "large_tie_closed_count": len(large),
        "large_cutoff_size": int(cutoff), "max_size_tie_count": len(max_group),
        "LCMS": lcms, "LCPCS": lcpcs, "LCMER": lcms / lcpcs if np.isfinite(lcms) and lcpcs > 0 else math.nan,
        "Top1CrossMixShare": top_cross, "Top1PairCapacityShare": top_capacity,
        "Top1MixExcessRatio": top_cross / top_capacity if np.isfinite(top_cross) and top_capacity > 0 else math.nan,
        "LargeClusterSampleShare": float(large.cluster_size.sum() / n),
        "Large_MacroPurity": mean_or_nan(large.cluster_purity), "SmallMid_MacroPurity": mean_or_nan(small.cluster_purity),
        "Large_MacroMixEntropy": mean_or_nan(large.normalized_cluster_entropy), "SmallMid_MacroMixEntropy": mean_or_nan(small.normalized_cluster_entropy),
        "Large_LocalPairMixMean": mean_or_nan(large.local_pair_mixing_rate), "SmallMid_LocalPairMixMean": mean_or_nan(small.local_pair_mixing_rate),
        "MixingHHI": hhi, "MixingEffectiveClusters": 1 / hhi if np.isfinite(hhi) and hhi > 0 else math.nan,
        "MixingBurdenEntropy": mix_entropy, "MixingGini": gini(frame.cross_class_pairs.to_numpy(float)),
    }
    summary["PurityGap"] = summary["SmallMid_MacroPurity"] - summary["Large_MacroPurity"]
    summary["EntropyGap"] = summary["Large_MacroMixEntropy"] - summary["SmallMid_MacroMixEntropy"]
    summary["PairMixGap"] = summary["Large_LocalPairMixMean"] - summary["SmallMid_LocalPairMixMean"]
    return frame.to_dict("records"), summary


def holm(values: list[float]) -> list[float]:
    p = np.asarray(values, dtype=float)
    order = np.argsort(p)
    out = np.empty_like(p)
    running = 0.0
    for rank, index in enumerate(order):
        running = max(running, (len(p) - rank) * p[index])
        out[index] = min(1.0, running)
    return out.tolist()


def profiles_and_stats(means: pd.DataFrame, cohort: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    part = means[means.cohort == cohort]
    profiles, stats = [], []
    for metric, direction in ALL_DIRECTIONS.items():
        family_indices, family_p = [], []
        ours = part[part.method == OURS][["dataset", metric]].rename(columns={metric: "ours"})
        for comparator in COMPARATORS:
            other = part[part.method == comparator][["dataset", metric]].rename(columns={metric: "other"})
            pair = ours.merge(other, on="dataset", validate="one_to_one").dropna()
            raw = pair.ours.to_numpy(float) - pair.other.to_numpy(float)
            advantage = raw if direction == "higher" else -raw
            wins, ties, losses = int(np.sum(advantage > TOL)), int(np.sum(np.abs(advantage) <= TOL)), int(np.sum(advantage < -TOL))
            mean = float(np.mean(advantage)) if len(advantage) else math.nan
            median = float(np.median(advantage)) if len(advantage) else math.nan
            favorable = bool(mean > 0 and median > 0 and wins > losses)
            profiles.append({
                "cohort": cohort, "metric": metric, "direction": direction, "comparator": comparator,
                "n_valid_datasets": len(advantage), "mean_raw_delta_psf_minus_comparator": float(np.mean(raw)) if len(raw) else math.nan,
                "median_raw_delta_psf_minus_comparator": float(np.median(raw)) if len(raw) else math.nan,
                "mean_directional_advantage": mean, "median_directional_advantage": median,
                "wins": wins, "ties": ties, "losses": losses, "favorable": favorable,
            })
            nonzero = advantage[np.abs(advantage) > TOL]
            if len(nonzero) == 0:
                statistic, pvalue = 0.0, 1.0
            else:
                test = wilcoxon(advantage, alternative="two-sided", zero_method="wilcox")
                statistic, pvalue = float(test.statistic), float(test.pvalue)
            stats.append({
                "cohort": cohort, "metric": metric, "comparator": comparator, "n_valid_datasets": len(advantage),
                "wilcoxon_statistic": statistic, "raw_p": pvalue, "mean_directional_advantage": mean,
                "median_directional_advantage": median, "wins": wins, "ties": ties, "losses": losses,
            })
            family_indices.append(len(stats) - 1)
            family_p.append(pvalue)
        for index, corrected in zip(family_indices, holm(family_p)):
            stats[index]["holm_p"] = corrected
    return pd.DataFrame(profiles), pd.DataFrame(stats)


def fav(profile: pd.DataFrame, cohort: str, metric: str, comparator: str | None = None) -> int | bool:
    rows = profile[(profile.cohort == cohort) & (profile.metric == metric)]
    if comparator is not None:
        return str(rows[rows.comparator == comparator].iloc[0].favorable).lower() == "true"
    return int(rows.favorable.astype(str).str.lower().eq("true").sum())


def classify_cohort(profile: pd.DataFrame, cohort: str) -> tuple[str, dict[str, int]]:
    counts = {metric: int(fav(profile, cohort, metric)) for metric in list(UNIFORM_DIRECTIONS) + list(CONCENTRATION_DIRECTIONS)}
    concentration_count = sum(counts[m] >= 4 for m in CONCENTRATION_DIRECTIONS)
    if counts["homogeneity"] < 4 or (counts["MacroMixEntropy"] < 4 and counts["MacroPurity"] < 4):
        return "M-D", counts | {"concentration_metrics_ge4": concentration_count}
    if all(counts[m] >= 4 for m in ["homogeneity", "MacroMixEntropy", "MacroPurity", "PairMixRate"]) and counts["LCMER"] < 4:
        return "M-A", counts | {"concentration_metrics_ge4": concentration_count}
    if all(counts[m] >= 4 for m in ["homogeneity", "MacroMixEntropy", "MacroPurity"]) and counts["PairMixRate"] < 4 and concentration_count >= 2:
        return "M-B", counts | {"concentration_metrics_ge4": concentration_count}
    return "M-C", counts | {"concentration_metrics_ge4": concentration_count}


def comparator_class(profile: pd.DataFrame, cohort: str, comparator: str) -> tuple[str, int]:
    u = {m: bool(fav(profile, cohort, m, comparator)) for m in UNIFORM_DIRECTIONS}
    c = {m: bool(fav(profile, cohort, m, comparator)) for m in CONCENTRATION_DIRECTIONS}
    c_count = sum(c.values())
    if all(u.values()) and not c["LCMER"]:
        return "U", c_count
    if u["homogeneity"] and u["MacroMixEntropy"] and u["MacroPurity"] and not u["PairMixRate"] and c_count >= 2:
        return "C", c_count
    if u["homogeneity"] or u["MacroMixEntropy"] or u["MacroPurity"]:
        return "M", c_count
    return "N", c_count


def save_figure(fig: plt.Figure, directory: Path, name: str) -> None:
    fig.tight_layout()
    fig.savefig(directory / f"{name}.pdf", bbox_inches="tight")
    fig.savefig(directory / f"{name}.png", dpi=180, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    if OUTPUT.exists() or ZIP_PATH.exists():
        raise RuntimeError("Refusing to overwrite existing cluster-mixing geometry output.")
    dirs = ["00_PROTOCOL", "01_INPUT_AUDIT", "02_CLUSTER_LEVEL_METRICS", "03_DATASET_LEVEL_SUMMARY", "04_COMPARATOR_PROFILES", "05_SIZE_STRATIFIED_ANALYSIS", "06_MIXING_CONCENTRATION", "07_FRAGMENTATION_MIXING_JOINT", "08_STATISTICS", "09_VALIDATION", "10_FINAL_REPORT", "figures"]
    for name in dirs:
        (OUTPUT / name).mkdir(parents=True, exist_ok=False)
    shutil.copy2(PROMPT, OUTPUT / "00_PROTOCOL" / "ORIGINAL_USER_PROTOCOL.txt")
    shutil.copy2(SCRIPT, OUTPUT / "00_PROTOCOL" / SCRIPT.name)
    clarifications = {
        "schema": "psfce-cluster-mixing-geometry-operational-clarifications-v1",
        "analysis_status": "EXPLORATORY_NOT_CONFIRMATORY",
        "frozen_before_endpoint_computation": True,
        "large_group_ties": "Tie-closed: include all clusters whose size is at least the nominal ceil(K/4) cutoff size; report nominal and actual counts.",
        "top1_ties": "Average per-cluster burden and capacity shares across all maximum-size tied clusters; the excess ratio is invariant to this common averaging factor.",
        "cohort_classification": "Apply M-A/M-B/M-C/M-D rules independently to Core-10 and Core-9. Final M-A or M-B requires identical classification in both; otherwise M-C, except Core-10 M-D remains M-D.",
        "comparator_classification": {
            "U": "All four uniform metrics favorable and LCMER not concentration-favorable.",
            "C": "Homogeneity, MacroMixEntropy, MacroPurity favorable; PairMixRate not favorable; at least two of eight concentration metrics favorable.",
            "M": "At least one of Homogeneity, MacroMixEntropy, MacroPurity favorable, but U/C not met.",
            "N": "None of Homogeneity, MacroMixEntropy, MacroPurity favorable.",
        },
        "representative_lorenz_dataset": "BBC News Sport pool0, fixed by cohort order rather than endpoint values.",
        "tie_tolerance": TOL,
    }
    write_json(OUTPUT / "00_PROTOCOL" / "OPERATIONAL_CLARIFICATIONS.json", clarifications)

    manifest = pd.read_csv(EXP1 / "INPUT_PROVENANCE.csv")
    manifest = manifest[manifest.method.isin(METHODS)].copy()
    manifest["pool"] = manifest.pool.astype(int)
    expected = 10 * 3 * 7
    if len(manifest) != expected or manifest[["dataset", "pool", "method"]].duplicated().any():
        raise RuntimeError("Revised Core-10 coverage failure")
    if set(manifest.dataset) != set(DATASETS) or set(manifest.method) != set(METHODS):
        raise RuntimeError("Dataset or method coverage mismatch")

    cluster_rows, summary_rows, audit_rows = [], [], []
    for row in manifest.itertuples(index=False):
        pred_path, truth_path = Path(row.prediction_path), Path(row.true_label_source_path)
        pred, truth = load_vector(pred_path, "labels"), load_vector(truth_path, "y")
        if len(pred) != len(truth):
            raise RuntimeError(f"Length mismatch: {row.dataset}/{row.pool}/{row.method}")
        pred_sha, truth_sha = sha256_file(pred_path), sha256_file(truth_path)
        pred_label_sha, truth_label_sha = sha256_i32(pred), sha256_i32(truth)
        audit_rows.append({
            "dataset": row.dataset, "pool": row.pool, "method": row.method,
            "prediction_path": str(pred_path), "truth_path": str(truth_path),
            "prediction_file_sha256": pred_sha, "truth_file_sha256": truth_sha,
            "prediction_label_sha256": pred_label_sha, "truth_label_sha256": truth_label_sha,
            "prediction_file_hash_match": pred_sha.lower() == str(row.prediction_file_sha256).lower(),
            "truth_file_hash_match": truth_sha.lower() == str(row.true_label_source_file_sha256).lower(),
            "prediction_label_hash_match": pred_label_sha.lower() == str(row.prediction_labels_sha256_int32_c).lower(),
            "truth_label_hash_match": truth_label_sha.lower() == str(row.true_labels_sha256_int32_c).lower(),
            "length_match": len(pred) == len(truth), "returned_k_manifest": int(row.returned_k),
            "returned_k_actual": int(np.unique(pred).size), "returned_k_match": int(row.returned_k) == int(np.unique(pred).size),
        })
        clusters, summary = cluster_geometry(truth, pred)
        summary.update({"cohort": "REVISED_CORE10_NATIVE", "dataset": row.dataset, "pool": row.pool, "method": row.method})
        summary_rows.append(summary)
        for cluster in clusters:
            cluster.update({"cohort": "REVISED_CORE10_NATIVE", "dataset": row.dataset, "pool": row.pool, "method": row.method})
            cluster_rows.append(cluster)

    audit = pd.DataFrame(audit_rows)
    bool_cols = [c for c in audit.columns if c.endswith("_match")]
    if not audit[bool_cols].all().all():
        raise RuntimeError("Input hash/identity audit failed")
    audit.to_csv(OUTPUT / "01_INPUT_AUDIT" / "INPUT_IDENTITY_AUDIT.csv", index=False, encoding="utf-8-sig")

    clusters = pd.DataFrame(cluster_rows)
    summaries = pd.DataFrame(summary_rows)
    clusters.to_csv(OUTPUT / "02_CLUSTER_LEVEL_METRICS" / "CLUSTER_LEVEL_METRICS.csv", index=False, encoding="utf-8-sig")
    summaries.to_csv(OUTPUT / "02_CLUSTER_LEVEL_METRICS" / "PREDICTION_LEVEL_SUMMARY.csv", index=False, encoding="utf-8-sig")
    clusters[clusters.dataset == "Iris"].to_csv(OUTPUT / "05_SIZE_STRATIFIED_ANALYSIS" / "IRIS_CLUSTER_GEOMETRY.csv", index=False, encoding="utf-8-sig")
    clusters[clusters.dataset == "Mushroom"].to_csv(OUTPUT / "05_SIZE_STRATIFIED_ANALYSIS" / "MUSHROOM_CLUSTER_GEOMETRY.csv", index=False, encoding="utf-8-sig")

    previous = pd.read_csv(HMIX / "02_DATASET_POOL_METRICS" / "ALL_COHORT_POOL_METRICS.csv")
    previous = previous[previous.cohort == "REVISED_CORE10_NATIVE"]
    reproduce_metrics = ["homogeneity", "H_Y_given_Z", "MacroMixEntropy", "PairMixRate", "MacroPurity", "H_Z", "effective_k", "cluster_size_cv"]
    merged = summaries.merge(previous[["dataset", "pool", "method"] + reproduce_metrics], on=["dataset", "pool", "method"], suffixes=("_new", "_old"), validate="one_to_one")
    reproduction_rows = []
    for metric in reproduce_metrics:
        diff = np.abs(merged[f"{metric}_new"] - merged[f"{metric}_old"])
        reproduction_rows.append({"metric": metric, "max_abs_difference": float(diff.max(skipna=True)), "within_1e12": bool(diff.max(skipna=True) <= TOL)})
    reproduction = pd.DataFrame(reproduction_rows)
    reproduction.to_csv(OUTPUT / "09_VALIDATION" / "INPUT_METRIC_REPRODUCTION.csv", index=False, encoding="utf-8-sig")
    reproduction_failure = not reproduction.within_1e12.all()

    core9_summaries = summaries[summaries.dataset != "Chameleon"].copy()
    core9_summaries["cohort"] = "REVISED_CORE9_NO_CHAMELEON"
    all_summaries = pd.concat([summaries, core9_summaries], ignore_index=True)
    metric_cols = [c for c in summaries.columns if c not in ["cohort", "dataset", "pool", "method"]]
    dataset_means = all_summaries.groupby(["cohort", "dataset", "method"], as_index=False)[metric_cols].mean()
    dataset_means.to_csv(OUTPUT / "03_DATASET_LEVEL_SUMMARY" / "DATASET_LEVEL_MEANS.csv", index=False, encoding="utf-8-sig")

    profile_parts, stat_parts = [], []
    for cohort in ["REVISED_CORE10_NATIVE", "REVISED_CORE9_NO_CHAMELEON"]:
        p, s = profiles_and_stats(dataset_means, cohort)
        profile_parts.append(p); stat_parts.append(s)
    profiles = pd.concat(profile_parts, ignore_index=True)
    stats = pd.concat(stat_parts, ignore_index=True)
    profiles.to_csv(OUTPUT / "04_COMPARATOR_PROFILES" / "COMPARATOR_PROFILES.csv", index=False, encoding="utf-8-sig")
    stats.to_csv(OUTPUT / "08_STATISTICS" / "EXPLORATORY_WILCOXON_HOLM.csv", index=False, encoding="utf-8-sig")

    cohort_classes, cohort_counts = {}, {}
    for cohort in ["REVISED_CORE10_NATIVE", "REVISED_CORE9_NO_CHAMELEON"]:
        cohort_classes[cohort], cohort_counts[cohort] = classify_cohort(profiles, cohort)
    if cohort_classes["REVISED_CORE10_NATIVE"] == "M-D":
        final_case = "M-D"
    elif cohort_classes["REVISED_CORE10_NATIVE"] in ["M-A", "M-B"] and cohort_classes["REVISED_CORE9_NO_CHAMELEON"] == cohort_classes["REVISED_CORE10_NATIVE"]:
        final_case = cohort_classes["REVISED_CORE10_NATIVE"]
    else:
        final_case = "M-C"

    comparator_rows = []
    for cohort in ["REVISED_CORE10_NATIVE", "REVISED_CORE9_NO_CHAMELEON"]:
        for comparator in COMPARATORS:
            label, concentration_count = comparator_class(profiles, cohort, comparator)
            comparator_rows.append({
                "cohort": cohort, "comparator": comparator, "classification": label,
                "concentration_metrics_favorable": concentration_count,
                **{f"{metric}_favorable": bool(fav(profiles, cohort, metric, comparator)) for metric in UNIFORM_DIRECTIONS},
                **{f"{metric}_concentration_favorable": bool(fav(profiles, cohort, metric, comparator)) for metric in CONCENTRATION_DIRECTIONS},
            })
    comparator_classes = pd.DataFrame(comparator_rows)
    comparator_classes.to_csv(OUTPUT / "04_COMPARATOR_PROFILES" / "COMPARATOR_MECHANISM_CLASSIFICATION.csv", index=False, encoding="utf-8-sig")

    joint_rows = []
    for cohort, frag_path in [
        ("REVISED_CORE10_NATIVE", EXP3 / "01_NATIVE_OUTPUT_CORE10" / "comparator_profiles.csv"),
        ("REVISED_CORE9_NO_CHAMELEON", EXP3 / "02_EXCLUDE_CHAMELEON_CORE9" / "comparator_profiles.csv"),
    ]:
        frag = pd.read_csv(frag_path)
        for comparator in COMPARATORS:
            h = str(frag[(frag.metric == "H_Z_given_Y") & (frag.comparator == comparator)].iloc[0].favorable).lower() == "true"
            macro = str(frag[(frag.metric == "macro_fragmentation") & (frag.comparator == comparator)].iloc[0].favorable).lower() == "true"
            mixing = comparator_classes[(comparator_classes.cohort == cohort) & (comparator_classes.comparator == comparator)].iloc[0].classification
            fragmentation = h and macro
            if fragmentation and mixing == "U": joint = "reduced_fragmentation_plus_uniform_purification"
            elif fragmentation and mixing == "C": joint = "reduced_fragmentation_plus_localized_residual_mixing"
            elif fragmentation: joint = "reduced_fragmentation_only"
            else: joint = "neither"
            joint_rows.append({"cohort": cohort, "comparator": comparator, "H_Z_given_Y_favorable": h, "macro_fragmentation_favorable": macro, "fragmentation_favorable": fragmentation, "mixing_class": mixing, "joint_class": joint})
    joint = pd.DataFrame(joint_rows)
    joint.to_csv(OUTPUT / "07_FRAGMENTATION_MIXING_JOINT" / "PARTITION_GEOMETRY_JOINT_SUMMARY.csv", index=False, encoding="utf-8-sig")

    # Fixed-scope audit plots; no endpoint-selected datasets.
    colors = {OURS: "#0072B2"}
    for comparator in COMPARATORS:
        for field, ylabel, slug in [
            ("normalized_cluster_entropy", "Normalized cluster entropy", "size_vs_entropy"),
            ("local_pair_mixing_rate", "Local pair mixing rate", "size_vs_pairmix"),
        ]:
            fig, ax = plt.subplots(figsize=(5.0, 3.6))
            for method, marker, color in [(comparator, "s", "#D55E00"), (OURS, "o", colors[OURS])]:
                part = clusters[clusters.method == method]
                ax.scatter(np.log(part.cluster_size), part[field], s=13, alpha=0.45, marker=marker, label=method, color=color)
            ax.set_xlabel("log cluster size"); ax.set_ylabel(ylabel); ax.legend(frameon=False, fontsize=8)
            save_figure(fig, OUTPUT / "figures", f"{slug}_{comparator.lower().replace('-', '_')}")
    fig, ax = plt.subplots(figsize=(6.0, 3.8))
    data = [summaries[summaries.method == method].LCMER.dropna().to_numpy() for method in METHODS]
    ax.boxplot(data, tick_labels=METHODS, showfliers=False); ax.axhline(1, color="grey", linestyle="--", linewidth=0.8); ax.tick_params(axis="x", rotation=35); ax.set_ylabel("LCMER")
    save_figure(fig, OUTPUT / "figures", "lcmer_by_method")
    fig, ax = plt.subplots(figsize=(6.0, 3.8))
    x = np.arange(len(METHODS)); large = [summaries[summaries.method == m].Large_MacroPurity.mean() for m in METHODS]; small = [summaries[summaries.method == m].SmallMid_MacroPurity.mean() for m in METHODS]
    ax.plot(x, large, "s-", label="Large"); ax.plot(x, small, "o-", label="Small/mid"); ax.set_xticks(x, METHODS, rotation=35); ax.set_ylabel("Macro purity"); ax.legend(frameon=False)
    save_figure(fig, OUTPUT / "figures", "large_vs_smallmid_macro_purity")
    fig, ax = plt.subplots(figsize=(5.0, 3.7))
    representative = clusters[(clusters.dataset == "BBC News Sport") & (clusters.pool == 0)]
    for method in METHODS:
        burden = np.sort(representative[representative.method == method].cross_class_pairs.to_numpy(float))
        if burden.sum() <= 0: continue
        curve = np.r_[0.0, np.cumsum(burden) / burden.sum()]
        ax.plot(np.linspace(0, 1, len(curve)), curve, linewidth=1, label=method)
    ax.plot([0, 1], [0, 1], "k--", linewidth=0.7); ax.set_xlabel("Cumulative cluster fraction"); ax.set_ylabel("Cumulative mixing burden"); ax.legend(fontsize=6, frameon=False, ncol=2)
    save_figure(fig, OUTPUT / "figures", "bbc_news_sport_pool0_mixing_lorenz")

    main_counts = cohort_counts["REVISED_CORE10_NATIVE"]
    core9_counts = cohort_counts["REVISED_CORE9_NO_CHAMELEON"]
    main_class = comparator_classes[comparator_classes.cohort == "REVISED_CORE10_NATIVE"]
    localized = main_class[main_class.classification == "C"].comparator.tolist()
    uniform = main_class[main_class.classification == "U"].comparator.tolist()
    mixed = main_class[main_class.classification == "M"].comparator.tolist()
    unsupported = main_class[main_class.classification == "N"].comparator.tolist()
    joint_main = joint[joint.cohort == "REVISED_CORE10_NATIVE"]
    joint_localized = joint_main[joint_main.joint_class == "reduced_fragmentation_plus_localized_residual_mixing"].comparator.tolist()

    # Dataset case summaries use fixed datasets and do not affect the verdict.
    case_studies = {}
    for dataset in ["Iris", "Mushroom"]:
        part = summaries[summaries.dataset == dataset]
        psf = part[part.method == OURS]
        case_studies[dataset] = {
            "psf_mean_returned_k": float(psf.returned_k.mean()), "psf_mean_cluster_size_cv": float(psf.cluster_size_cv.mean()),
            "psf_mean_LCMER": float(psf.LCMER.mean()), "psf_mean_Top1MixExcessRatio": float(psf.Top1MixExcessRatio.mean()),
            "psf_mean_MixingHHI": float(psf.MixingHHI.mean()), "psf_mean_PurityGap": float(psf.PurityGap.mean()),
            "psf_mean_EntropyGap": float(psf.EntropyGap.mean()), "psf_mean_PairMixGap": float(psf.PairMixGap.mean()),
        }

    case_labels = {"M-A": "UNIFORM_MIXING_REDUCTION", "M-B": "LOCALIZED_RESIDUAL_MIXING", "M-C": "MIXED_CLUSTER_GEOMETRY", "M-D": "NO_STABLE_HOMOGENEITY_STRUCTURE"}
    answers = {
        "Q01_homogeneity_reproduced": main_counts["homogeneity"], "Q02_macro_mix_entropy_reproduced": main_counts["MacroMixEntropy"],
        "Q03_macro_purity_reproduced": main_counts["MacroPurity"], "Q04_pair_mix_rate_reproduced": main_counts["PairMixRate"],
        "Q05_stronger_size_mixing_association": {"rho_size_entropy": main_counts["rho_size_entropy"], "rho_size_pairmix": main_counts["rho_size_pairmix"]},
        "Q06_LCMER": main_counts["LCMER"], "Q07_Top1MixExcessRatio": main_counts["Top1MixExcessRatio"], "Q08_MixingHHI": main_counts["MixingHHI"],
        "Q09_PurityGap": main_counts["PurityGap"], "Q10_EntropyGap": main_counts["EntropyGap"], "Q11_PairMixGap": main_counts["PairMixGap"],
        "Q12_concentration_metrics_ge4": main_counts["concentration_metrics_ge4"],
        "Q13_core9_same_top_level": cohort_classes["REVISED_CORE9_NO_CHAMELEON"] == cohort_classes["REVISED_CORE10_NATIVE"],
        "Q14_localized_comparators": localized, "Q15_uniform_comparators": uniform,
        "Q16_mixed_or_unsupported_comparators": {"mixed": mixed, "unsupported": unsupported},
        "Q17_mushroom": case_studies["Mushroom"], "Q18_iris": case_studies["Iris"],
        "Q19_joint_stable_structure": {"localized_with_fragmentation": joint_localized, "count": len(joint_localized)},
        "Q20_final_case": final_case, "Q21_uniform_purification_supported": final_case == "M-A",
        "Q22_localized_residual_mixing_supported": final_case == "M-B",
        "Q23_fragmentation_plus_localized_supported": len(joint_localized) >= 4,
        "Q24_paper_narrative": case_labels[final_case],
    }
    final = {
        "schema": "psfce-exploratory-cluster-mixing-geometry-final-v1", "analysis_status": "EXPLORATORY_NOT_CONFIRMATORY",
        "cohort_classifications": cohort_classes, "cohort_profile_counts": cohort_counts,
        "final_case": final_case, "final_label": case_labels[final_case],
        "comparator_classes_core10": {r.comparator: r.classification for r in main_class.itertuples(index=False)},
        "joint_localized_with_fragmentation": joint_localized, "case_studies": case_studies,
        "required_answers": answers,
        "boundary": "Cluster-level geometry is exploratory structural evidence, not causal mechanism proof; no prediction or model was changed.",
    }
    write_json(OUTPUT / "10_FINAL_REPORT" / "FINAL_CLUSTER_MIXING_GEOMETRY_REPORT.json", final)
    report = ["# Cluster-level mixing geometry analysis", "", f"Final classification: **{final_case} — {case_labels[final_case]}**.", "", "## Cohort verdicts", "", f"- Revised Core-10: {cohort_classes['REVISED_CORE10_NATIVE']}", f"- Exclude-Chameleon Core-9: {cohort_classes['REVISED_CORE9_NO_CHAMELEON']}", "", "## Comparator classifications", ""]
    for r in main_class.itertuples(index=False): report.append(f"- {r.comparator}: {r.classification} ({r.concentration_metrics_favorable}/8 concentration metrics favorable)")
    report += ["", "## Required answers", ""]
    for key, value in answers.items(): report += [f"### {key}", "", json.dumps(value, ensure_ascii=False), ""]
    report += ["## Boundary", "", "All findings are exploratory. The analysis does not establish causality, rerun models, repair labels, or change authoritative evidence.", ""]
    (OUTPUT / "10_FINAL_REPORT" / "FINAL_CLUSTER_MIXING_GEOMETRY_REPORT.md").write_text("\n".join(report), encoding="utf-8")
    if final_case == "M-A": recommendation = "Reduced fragmentation and broadly reduced inter-class mixing may be discussed as an exploratory structural pattern."
    elif final_case == "M-B": recommendation = "Use localized residual mixing, not uniform mixing reduction, and keep the interpretation exploratory."
    elif final_case == "M-C": recommendation = "Keep fragmentation as the primary structural finding; present Homogeneity/mixing as heterogeneous supportive analysis."
    else: recommendation = "Do not place Homogeneity in the mechanism main line."
    (OUTPUT / "10_FINAL_REPORT" / "PAPER_NARRATIVE_RECOMMENDATION.md").write_text("# Paper narrative recommendation\n\n" + recommendation + "\n\nNo manuscript was modified.\n", encoding="utf-8")

    primary_keys = {
        "01_INPUT_AUDIT/INPUT_IDENTITY_AUDIT.csv": ["dataset", "pool", "method"],
        "02_CLUSTER_LEVEL_METRICS/CLUSTER_LEVEL_METRICS.csv": ["dataset", "pool", "method", "predicted_cluster_label"],
        "02_CLUSTER_LEVEL_METRICS/PREDICTION_LEVEL_SUMMARY.csv": ["dataset", "pool", "method"],
        "03_DATASET_LEVEL_SUMMARY/DATASET_LEVEL_MEANS.csv": ["cohort", "dataset", "method"],
        "04_COMPARATOR_PROFILES/COMPARATOR_PROFILES.csv": ["cohort", "metric", "comparator"],
        "04_COMPARATOR_PROFILES/COMPARATOR_MECHANISM_CLASSIFICATION.csv": ["cohort", "comparator"],
        "07_FRAGMENTATION_MIXING_JOINT/PARTITION_GEOMETRY_JOINT_SUMMARY.csv": ["cohort", "comparator"],
        "08_STATISTICS/EXPLORATORY_WILCOXON_HOLM.csv": ["cohort", "metric", "comparator"],
    }
    key_audit = []
    for relative, keys in primary_keys.items():
        frame = pd.read_csv(OUTPUT / relative)
        key_audit.append({"file": relative, "rows": len(frame), "keys": "|".join(keys), "duplicates": int(frame.duplicated(keys).sum())})
    key_audit_frame = pd.DataFrame(key_audit)
    key_audit_frame.to_csv(OUTPUT / "09_VALIDATION" / "CSV_PRIMARY_KEY_AUDIT.csv", index=False, encoding="utf-8-sig")
    if key_audit_frame.duplicates.sum() != 0: raise RuntimeError("Duplicate primary keys")
    if len(clusters) != int(summaries.returned_k.sum()): raise RuntimeError("Cluster row count mismatch")

    validation = {
        "schema": "psfce-cluster-mixing-geometry-validation-v1", "status": "PASS_WITH_REPRODUCTION_WARNING" if reproduction_failure else "PASS",
        "model_runs_performed": 0, "predictions_modified": 0, "labels_repaired": 0,
        "core10_prediction_rows": len(summaries), "core9_prediction_rows": len(core9_summaries), "cluster_rows": len(clusters),
        "coverage": "PASS", "hash_identity": "PASS", "returned_k_cluster_count": "PASS",
        "input_metric_reproduction_max_abs_error": float(reproduction.max_abs_difference.max()),
        "input_metric_reproduction_status": "INPUT_METRIC_REPRODUCTION_FAILURE" if reproduction_failure else "PASS",
        "duplicate_primary_key_status": "PASS", "core10_native_mcla_chameleon_under_k_preserved": True,
        "versions": {"python": sys.version, "platform": platform.platform(), "numpy": np.__version__, "pandas": pd.__version__, "scipy": scipy.__version__, "sklearn": sklearn.__version__},
        "not_verified": ["Causal mechanism", "Generality beyond revised Core-10/Core-9", "Historical METIS byte identity"],
    }
    write_json(OUTPUT / "09_VALIDATION" / "VALIDATION_REPORT.json", validation)
    write_json(OUTPUT / "00_PROTOCOL" / "PACKAGE_MANIFEST.json", {
        "schema": "psfce-cluster-mixing-geometry-package-v1", "created_at": datetime.now(timezone.utc).isoformat(),
        "analysis_status": "EXPLORATORY_NOT_CONFIRMATORY", "source_provenance": str(EXP1 / "INPUT_PROVENANCE.csv"),
        "source_provenance_sha256": sha256_file(EXP1 / "INPUT_PROVENANCE.csv"), "user_protocol_sha256": sha256_file(PROMPT),
        "final_case": final_case, "final_label": case_labels[final_case],
    })
    files = sorted(p for p in OUTPUT.rglob("*") if p.is_file() and p.name != "SHA256SUMS.txt" and "__pycache__" not in p.parts)
    (OUTPUT / "SHA256SUMS.txt").write_text("\n".join(f"{sha256_file(p)}  {p.relative_to(OUTPUT).as_posix()}" for p in files) + "\n", encoding="utf-8")
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for p in sorted(p for p in OUTPUT.rglob("*") if p.is_file() and "__pycache__" not in p.parts):
            archive.write(p, arcname=(Path(OUTPUT.name) / p.relative_to(OUTPUT)).as_posix())
    with zipfile.ZipFile(ZIP_PATH, "r") as archive:
        bad = archive.testzip()
        if bad is not None: raise RuntimeError(f"ZIP failure: {bad}")
        members = len(archive.infolist())
    sidecar = {"status": validation["status"], "zip": str(ZIP_PATH), "zip_sha256": sha256_file(ZIP_PATH), "zip_members": members, "final_case": final_case, "final_label": case_labels[final_case]}
    write_json(ZIP_PATH.with_suffix(".zip.validation.json"), sidecar)
    print(json.dumps({**sidecar, "cohort_classes": cohort_classes, "profile_counts": cohort_counts}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
