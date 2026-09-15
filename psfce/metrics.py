from __future__ import annotations

import numpy as np
from scipy.optimize import linear_sum_assignment
from scipy.stats import wilcoxon
from sklearn.metrics import adjusted_rand_score, f1_score, normalized_mutual_info_score


def clustering_accuracy(y_true, y_pred) -> float:
    yt = np.asarray(y_true, dtype=np.int64)
    yp = np.asarray(y_pred, dtype=np.int64)
    ut, yt_idx = np.unique(yt, return_inverse=True)
    up, yp_idx = np.unique(yp, return_inverse=True)
    w = np.zeros((len(up), len(ut)), dtype=np.int64)
    np.add.at(w, (yp_idx, yt_idx), 1)
    r, c = linear_sum_assignment(w.max(initial=0) - w)
    return float(w[r, c].sum() / len(yt))


def aligned_macro_f1(y_true, y_pred) -> float:
    yt = np.asarray(y_true, dtype=np.int64)
    yp = np.asarray(y_pred, dtype=np.int64)
    ut, yt_idx = np.unique(yt, return_inverse=True)
    up, yp_idx = np.unique(yp, return_inverse=True)
    w = np.zeros((len(up), len(ut)), dtype=np.int64)
    np.add.at(w, (yp_idx, yt_idx), 1)
    r, c = linear_sum_assignment(w.max(initial=0) - w)
    mp = {int(up[i]): int(ut[j]) for i, j in zip(r, c)}
    # unmatched predicted clusters receive a fresh label and therefore zero recall for true classes
    sentinel = int(ut.max(initial=0) + 1)
    aligned = np.asarray([mp.get(int(v), sentinel) for v in yp], dtype=np.int64)
    return float(f1_score(yt, aligned, labels=ut, average="macro", zero_division=0))


def evaluate_clustering(y_true, y_pred) -> dict[str, float]:
    return {
        "ACC": clustering_accuracy(y_true, y_pred),
        "NMI": float(normalized_mutual_info_score(y_true, y_pred)),
        "ARI": float(adjusted_rand_score(y_true, y_pred)),
        "F1": aligned_macro_f1(y_true, y_pred),
    }


def paired_wilcoxon(x, y) -> float:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    d = x - y
    if len(d) == 0 or np.all(np.abs(d) < 1e-15):
        return 1.0
    try:
        return float(wilcoxon(d, zero_method="wilcox", alternative="two-sided").pvalue)
    except ValueError:
        return 1.0


def holm_adjust(pvals):
    p = np.asarray(pvals, dtype=float)
    m = len(p)
    order = np.argsort(p)
    adj_sorted = np.maximum.accumulate((m - np.arange(m)) * p[order])
    adj_sorted = np.minimum(adj_sorted, 1.0)
    out = np.empty_like(adj_sorted)
    out[order] = adj_sorted
    return out


def bootstrap_mean_ci(values, seed=2027, n_boot=5000, alpha=0.05):
    x = np.asarray(values, dtype=float)
    if len(x) == 0:
        return (np.nan, np.nan)
    rng = np.random.default_rng(seed)
    means = np.empty(n_boot, dtype=float)
    for b in range(n_boot):
        means[b] = rng.choice(x, size=len(x), replace=True).mean()
    return tuple(np.quantile(means, [alpha / 2, 1 - alpha / 2]).tolist())
