"""Evaluation metrics; labels are used only after consensus generation."""

from __future__ import annotations

import numpy as np
from scipy.optimize import linear_sum_assignment
from sklearn.metrics import adjusted_rand_score, f1_score, normalized_mutual_info_score


def _codes(values: np.ndarray) -> np.ndarray:
    return np.unique(np.asarray(values).reshape(-1), return_inverse=True)[1]


def evaluate_clustering(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    yt = _codes(y_true)
    yp = _codes(y_pred)
    if yt.shape != yp.shape:
        raise ValueError("y_true and y_pred must have the same length")
    contingency = np.zeros((int(yp.max()) + 1, int(yt.max()) + 1), dtype=np.int64)
    np.add.at(contingency, (yp, yt), 1)
    row, col = linear_sum_assignment(contingency.max() - contingency)
    mapping = {int(r): int(c) for r, c in zip(row, col)}
    aligned = np.asarray([mapping.get(int(value), 0) for value in yp], dtype=np.int32)
    return {
        "ACC": float(contingency[row, col].sum() / len(yt)),
        "NMI": float(normalized_mutual_info_score(yt, yp)),
        "ARI": float(adjusted_rand_score(yt, yp)),
        "MacroF1": float(f1_score(yt, aligned, average="macro")),
    }
