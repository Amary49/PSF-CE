from __future__ import annotations

import hashlib
import numpy as np
from scipy import sparse


def canonicalize_labels(labels: np.ndarray) -> np.ndarray:
    labels = np.asarray(labels)
    _, inv = np.unique(labels, return_inverse=True)
    return inv.astype(np.int32, copy=False)


def normalized_indicator_sparse(labels: np.ndarray, dtype=np.float64) -> sparse.csr_matrix:
    z = canonicalize_labels(labels)
    n = z.size
    counts = np.bincount(z).astype(dtype)
    if np.any(counts <= 0):
        raise ValueError("partition contains an empty cluster after canonicalization")
    values = (1.0 / np.sqrt(counts[z])).astype(dtype, copy=False)
    rows = np.arange(n, dtype=np.int64)
    return sparse.csr_matrix((values, (rows, z)), shape=(n, counts.size), dtype=dtype)


def stacked_indicator(parts, dtype=np.float64):
    parts = [canonicalize_labels(p) for p in parts]
    if len(parts) < 2:
        raise ValueError("need at least two base partitions")
    n = len(parts[0])
    if any(len(p) != n for p in parts):
        raise ValueError("all base partitions must have the same sample count")
    indicators = [normalized_indicator_sparse(p, dtype=dtype) for p in parts]
    H = sparse.hstack(indicators, format="csr", dtype=dtype)
    offsets = np.zeros(len(indicators) + 1, dtype=np.int64)
    for i, hm in enumerate(indicators):
        offsets[i + 1] = offsets[i] + hm.shape[1]
    return parts, indicators, H, offsets


def dataset_fingerprint(y: np.ndarray, parts) -> str:
    h = hashlib.sha256()
    yy = canonicalize_labels(y)
    h.update(np.asarray(yy.shape, dtype=np.int64).tobytes())
    h.update(yy.tobytes())
    for p in parts:
        z = canonicalize_labels(p)
        h.update(np.asarray(z.shape, dtype=np.int64).tobytes())
        h.update(z.tobytes())
    return h.hexdigest()
