from __future__ import annotations

import hashlib
import json
import math
import os
import platform
import shutil
import sys
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
from scipy.stats import wilcoxon
import sklearn
from sklearn.metrics import adjusted_mutual_info_score


OUTPUT_TEXT = os.environ.get("PSFCE_EXP3_OUTPUT_ROOT")
PART1_TEXT = os.environ.get("PSFCE_EXP3_PART1_INPUT")
PART2_TEXT = os.environ.get("PSFCE_EXP3_PART2_INPUT")
PROMPT_TEXT = os.environ.get("PSFCE_EXP3_PROTOCOL_FILE")
if not all((OUTPUT_TEXT, PART1_TEXT, PART2_TEXT, PROMPT_TEXT)):
    raise SystemExit(
        "This archival analysis requires private frozen inputs. Set "
        "PSFCE_EXP3_OUTPUT_ROOT, PSFCE_EXP3_PART1_INPUT, "
        "PSFCE_EXP3_PART2_INPUT, and PSFCE_EXP3_PROTOCOL_FILE. "
        "The public repository intentionally omits predictions and raw labels."
    )
ROOT = Path(OUTPUT_TEXT).expanduser().resolve()
PART1 = Path(PART1_TEXT).expanduser().resolve()
PART2 = Path(PART2_TEXT).expanduser().resolve()
PROMPT = Path(PROMPT_TEXT).expanduser().resolve()
EXTERNAL = ["MCLA", "HBGF", "CEHM", "YACHT", "RANGE", "GPEC"]
OURS = "PSF-CE"
METHODS = EXTERNAL + [OURS]
TOL = 1e-12
REPRO_TOL = 1e-10
SEED = 20260919


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_i32(values: np.ndarray) -> str:
    return hashlib.sha256(np.asarray(values, dtype=np.int32).reshape(-1).tobytes(order="C")).hexdigest()


def write_json(path: Path, obj: object) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def load_prediction(path: Path) -> np.ndarray:
    if path.suffix.lower() == ".npz":
        with np.load(path, allow_pickle=False) as payload:
            return np.asarray(payload["labels"], dtype=np.int32).reshape(-1)
    if path.suffix.lower() == ".mat":
        with h5py.File(path, "r") as handle:
            return np.asarray(handle["result"]["predicted_labels"], dtype=np.int32).ravel(order="F")
    raise ValueError(f"Unsupported prediction file: {path}")


def load_truth(path: Path) -> np.ndarray:
    with np.load(path, allow_pickle=False) as payload:
        return np.asarray(payload["y"], dtype=np.int32).reshape(-1)


def entropy(probabilities: np.ndarray) -> float:
    p = np.asarray(probabilities, dtype=float)
    p = p[p > 0]
    return float(-np.sum(p * np.log(p)))


def metrics_and_classes(y: np.ndarray, z: np.ndarray) -> tuple[dict[str, object], list[dict[str, object]]]:
    y_values, yi = np.unique(np.asarray(y), return_inverse=True)
    z_values, zi = np.unique(np.asarray(z), return_inverse=True)
    counts = np.zeros((len(y_values), len(z_values)), dtype=np.int64)
    np.add.at(counts, (yi, zi), 1)
    n = int(counts.sum())
    joint = counts / float(n)
    py = joint.sum(axis=1)
    pz = joint.sum(axis=0)
    h_y = entropy(py)
    h_z = entropy(pz)
    h_yz = entropy(joint.reshape(-1))
    mi = float(h_y + h_z - h_yz)
    # Clip only floating residuals around zero; no substantive endpoint is altered.
    if abs(mi) <= 1e-14:
        mi = 0.0
    h_z_given_y = float(h_yz - h_y)
    h_y_given_z = float(h_yz - h_z)
    nmi = float(2.0 * mi / (h_y + h_z)) if h_y + h_z > 0 else 1.0
    homogeneity = float(mi / h_y) if h_y > 0 else 1.0
    completeness = float(mi / h_z) if h_z > 0 else 1.0
    class_rows: list[dict[str, object]] = []
    class_entropies = []
    class_effective = []
    for idx, label in enumerate(y_values):
        row_counts = counts[idx].astype(float)
        size = int(row_counts.sum())
        conditional = row_counts / float(size)
        ordered = np.sort(conditional)[::-1]
        h_class = entropy(conditional)
        effective = float(np.exp(h_class))
        class_entropies.append(h_class)
        class_effective.append(effective)
        class_rows.append({
            "true_class": int(label),
            "class_size": size,
            "H_Z_given_Y_class": h_class,
            "effective_fragments": effective,
            "occupied_predicted_clusters": int(np.count_nonzero(row_counts)),
            "dominant_predicted_cluster_share": float(ordered[0]),
            "second_largest_predicted_cluster_share": float(ordered[1]) if len(ordered) > 1 else 0.0,
        })
    cluster_sizes = counts.sum(axis=0).astype(int)
    cluster_props = cluster_sizes / float(n)
    target_c = len(y_values)
    metrics = {
        "n": n,
        "number_of_true_classes": target_c,
        "number_of_predicted_clusters": len(z_values),
        "H_Y": h_y,
        "H_Z": h_z,
        "H_YZ": h_yz,
        "MI": mi,
        "H_Z_given_Y": h_z_given_y,
        "H_Y_given_Z": h_y_given_z,
        "NMI": nmi,
        "AMI": float(adjusted_mutual_info_score(y, z, average_method="arithmetic")),
        "homogeneity": homogeneity,
        "completeness": completeness,
        "effective_partition_size": float(np.exp(h_z)),
        "normalized_H_Z": float(h_z / np.log(target_c)) if target_c > 1 else 0.0,
        "macro_class_fragmentation": float(np.mean(class_entropies)),
        "macro_effective_fragments": float(np.mean(class_effective)),
        "min_cluster_proportion": float(np.min(cluster_props)),
        "max_cluster_proportion": float(np.max(cluster_props)),
        "cluster_sizes_json": json.dumps(cluster_sizes.tolist(), separators=(",", ":")),
        "cluster_proportions_json": json.dumps(cluster_props.tolist(), separators=(",", ":")),
    }
    return metrics, class_rows


def nmi_f(mi: float, h_y: float, h_z: float) -> float:
    denom = h_y + h_z
    return float(2.0 * mi / denom) if denom > 0 else 1.0


def shapley_attribution(base: pd.Series, psf: pd.Series) -> tuple[float, float, float]:
    i_b, h_b = float(base.MI), float(base.H_Z)
    i_p, h_p = float(psf.MI), float(psf.H_Z)
    h_y = float(psf.H_Y)
    phi_i = 0.5 * (nmi_f(i_p, h_y, h_b) - nmi_f(i_b, h_y, h_b)) + 0.5 * (
        nmi_f(i_p, h_y, h_p) - nmi_f(i_b, h_y, h_p)
    )
    phi_h = 0.5 * (nmi_f(i_b, h_y, h_p) - nmi_f(i_b, h_y, h_b)) + 0.5 * (
        nmi_f(i_p, h_y, h_p) - nmi_f(i_p, h_y, h_b)
    )
    delta = nmi_f(i_p, h_y, h_p) - nmi_f(i_b, h_y, h_b)
    return float(phi_i), float(phi_h), float(delta)


def holm_adjust(values: list[float]) -> list[float]:
    p = np.asarray(values, dtype=float)
    order = np.argsort(p)
    ranked = np.maximum.accumulate((len(p) - np.arange(len(p))) * p[order])
    ranked = np.minimum(ranked, 1.0)
    out = np.empty_like(ranked)
    out[order] = ranked
    return out.tolist()


def wtl(values: np.ndarray, favorable: str) -> tuple[int, int, int]:
    arr = np.asarray(values, dtype=float)
    ties = int(np.sum(np.abs(arr) <= TOL))
    if favorable == "negative":
        wins = int(np.sum(arr < -TOL))
        losses = int(np.sum(arr > TOL))
    else:
        wins = int(np.sum(arr > TOL))
        losses = int(np.sum(arr < -TOL))
    return wins, ties, losses


def wilcoxon_two_sided(values: np.ndarray) -> tuple[float, float, int]:
    # Pandas/NumPy may expose a read-only view; copy before applying the
    # preregistered tie tolerance. This changes mutability only, not values.
    arr = np.asarray(values, dtype=float).copy()
    arr[np.abs(arr) <= TOL] = 0.0
    nonzero = int(np.count_nonzero(arr))
    if nonzero == 0:
        return 0.0, 1.0, 0
    result = wilcoxon(arr, zero_method="wilcox", alternative="two-sided")
    return float(result.statistic), float(result.pvalue), nonzero


def markdown_table(frame: pd.DataFrame, columns: list[str]) -> str:
    view = frame[columns].copy()
    for col in view.columns:
        if pd.api.types.is_float_dtype(view[col]):
            view[col] = view[col].map(lambda x: "NA" if pd.isna(x) else f"{x:.6g}")
    header = "| " + " | ".join(view.columns) + " |"
    sep = "| " + " | ".join(["---"] * len(view.columns)) + " |"
    rows = ["| " + " | ".join(str(v) for v in row) + " |" for row in view.itertuples(index=False, name=None)]
    return "\n".join([header, sep] + rows)


def run_unit_tests() -> dict[str, object]:
    results: list[dict[str, object]] = []

    def record(name: str, passed: bool, detail: object) -> None:
        results.append({"name": name, "status": "PASS" if passed else "FAIL", "detail": detail})

    y = np.repeat(np.arange(3), 4)
    z = y.copy()
    m, classes = metrics_and_classes(y, z)
    record(
        "perfect_clustering",
        abs(float(m["H_Z_given_Y"])) <= TOL
        and max(abs(float(x["effective_fragments"]) - 1.0) for x in classes) <= TOL
        and abs(float(m["AMI"]) - 1.0) <= TOL
        and abs(float(m["NMI"]) - 1.0) <= TOL,
        {k: m[k] for k in ["H_Z_given_Y", "AMI", "NMI"]},
    )

    y_frag = np.array([0] * 8 + [1] * 8, dtype=np.int32)
    z_frag = np.array([0] * 4 + [1] * 4 + [2] * 8, dtype=np.int32)
    _, class_frag = metrics_and_classes(y_frag, z_frag)
    first = next(x for x in class_frag if x["true_class"] == 0)
    record(
        "artificial_fragmentation",
        abs(float(first["H_Z_given_Y_class"]) - math.log(2.0)) <= TOL
        and abs(float(first["effective_fragments"]) - 2.0) <= TOL,
        first,
    )

    rng = np.random.default_rng(SEED)
    y_perm = rng.integers(0, 5, size=500, dtype=np.int32)
    z_perm = rng.integers(0, 5, size=500, dtype=np.int32)
    before, before_classes = metrics_and_classes(y_perm, z_perm)
    mapping = np.array([3, 1, 4, 0, 2], dtype=np.int32)
    after, after_classes = metrics_and_classes(y_perm, mapping[z_perm])
    fields = ["H_Z", "H_Z_given_Y", "MI", "NMI", "AMI", "macro_class_fragmentation", "macro_effective_fragments"]
    residual = max(abs(float(before[k]) - float(after[k])) for k in fields)
    class_residual = max(
        abs(float(a["effective_fragments"]) - float(b["effective_fragments"]))
        for a, b in zip(before_classes, after_classes)
    )
    record("cluster_label_permutation_invariance", max(residual, class_residual) <= TOL, {"max_residual": max(residual, class_residual)})

    identity_residuals = []
    for _ in range(100):
        counts = rng.integers(0, 25, size=(rng.integers(2, 8), rng.integers(2, 8)))
        if counts.sum() == 0:
            counts[0, 0] = 1
        y_vals = []
        z_vals = []
        for i in range(counts.shape[0]):
            for j in range(counts.shape[1]):
                y_vals.extend([i] * int(counts[i, j]))
                z_vals.extend([j] * int(counts[i, j]))
        metric, _ = metrics_and_classes(np.asarray(y_vals), np.asarray(z_vals))
        other = metric.copy()
        other["MI"] = max(0.0, float(metric["MI"]) * float(rng.uniform(0.3, 1.7)))
        other["H_Z"] = max(1e-6, float(metric["H_Z"]) * float(rng.uniform(0.3, 1.7)))
        base = pd.Series(metric)
        psf = pd.Series(other)
        phi_i, phi_h, delta = shapley_attribution(base, psf)
        identity_residuals.append(abs(delta - phi_i - phi_h))
    record("shapley_identity_random_tables", max(identity_residuals) < 1e-10, {"max_residual": max(identity_residuals), "n": 100})

    passed = all(item["status"] == "PASS" for item in results)
    return {"status": "PASS" if passed else "FAIL", "tests": results}


def save_figure(fig: plt.Figure, stem: str) -> None:
    fig.tight_layout()
    fig.savefig(ROOT / "figures" / f"{stem}.pdf", bbox_inches="tight")
    fig.savefig(ROOT / "figures" / f"{stem}.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def make_figures(dataset_deltas: pd.DataFrame, class_summary: pd.DataFrame) -> list[str]:
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "pdf.fonttype": 42, "ps.fonttype": 42})
    created: list[str] = []

    heat = dataset_deltas.pivot(index="dataset", columns="comparator", values="fraction_classes_lower_effective_fragments")
    heat = heat.reindex(index=CONFIG["cohort_order"], columns=EXTERNAL)
    heat.to_csv(ROOT / "figures" / "figure1_class_fragmentation_consistency_data.csv", encoding="utf-8-sig")
    fig, ax = plt.subplots(figsize=(6.8, 4.2))
    image = ax.imshow(heat.values, vmin=0.0, vmax=1.0, cmap="RdYlGn", aspect="auto")
    ax.set_xticks(range(len(EXTERNAL)), EXTERNAL, rotation=30, ha="right")
    ax.set_yticks(range(len(heat.index)), heat.index)
    ax.set_title("Fraction of true classes less fragmented under PSF-CE")
    for i in range(heat.shape[0]):
        for j in range(heat.shape[1]):
            ax.text(j, i, f"{heat.iloc[i, j]:.2f}", ha="center", va="center", fontsize=7)
    fig.colorbar(image, ax=ax, label="class fraction")
    save_figure(fig, "figure1_true_class_fragmentation_heatmap")
    created.append("figure1_true_class_fragmentation_heatmap")

    dataset_deltas.to_csv(ROOT / "figures" / "figure2_conditional_entropy_scatter_data.csv", index=False, encoding="utf-8-sig")
    fig, ax = plt.subplots(figsize=(5.4, 4.6))
    for comparator in EXTERNAL:
        part = dataset_deltas[dataset_deltas.comparator == comparator]
        ax.scatter(part.baseline_H_Z_given_Y, part.PSF_H_Z_given_Y, s=25, alpha=0.8, label=comparator)
    lim = max(float(dataset_deltas.baseline_H_Z_given_Y.max()), float(dataset_deltas.PSF_H_Z_given_Y.max())) * 1.04
    ax.plot([0, lim], [0, lim], color="black", linewidth=0.8, linestyle="--")
    ax.set(xlabel="Baseline H(Z|Y)", ylabel="PSF-CE H(Z|Y)", xlim=(0, lim), ylim=(0, lim), title="Dataset-level conditional entropy")
    ax.legend(fontsize=7, ncol=2)
    save_figure(fig, "figure2_psf_vs_baseline_conditional_entropy")
    created.append("figure2_psf_vs_baseline_conditional_entropy")

    positive = dataset_deltas[dataset_deltas.delta_NMI > TOL]
    bar = positive.groupby("comparator", sort=False)[["phi_MI", "phi_entropy"]].mean().reindex(EXTERNAL).reset_index()
    bar["positive_delta_nmi_n"] = positive.groupby("comparator").size().reindex(EXTERNAL).fillna(0).astype(int).values
    bar.to_csv(ROOT / "figures" / "figure3_nmi_contribution_data.csv", index=False, encoding="utf-8-sig")
    fig, ax = plt.subplots(figsize=(6.2, 3.8))
    x = np.arange(len(EXTERNAL))
    ax.bar(x - 0.18, bar.phi_MI, width=0.36, label=r"$\phi_I$", color="#2f7ed8")
    ax.bar(x + 0.18, bar.phi_entropy, width=0.36, label=r"$\phi_H$", color="#f28e2b")
    ax.axhline(0, color="black", linewidth=0.7)
    ax.set_xticks(x, [f"{c}\n(n={n})" for c, n in zip(bar.comparator, bar.positive_delta_nmi_n)])
    ax.set_ylabel("Mean contribution to ΔNMI")
    ax.set_title("Algebraic attribution within positive-ΔNMI comparisons")
    ax.legend()
    save_figure(fig, "figure3_nmi_contribution_decomposition")
    created.append("figure3_nmi_contribution_decomposition")

    dataset_deltas[["dataset", "comparator", "delta_NMI", "delta_H_Z_given_Y"]].to_csv(
        ROOT / "figures" / "figure4_delta_nmi_vs_fragmentation_data.csv", index=False, encoding="utf-8-sig"
    )
    fig, ax = plt.subplots(figsize=(5.4, 4.3))
    for comparator in EXTERNAL:
        part = dataset_deltas[dataset_deltas.comparator == comparator]
        ax.scatter(part.delta_H_Z_given_Y, part.delta_NMI, s=25, alpha=0.8, label=comparator)
    ax.axhline(0, color="black", linewidth=0.7)
    ax.axvline(0, color="black", linewidth=0.7)
    ax.set(xlabel="ΔH(Z|Y): PSF-CE − baseline", ylabel="ΔNMI: PSF-CE − baseline", title="NMI difference and true-class fragmentation")
    ax.legend(fontsize=7, ncol=2)
    save_figure(fig, "figure4_delta_nmi_vs_fragmentation")
    created.append("figure4_delta_nmi_vs_fragmentation")

    dataset_deltas[["dataset", "comparator", "delta_NMI", "delta_AMI"]].to_csv(
        ROOT / "figures" / "figure5_delta_ami_vs_nmi_data.csv", index=False, encoding="utf-8-sig"
    )
    fig, ax = plt.subplots(figsize=(5.4, 4.3))
    for comparator in EXTERNAL:
        part = dataset_deltas[dataset_deltas.comparator == comparator]
        ax.scatter(part.delta_NMI, part.delta_AMI, s=25, alpha=0.8, label=comparator)
    lo = min(float(dataset_deltas.delta_NMI.min()), float(dataset_deltas.delta_AMI.min()))
    hi = max(float(dataset_deltas.delta_NMI.max()), float(dataset_deltas.delta_AMI.max()))
    ax.plot([lo, hi], [lo, hi], color="black", linewidth=0.8, linestyle="--")
    ax.axhline(0, color="grey", linewidth=0.6)
    ax.axvline(0, color="grey", linewidth=0.6)
    ax.set(xlabel="ΔNMI", ylabel="ΔAMI", title="Chance-adjusted and unadjusted differences")
    ax.legend(fontsize=7, ncol=2)
    save_figure(fig, "figure5_delta_ami_vs_nmi")
    created.append("figure5_delta_ami_vs_nmi")
    return created


def build_report(
    statistics: pd.DataFrame,
    profile: pd.DataFrame,
    h3c: dict[str, object],
    verdicts: dict[str, object],
    reproduction: dict[str, object],
) -> str:
    stats_view = statistics[["metric", "comparator", "mean_delta", "median_delta", "wins", "ties", "losses", "raw_p", "holm_p"]]
    lines = [
        "# Experiment 3 — Partition Fragmentation and Entropy Decomposition",
        "",
        "## Status and boundary",
        "",
        f"This is an exploratory, analysis-only recomputation over the native saved predictions for {CONFIG['cohort_label']}. No clustering method was rerun, no label was repaired, and no seed, comparator, metric, or decision gate was changed.",
        "",
        f"- Source/hash integrity: **{reproduction['source_integrity_status']}**",
        f"- Experiment 1 metric reproduction: **{reproduction['experiment1_reproduction_status']}** (max absolute error `{reproduction['max_abs_reproduction_error']:.3e}`)",
        f"- Unit tests: **{reproduction['unit_test_status']}**",
        f"- Statistical unit: dataset mean after averaging three frozen pools (n={len(CONFIG['cohort_order'])}), not {len(CONFIG['cohort_order']) * 3} independent pools.",
        f"- Entropy logarithm: natural.",
        f"- AMI implementation: sklearn adjusted_mutual_info_score, average_method='arithmetic' (sklearn {sklearn.__version__}).",
        "",
        "Lower H(Z|Y) is interpreted narrowly as lower reference-class conditional dispersion. It is not by itself a quality guarantee: cluster-size imbalance or collapse can also lower entropy-related quantities. AMI is chance-adjusted under its null model; it does not fully remove all marginal effects.",
        "",
        "## Prespecified-gate outcomes (exploratory)",
        "",
        f"- H3-A reduced-fragmentation profile: **{verdicts['H3_A']['status']}** ({verdicts['H3_A']['favorable_comparators']}/6 comparator medians favorable).",
        f"- H3-B macro/class-level consistency: **{verdicts['H3_B']['status']}** ({verdicts['H3_B']['favorable_comparators']}/6).",
        f"- AMI profile: **{verdicts['AMI_profile']['status']}** ({verdicts['AMI_profile']['favorable_comparators']}/6).",
        f"- MI profile: **{verdicts['MI_profile']['status']}** ({verdicts['MI_profile']['favorable_comparators']}/6).",
        f"- Final deterministic interpretation: **{verdicts['final_case']}** — {verdicts['final_interpretation']}",
        "",
        "The primary H3-A/H3-B verdicts follow the preregistered comparator-level median-direction gates. Wilcoxon tests are supporting evidence and do not override those gates.",
        "",
        "## Comparator profiles",
        "",
        markdown_table(profile, ["metric", "comparator", "mean_delta", "median_delta", "wins", "ties", "losses", "favorable"]),
        "",
        "## Paired Wilcoxon tests",
        "",
        "Holm correction is applied separately within each metric's six-comparator family.",
        "",
        markdown_table(stats_view, list(stats_view.columns)),
        "",
        "## NMI algebraic attribution",
        "",
        f"Among {h3c['positive_delta_nmi_count']} of {len(CONFIG['cohort_order']) * len(EXTERNAL)} dataset-by-comparator comparisons with ΔNMI > 1e-12: φ_I>0 in {h3c['phi_MI_positive_fraction']:.3f}, φ_H>0 in {h3c['phi_entropy_positive_fraction']:.3f}, |φ_I|>|φ_H| in {h3c['MI_abs_dominant_fraction']:.3f}, and |φ_H|>|φ_I| in {h3c['entropy_abs_dominant_fraction']:.3f}.",
        "",
        f"Descriptive classification: **{h3c['classification']}**.",
        "",
        "This is an exact algebraic attribution for the chosen f(I,H_Z)=2I/(H(Y)+H_Z) parameterization. The mixed counterfactual points need not correspond to realizable partitions. The positive-ΔNMI subset is outcome-conditioned; its percentages are descriptive and are not independent significance evidence.",
        "",
        "## Cross-experiment synthesis",
        "",
        "This run reuses the previously specified Experiment 3 metrics, delta orientation, dataset-level statistical unit, Holm families, and directional gates. It does not import an Experiment 2 scientific verdict. The native-output Core-10 variant permits the two source-verified Chameleon/MCLA under-k rows; the Core-9 sensitivity variant removes Chameleon entirely. These observational analyses do not establish a causal mechanism.",
        "",
        "## Publication boundary",
        "",
        "Exploratory only: these outputs do not replace the authoritative frozen analysis or update the paper claims contract. Report both cohort variants together and retain the native under-k record. Do not write 'proves', 'demonstrates the mechanism', 'preserves more information', or imply that entropy reduction is necessarily beneficial.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    protected = [ROOT / "metrics_full.csv", ROOT / "RUN_COMPLETION.json"]
    if any(path.exists() for path in protected):
        raise RuntimeError("Refusing to overwrite an existing exploratory Experiment 3 run.")
    (ROOT / "figures").mkdir(parents=True, exist_ok=True)
    part1_config = json.loads((PART1 / "RUN_CONFIG.json").read_text(encoding="utf-8"))
    core10 = list(part1_config["cohort_order"])
    cohort_label = str(part1_config["cohort_label"])
    if part1_config["external_comparators"] != EXTERNAL:
        raise RuntimeError("Experiment 1 external comparator set differs from the frozen Experiment 3 set.")
    global CONFIG
    CONFIG = {
        "schema": "psfce-experiment3-partition-fragmentation-exploratory-v1",
        "protocol_id": str(part1_config["exploratory_protocol_id"]),
        "stage": "POST_HOC_EXPLORATORY_NATIVE_OUTPUT_ANALYSIS",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "experiment": f"Experiment 3 — Partition Fragmentation and Entropy Decomposition ({cohort_label}; exploratory)",
        "analysis_status": "EXPLORATORY_NOT_CONFIRMATORY",
        "cohort_label": cohort_label,
        "analysis_only": True,
        "model_runs_performed": 0,
        "cohort_order": core10,
        "external_comparators": EXTERNAL,
        "our_method": OURS,
        "methods_analyzed": METHODS,
        "pools_per_dataset": 3,
        "statistical_unit": "dataset mean after averaging three frozen pools",
        "entropy_log_base": "natural",
        "ami": {"implementation": "sklearn.metrics.adjusted_mutual_info_score", "average_method": "arithmetic"},
        "tie_tolerance": TOL,
        "reproduction_tolerance": REPRO_TOL,
        "wilcoxon": {"alternative": "two-sided", "zero_method": "wilcox", "n_datasets": len(core10)},
        "holm_families": {
            "delta_H_Z_given_Y": 6,
            "delta_macro_fragmentation": 6,
            "delta_AMI": 6,
            "delta_MI": 6,
        },
        "frozen_gates": {
            "H3_A": "A comparator is favorable iff median delta_H_Z_given_Y < -1e-12; SUPPORTED iff >=4/6.",
            "H3_B": "A comparator is favorable iff median delta_macro_fragmentation < -1e-12; SUPPORTED iff >=4/6.",
            "AMI_profile": "A comparator is favorable iff median delta_AMI > 1e-12; SUPPORTED iff >=4/6.",
            "MI_profile": "A comparator is favorable iff median delta_MI > 1e-12; SUPPORTED iff >=4/6.",
            "H3_C": "Within outcome-conditioned dataset-comparator cases with delta_NMI>1e-12, label MI_DOMINANT if |phi_MI|>|phi_entropy| in >0.5 of cases, ENTROPY_DOMINANT if the reverse fraction is >0.5, otherwise MIXED_OR_TIED. Descriptive only.",
            "case_A": "H3-A SUPPORTED and MI profile SUPPORTED and AMI profile SUPPORTED.",
            "case_B": "H3-A SUPPORTED and Case A is false.",
            "case_C": "H3-A NOT SUPPORTED and H3-C is ENTROPY_DOMINANT.",
            "case_D": "All remaining outcomes.",
        },
        "construct_limits": [
            "Lower H(Z|Y) denotes lower reference-class conditional dispersion, not guaranteed clustering quality.",
            "AMI is chance-adjusted under its null model but does not remove all marginal effects.",
            "The Shapley-style split is exact for the chosen (MI,H_Z) parameterization; its mixed points need not be realizable partitions.",
            "H3-C conditions on positive delta_NMI and is descriptive, not independent confirmation.",
            "Class-level proportions are explanatory and are not treated as independent observations.",
        ],
        "versions": {
            "python": sys.version,
            "platform": platform.platform(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scipy": scipy.__version__,
            "matplotlib": matplotlib.__version__,
            "sklearn": sklearn.__version__,
            "h5py": h5py.__version__,
        },
        "source_files": {
            "experiment3_prompt": {"path": str(PROMPT), "sha256": sha256_file(PROMPT)},
            "experiment1_directory": str(PART1),
            "experiment2_directory": str(PART2),
            "experiment1_input_provenance_sha256": sha256_file(PART1 / "INPUT_PROVENANCE.csv"),
            "experiment1_pool_metrics_sha256": sha256_file(PART1 / "PART1_POOL_LEVEL_METRICS.csv"),
            "experiment2_provenance_audit_sha256": sha256_file(PART2 / "PART2_INPUT_PROVENANCE_AUDIT.csv"),
        },
    }
    write_json(ROOT / "config.json", CONFIG)

    unit_tests = run_unit_tests()
    write_json(ROOT / "unit_tests.json", unit_tests)
    if unit_tests["status"] != "PASS":
        raise RuntimeError("Unit tests failed; endpoint analysis stopped.")

    provenance_all = pd.read_csv(PART1 / "INPUT_PROVENANCE.csv")
    part2_audit = pd.read_csv(PART2 / "PART2_INPUT_PROVENANCE_AUDIT.csv")
    expected_all_rows = len(core10) * 3 * len(part1_config["all_methods"])
    if len(provenance_all) != expected_all_rows or provenance_all[["dataset", "pool", "method"]].duplicated().any():
        raise RuntimeError(f"Experiment 1 provenance is not the required unique {expected_all_rows}-row set.")
    if len(part2_audit) != expected_all_rows or not part2_audit["exploratory_input_valid"].astype(str).str.lower().eq("true").all():
        raise RuntimeError("Exploratory provenance audit is incomplete or contains failures beyond the explicitly permitted returned-k condition.")
    merged = provenance_all.merge(
        part2_audit[["dataset", "pool", "method", "prediction_file_sha256", "prediction_labels_sha256_int32_c"]],
        on=["dataset", "pool", "method"],
        suffixes=("_part1", "_part2"),
        validate="one_to_one",
    )
    cross_experiment_hash_match = (
        merged.prediction_file_sha256_part1.str.lower().eq(merged.prediction_file_sha256_part2.str.lower())
        & merged.prediction_labels_sha256_int32_c_part1.str.lower().eq(merged.prediction_labels_sha256_int32_c_part2.str.lower())
    )
    if not cross_experiment_hash_match.all():
        raise RuntimeError("Experiment 1/2 prediction hashes disagree.")
    provenance = provenance_all[provenance_all.method.isin(METHODS)].copy()
    expected_exploratory_rows = len(core10) * 3 * len(METHODS)
    if len(provenance) != expected_exploratory_rows or provenance[["dataset", "pool", "method"]].duplicated().any():
        raise RuntimeError(f"Exploratory external subset must contain {expected_exploratory_rows} unique predictions.")

    pool_rows: list[dict[str, object]] = []
    class_rows_all: list[dict[str, object]] = []
    provenance_rows: list[dict[str, object]] = []
    part1_metrics = pd.read_csv(PART1 / "PART1_POOL_LEVEL_METRICS.csv")
    part1_index = part1_metrics.set_index(["dataset", "pool", "method"])
    reproduction_rows: list[dict[str, object]] = []
    source_failures: list[dict[str, object]] = []

    for row in provenance.itertuples(index=False):
        key = (row.dataset, int(row.pool), row.method)
        true_path = Path(row.true_label_source_path)
        pred_path = Path(row.prediction_path)
        true_file_sha = sha256_file(true_path)
        pred_file_sha = sha256_file(pred_path)
        y = load_truth(true_path)
        z = load_prediction(pred_path)
        checks = {
            "true_file_sha_match": true_file_sha.lower() == str(row.true_label_source_file_sha256).lower(),
            "prediction_file_sha_match": pred_file_sha.lower() == str(row.prediction_file_sha256).lower(),
            "true_label_sha_match": sha256_i32(y).lower() == str(row.true_labels_sha256_int32_c).lower(),
            "prediction_label_sha_match": sha256_i32(z).lower() == str(row.prediction_labels_sha256_int32_c).lower(),
            "sample_count_match": len(y) == len(z) == int(row.n),
        }
        if not all(checks.values()):
            source_failures.append({"dataset": row.dataset, "pool": int(row.pool), "method": row.method, **checks})
            continue
        metric, class_rows = metrics_and_classes(y, z)
        pool_rows.append({
            "dataset": row.dataset,
            "pool": int(row.pool),
            "method": row.method,
            "method_role": row.method_role,
            **metric,
            "prediction_labels_sha256_int32_c": row.prediction_labels_sha256_int32_c,
        })
        for class_row in class_rows:
            class_rows_all.append({"dataset": row.dataset, "pool": int(row.pool), "method": row.method, **class_row})
        prior = part1_index.loc[key]
        reproduction_rows.append({
            "dataset": row.dataset,
            "pool": int(row.pool),
            "method": row.method,
            "delta_NMI": float(metric["NMI"]) - float(prior.NMI),
            "delta_homogeneity": float(metric["homogeneity"]) - float(prior.homogeneity),
            "delta_completeness": float(metric["completeness"]) - float(prior.completeness),
        })
        provenance_rows.append({
            "dataset": row.dataset,
            "method": row.method,
            "run": int(row.pool),
            "source_experiment": "Experiment 1 provenance; hashes cross-verified against the copied provenance audit",
            "prediction_file": str(pred_path),
            "prediction_file_sha256": pred_file_sha,
            "prediction_labels_sha256_int32_c": sha256_i32(z),
            "ground_truth_file": str(true_path),
            "ground_truth_file_sha256": true_file_sha,
            "ground_truth_labels_sha256_int32_c": sha256_i32(y),
            "sample_count": len(y),
            "number_of_true_classes": int(np.unique(y).size),
            "number_of_predicted_clusters": int(np.unique(z).size),
        })

    if source_failures:
        pd.DataFrame(source_failures).to_csv(ROOT / "SOURCE_INTEGRITY_FAILURES.csv", index=False, encoding="utf-8-sig")
        raise RuntimeError("Prediction or ground-truth source integrity failed.")

    reproduction = pd.DataFrame(reproduction_rows)
    reproduction["max_abs_error"] = reproduction[["delta_NMI", "delta_homogeneity", "delta_completeness"]].abs().max(axis=1)
    reproduction.to_csv(ROOT / "experiment1_reproduction.csv", index=False, encoding="utf-8-sig")
    max_repro = float(reproduction.max_abs_error.max())
    if max_repro > REPRO_TOL:
        raise RuntimeError(f"Experiment 1 reproduction failed: max error {max_repro}")

    pd.DataFrame(provenance_rows).to_csv(ROOT / "prediction_provenance.csv", index=False, encoding="utf-8-sig")
    metrics_full = pd.DataFrame(pool_rows)
    class_full = pd.DataFrame(class_rows_all)
    metrics_full.to_csv(ROOT / "metrics_full.csv", index=False, encoding="utf-8-sig")
    class_full.to_csv(ROOT / "class_fragmentation.csv", index=False, encoding="utf-8-sig")
    numeric_metrics = [
        "n", "number_of_true_classes", "number_of_predicted_clusters", "H_Y", "H_Z", "H_YZ", "MI",
        "H_Z_given_Y", "H_Y_given_Z", "NMI", "AMI", "homogeneity", "completeness",
        "effective_partition_size", "normalized_H_Z", "macro_class_fragmentation",
        "macro_effective_fragments", "min_cluster_proportion", "max_cluster_proportion",
    ]
    dataset_metrics = metrics_full.groupby(["dataset", "method"], as_index=False)[numeric_metrics].mean()
    dataset_metrics.to_csv(ROOT / "metrics_dataset_means.csv", index=False, encoding="utf-8-sig")
    class_summary = class_full.groupby(["dataset", "method", "true_class"], as_index=False).agg(
        class_size=("class_size", "mean"),
        H_Z_given_Y_class=("H_Z_given_Y_class", "mean"),
        effective_fragments=("effective_fragments", "mean"),
        occupied_predicted_clusters=("occupied_predicted_clusters", "mean"),
        dominant_predicted_cluster_share=("dominant_predicted_cluster_share", "mean"),
        second_largest_predicted_cluster_share=("second_largest_predicted_cluster_share", "mean"),
    )
    class_summary.to_csv(ROOT / "class_fragmentation_dataset_means.csv", index=False, encoding="utf-8-sig")

    metric_index = metrics_full.set_index(["dataset", "pool", "method"])
    pool_delta_rows: list[dict[str, object]] = []
    for dataset in core10:
        for pool in range(3):
            psf = metric_index.loc[(dataset, pool, OURS)]
            for comparator in EXTERNAL:
                base = metric_index.loc[(dataset, pool, comparator)]
                phi_i, phi_h, reconstructed_delta = shapley_attribution(base, psf)
                observed_delta = float(psf.NMI - base.NMI)
                pool_delta_rows.append({
                    "dataset": dataset,
                    "pool": pool,
                    "comparator": comparator,
                    "delta_NMI": observed_delta,
                    "delta_AMI": float(psf.AMI - base.AMI),
                    "delta_MI": float(psf.MI - base.MI),
                    "delta_H_Z": float(psf.H_Z - base.H_Z),
                    "delta_H_Z_given_Y": float(psf.H_Z_given_Y - base.H_Z_given_Y),
                    "delta_macro_fragmentation": float(psf.macro_class_fragmentation - base.macro_class_fragmentation),
                    "delta_effective_fragments": float(psf.macro_effective_fragments - base.macro_effective_fragments),
                    "phi_MI": phi_i,
                    "phi_entropy": phi_h,
                    "shapley_identity_residual": observed_delta - phi_i - phi_h,
                    "PSF_H_Z_given_Y": float(psf.H_Z_given_Y),
                    "baseline_H_Z_given_Y": float(base.H_Z_given_Y),
                    "PSF_H_Z": float(psf.H_Z),
                    "baseline_H_Z": float(base.H_Z),
                    "PSF_MI": float(psf.MI),
                    "baseline_MI": float(base.MI),
                    "PSF_NMI": float(psf.NMI),
                    "baseline_NMI": float(base.NMI),
                    "PSF_AMI": float(psf.AMI),
                    "baseline_AMI": float(base.AMI),
                })
    pool_deltas = pd.DataFrame(pool_delta_rows)
    if float(pool_deltas.shapley_identity_residual.abs().max()) >= 1e-10:
        raise RuntimeError("Shapley attribution identity failed.")
    pool_deltas.to_csv(ROOT / "external_pairwise_deltas.csv", index=False, encoding="utf-8-sig")
    delta_numeric = [c for c in pool_deltas.columns if c not in ["dataset", "pool", "comparator"]]
    dataset_deltas = pool_deltas.groupby(["dataset", "comparator"], as_index=False)[delta_numeric].mean()

    class_lookup = class_summary.set_index(["dataset", "method", "true_class"])
    class_fraction_rows = []
    for dataset in core10:
        classes = sorted(class_summary[class_summary.dataset == dataset].true_class.unique())
        for comparator in EXTERNAL:
            diffs = []
            for label in classes:
                psf_eff = float(class_lookup.loc[(dataset, OURS, label)].effective_fragments)
                base_eff = float(class_lookup.loc[(dataset, comparator, label)].effective_fragments)
                diffs.append(psf_eff - base_eff)
            class_fraction_rows.append({
                "dataset": dataset,
                "comparator": comparator,
                "number_of_true_classes": len(classes),
                "classes_lower_effective_fragments": int(np.sum(np.asarray(diffs) < -TOL)),
                "classes_tied_effective_fragments": int(np.sum(np.abs(np.asarray(diffs)) <= TOL)),
                "classes_higher_effective_fragments": int(np.sum(np.asarray(diffs) > TOL)),
                "fraction_classes_lower_effective_fragments": float(np.mean(np.asarray(diffs) < -TOL)),
            })
    class_fractions = pd.DataFrame(class_fraction_rows)
    dataset_deltas = dataset_deltas.merge(class_fractions, on=["dataset", "comparator"], validate="one_to_one")
    dataset_deltas.to_csv(ROOT / "external_pairwise_dataset_deltas.csv", index=False, encoding="utf-8-sig")

    metric_specs = {
        "H_Z_given_Y": ("delta_H_Z_given_Y", "negative"),
        "macro_fragmentation": ("delta_macro_fragmentation", "negative"),
        "AMI": ("delta_AMI", "positive"),
        "MI": ("delta_MI", "positive"),
    }
    stats_rows = []
    profile_rows = []
    for metric, (column, direction) in metric_specs.items():
        raw_rows = []
        for comparator in EXTERNAL:
            values = dataset_deltas.loc[dataset_deltas.comparator == comparator, column].to_numpy(dtype=float)
            statistic, raw_p, nonzero = wilcoxon_two_sided(values)
            wins, ties, losses = wtl(values, direction)
            median = float(np.median(values))
            favorable = median < -TOL if direction == "negative" else median > TOL
            row = {
                "metric": metric,
                "comparator": comparator,
                "test": "paired Wilcoxon signed-rank, two-sided",
                "n": len(values),
                "nonzero_n": nonzero,
                "mean_delta": float(np.mean(values)),
                "median_delta": median,
                "wins": wins,
                "ties": ties,
                "losses": losses,
                "positive_count": int(np.sum(values > TOL)),
                "negative_count": int(np.sum(values < -TOL)),
                "zero_count": int(np.sum(np.abs(values) <= TOL)),
                "wilcoxon_statistic": statistic,
                "raw_p": raw_p,
                "favorable_direction": direction,
                "favorable": bool(favorable),
            }
            raw_rows.append(row)
            profile_rows.append({k: row[k] for k in ["metric", "comparator", "mean_delta", "median_delta", "wins", "ties", "losses", "favorable"]})
        adjusted = holm_adjust([row["raw_p"] for row in raw_rows])
        for row, holm_p in zip(raw_rows, adjusted):
            row["holm_p"] = holm_p
            stats_rows.append(row)
    statistics = pd.DataFrame(stats_rows)
    profile = pd.DataFrame(profile_rows)
    statistics.to_csv(ROOT / "statistics.csv", index=False, encoding="utf-8-sig")
    profile.to_csv(ROOT / "comparator_profiles.csv", index=False, encoding="utf-8-sig")

    profile_counts = profile.groupby("metric").favorable.sum().astype(int).to_dict()
    h3a_supported = profile_counts["H_Z_given_Y"] >= 4
    h3b_supported = profile_counts["macro_fragmentation"] >= 4
    ami_supported = profile_counts["AMI"] >= 4
    mi_supported = profile_counts["MI"] >= 4

    positive = dataset_deltas[dataset_deltas.delta_NMI > TOL].copy()
    positive_count = len(positive)
    if positive_count:
        h3c = {
            "positive_delta_nmi_count": positive_count,
            "phi_MI_positive_fraction": float(np.mean(positive.phi_MI > TOL)),
            "phi_entropy_positive_fraction": float(np.mean(positive.phi_entropy > TOL)),
            "MI_abs_dominant_fraction": float(np.mean(positive.phi_MI.abs() > positive.phi_entropy.abs() + TOL)),
            "entropy_abs_dominant_fraction": float(np.mean(positive.phi_entropy.abs() > positive.phi_MI.abs() + TOL)),
            "both_positive_fraction": float(np.mean((positive.phi_MI > TOL) & (positive.phi_entropy > TOL))),
            "MI_positive_entropy_negative_fraction": float(np.mean((positive.phi_MI > TOL) & (positive.phi_entropy < -TOL))),
            "entropy_positive_MI_negative_fraction": float(np.mean((positive.phi_entropy > TOL) & (positive.phi_MI < -TOL))),
        }
    else:
        h3c = {key: 0.0 for key in [
            "phi_MI_positive_fraction", "phi_entropy_positive_fraction", "MI_abs_dominant_fraction",
            "entropy_abs_dominant_fraction", "both_positive_fraction", "MI_positive_entropy_negative_fraction",
            "entropy_positive_MI_negative_fraction",
        ]}
        h3c["positive_delta_nmi_count"] = 0
    if h3c["MI_abs_dominant_fraction"] > 0.5:
        h3c["classification"] = "MI_DOMINANT"
    elif h3c["entropy_abs_dominant_fraction"] > 0.5:
        h3c["classification"] = "ENTROPY_DOMINANT"
    else:
        h3c["classification"] = "MIXED_OR_TIED"

    h3c_by_comparator = positive.groupby("comparator", as_index=False).agg(
        positive_delta_nmi_n=("delta_NMI", "size"),
        mean_phi_MI=("phi_MI", "mean"),
        median_phi_MI=("phi_MI", "median"),
        mean_phi_entropy=("phi_entropy", "mean"),
        median_phi_entropy=("phi_entropy", "median"),
    ).set_index("comparator").reindex(EXTERNAL).reset_index()
    h3c_by_comparator.to_csv(ROOT / "nmi_attribution_by_comparator.csv", index=False, encoding="utf-8-sig")

    if h3a_supported and mi_supported and ami_supported:
        final_case = "Case A"
        final_interpretation = "Reduced true-class fragmentation co-occurs with favorable MI and AMI profiles on this exploratory cohort."
    elif h3a_supported:
        final_case = "Case B"
        final_interpretation = "PSF-CE mainly reorganizes predictions toward lower reference-class fragmentation without stable joint MI and AMI increases."
    elif h3c["classification"] == "ENTROPY_DOMINANT":
        final_case = "Case C"
        final_interpretation = "The favorable NMI profile is more associated with predicted-partition entropy/marginal changes than robust fragmentation reduction."
    else:
        final_case = "Case D"
        final_interpretation = "No single general partition-structure mechanism is supported by these exploratory profiles."
    verdicts = {
        "H3_A": {"status": "SUPPORTED" if h3a_supported else "NOT_SUPPORTED", "favorable_comparators": profile_counts["H_Z_given_Y"], "threshold": ">=4/6 comparator medians < -1e-12"},
        "H3_B": {"status": "SUPPORTED" if h3b_supported else "NOT_SUPPORTED", "favorable_comparators": profile_counts["macro_fragmentation"], "threshold": ">=4/6 comparator medians < -1e-12"},
        "AMI_profile": {"status": "SUPPORTED" if ami_supported else "NOT_SUPPORTED", "favorable_comparators": profile_counts["AMI"], "threshold": ">=4/6 comparator medians > 1e-12"},
        "MI_profile": {"status": "SUPPORTED" if mi_supported else "NOT_SUPPORTED", "favorable_comparators": profile_counts["MI"], "threshold": ">=4/6 comparator medians > 1e-12"},
        "H3_C": h3c,
        "final_case": final_case,
        "final_interpretation": final_interpretation,
    }
    write_json(ROOT / "hypothesis_verdicts.json", verdicts)

    figures = make_figures(dataset_deltas, class_summary)
    reproduction_status = {
        "source_integrity_status": "PASS",
        "experiment1_experiment2_prediction_hash_identity": "PASS",
        "cross_experiment_rows_checked": expected_all_rows,
        "exploratory_prediction_rows_checked": expected_exploratory_rows,
        "experiment1_reproduction_status": "PASS",
        "max_abs_reproduction_error": max_repro,
        "reproduction_rows": len(reproduction),
        "unit_test_status": unit_tests["status"],
        "shapley_identity_status": "PASS",
        "max_abs_shapley_identity_residual": float(pool_deltas.shapley_identity_residual.abs().max()),
        "no_model_retraining": True,
    }
    write_json(ROOT / "integrity_and_reproduction_report.json", reproduction_status)
    report = build_report(statistics, profile, h3c, verdicts, reproduction_status)
    (ROOT / "experiment3_report.md").write_text(report, encoding="utf-8")

    readme = f"""# PSF-CE Experiment 3: Partition Fragmentation and Entropy Decomposition

This directory is an **exploratory, analysis-only** mechanism recomputation over copied provenance records and the exact native saved predictions. It performs **zero model training or clustering runs**, does not repair under-k labels, and does not replace the authoritative frozen analysis.

## Questions

1. Does PSF-CE exhibit lower true-class conditional dispersion H(Z|Y)?
2. Does the pattern remain under an unweighted macro average across true classes?
3. Are NMI differences algebraically associated more with MI changes or predicted-partition entropy changes?

## Reproduce

From this directory with the original prediction source paths still available:

```powershell
python scripts\\run_experiment3_exploratory.py
```

The command verifies all source hashes, unit tests, and Experiment 1 endpoint reproduction before mechanism endpoints are produced. It then writes fresh outputs into this directory and rebuilds the ZIP beside it.

## Prespecified analysis choices retained for this exploratory sensitivity analysis

- The cohort ({cohort_label}) and the six external comparators are loaded from the copied Experiment 1 provenance.
- Three pools are averaged before each dataset-level paired comparison.
- H3-A and H3-B use the prompt's comparator-median direction gates; |delta| <= {TOL:g} is a tie.
- Holm correction is separate for each four metric families.
- AMI uses sklearn `adjusted_mutual_info_score(..., average_method='arithmetic')`.
- H3-C is outcome-conditioned and descriptive.

See `config.json`, `hypothesis_verdicts.json`, and `experiment3_report.md` for the exact rules and conclusions.
"""
    (ROOT / "README.md").write_text(readme, encoding="utf-8")

    completion = {
        "schema": "psfce-experiment3-completion-v1",
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "status": "COMPLETE",
        "prediction_rows": len(provenance_rows),
        "pool_metric_rows": len(metrics_full),
        "class_pool_rows": len(class_full),
        "dataset_method_rows": len(dataset_metrics),
        "dataset_comparator_rows": len(dataset_deltas),
        "statistics_rows": len(statistics),
        "figures_png_pdf_pairs": len(figures),
        "H3_A": verdicts["H3_A"]["status"],
        "H3_B": verdicts["H3_B"]["status"],
        "AMI_profile": verdicts["AMI_profile"]["status"],
        "MI_profile": verdicts["MI_profile"]["status"],
        "H3_C": h3c["classification"],
        "final_case": final_case,
        "model_runs_performed": 0,
    }
    write_json(ROOT / "RUN_COMPLETION.json", completion)

    # Exclude the checksum manifest itself to avoid self-reference.
    files = sorted(
        p for p in ROOT.rglob("*")
        if p.is_file() and p.name != "checksums.sha256" and "__pycache__" not in p.parts
    )
    checksum_lines = [f"{sha256_file(path)}  {path.relative_to(ROOT).as_posix()}" for path in files]
    (ROOT / "checksums.sha256").write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")

    zip_path = ROOT.parent / f"{ROOT.name}.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(p for p in ROOT.rglob("*") if p.is_file() and "__pycache__" not in p.parts):
            archive.write(path, arcname=(Path(ROOT.name) / path.relative_to(ROOT)).as_posix())
    print(json.dumps({"status": "COMPLETE", "root": str(ROOT), "zip": str(zip_path), **completion}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
