"""Frozen classic MCLA-METIS and HBGF-METIS implementations.

The constructions are clean-room reproductions of the definitions used in the
original cluster-ensemble literature and the archived ClusterPack audit.  No
spectral, hierarchical, or outcome-dependent fallback is permitted.
"""

from __future__ import annotations

from dataclasses import dataclass
import importlib.metadata
import time
from typing import Any

import numpy as np
from scipy import sparse


MCLA_MAX_META_SIMILARITY_CELLS = 25_000_000
HBGF_MAX_DIRECTED_EDGES = 50_000_000


@dataclass(frozen=True)
class BaselineResult:
    method: str
    variant: str
    labels: np.ndarray | None
    status: str
    runtime_seconds: float
    diagnostics: dict[str, Any]


def validate_parts(parts: np.ndarray) -> np.ndarray:
    array = np.asarray(parts)
    if array.ndim != 2:
        raise ValueError("parts must have shape (n_samples, n_partitions)")
    if array.shape[0] < 2 or array.shape[1] < 1:
        raise ValueError("parts must contain at least two samples and one partition")
    if not np.issubdtype(array.dtype, np.number):
        raise TypeError("partition labels must be numeric")
    if not np.all(np.isfinite(array)):
        raise ValueError("partition labels must be finite")
    return array


def canonical_membership(parts: np.ndarray) -> sparse.csr_matrix:
    """Return base-cluster-by-sample binary membership in canonical row order."""

    array = validate_parts(parts)
    rows: list[np.ndarray] = []
    for partition_id in range(array.shape[1]):
        labels = array[:, partition_id]
        for label in np.unique(labels):
            rows.append(np.flatnonzero(labels == label))
    rows.sort(key=lambda members: tuple(members.tolist()))
    row_ids: list[int] = []
    col_ids: list[int] = []
    for row_id, members in enumerate(rows):
        row_ids.extend([row_id] * int(members.size))
        col_ids.extend(members.tolist())
    data = np.ones(len(row_ids), dtype=np.int64)
    return sparse.csr_matrix(
        (data, (row_ids, col_ids)),
        shape=(len(rows), array.shape[0]),
        dtype=np.int64,
    )


def jaccard_meta_graph(membership: sparse.csr_matrix) -> np.ndarray:
    """Weighted MCLA meta-graph using binary Jaccard similarity."""

    safe = sparse.csr_matrix(membership, dtype=np.int64)
    intersections = (safe @ safe.T).toarray().astype(np.int64, copy=False)
    sizes = np.asarray(safe.sum(axis=1)).ravel().astype(np.int64, copy=False)
    unions = sizes[:, None] + sizes[None, :] - intersections
    similarity = np.divide(
        intersections,
        unions,
        out=np.zeros_like(intersections, dtype=np.float64),
        where=unions > 0,
    )
    np.fill_diagonal(similarity, 1.0)
    return similarity


def _metis_weighted_csr(
    similarity: np.ndarray | sparse.spmatrix,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    matrix = sparse.csr_matrix(similarity, dtype=np.float64).copy()
    matrix.setdiag(0.0)
    matrix.eliminate_zeros()
    if matrix.nnz == 0:
        raise ValueError("graph contains no positive off-diagonal edge")
    if np.min(matrix.data) < 0:
        raise ValueError("METIS similarity graph cannot contain negative weights")
    scale = 100_000_000.0 / float(matrix.data.sum())
    weights = np.rint(matrix.data * scale).astype(np.int64)
    matrix.data = weights
    matrix.eliminate_zeros()
    return (
        matrix.indptr.astype(np.int64, copy=False),
        matrix.indices.astype(np.int64, copy=False),
        matrix.data.astype(np.int64, copy=False),
    )


def _scale_vertex_weights(values: np.ndarray) -> list[int]:
    array = np.asarray(values, dtype=np.float64)
    if array.ndim != 1 or np.any(array < 0) or not np.any(array > 0):
        raise ValueError("vertex weights must be a nonnegative, nonzero vector")
    scaled = np.rint(array * (100_000_000.0 / float(array.sum()))).astype(np.int64)
    scaled[(array > 0) & (scaled == 0)] = 1
    return scaled.tolist()


def _pymetis() -> Any:
    try:
        import pymetis  # type: ignore
    except ImportError as exc:
        raise RuntimeError("frozen backend pymetis==2025.2.2 is unavailable") from exc
    version = importlib.metadata.version("pymetis")
    if version != "2025.2.2":
        raise RuntimeError(f"pymetis version drift: expected 2025.2.2, got {version}")
    return pymetis


def partition_weighted_graph(
    similarity: np.ndarray | sparse.spmatrix,
    c: int,
    *,
    seed: int,
    vertex_weights: np.ndarray | None = None,
) -> tuple[int, np.ndarray]:
    pymetis = _pymetis()
    xadj, adjncy, eweights = _metis_weighted_csr(similarity)
    kwargs: dict[str, Any] = {
        "adjacency": pymetis.CSRAdjacency(xadj, adjncy),
        "eweights": eweights,
        "recursive": True,
        "options": pymetis.Options(seed=int(seed)),
    }
    if vertex_weights is not None:
        kwargs["vweights"] = _scale_vertex_weights(vertex_weights)
    edge_cut, labels = pymetis.part_graph(c, **kwargs)
    return int(edge_cut), np.asarray(labels, dtype=np.int32)


def mcla_metis(parts: np.ndarray, c: int, *, seed: int = 0) -> BaselineResult:
    """Classic MCLA: Jaccard meta-graph, METIS, collapse, and assignment."""

    array = validate_parts(parts)
    membership = canonical_membership(array)
    n_base_clusters = int(membership.shape[0])
    if n_base_clusters**2 > MCLA_MAX_META_SIMILARITY_CELLS:
        return BaselineResult(
            "MCLA", "MCLA-METIS-PyMetis", None, "RESOURCE_BLOCKED", 0.0,
            {
                "meta_similarity_cells": n_base_clusters**2,
                "gate": MCLA_MAX_META_SIMILARITY_CELLS,
                "no_approximation": True,
            },
        )
    started = time.perf_counter()
    similarity = jaccard_meta_graph(membership)
    cluster_sizes = np.asarray(membership.sum(axis=1)).ravel().astype(np.int64)
    edge_cut, meta_labels = partition_weighted_graph(
        similarity, c, seed=seed, vertex_weights=cluster_sizes
    )
    association = np.zeros((array.shape[0], c), dtype=np.float64)
    for meta_cluster in range(c):
        rows = np.flatnonzero(meta_labels == meta_cluster)
        if rows.size:
            association[:, meta_cluster] = np.asarray(
                membership[rows].mean(axis=0)
            ).ravel()
    # ClusterPack specifies a small seeded perturbation only to resolve exact ties.
    association += np.random.default_rng(seed).random(association.shape) / 10_000.0
    labels = np.argmax(association, axis=1).astype(np.int32)
    return BaselineResult(
        "MCLA", "MCLA-METIS-PyMetis", labels, "COMPLETED",
        time.perf_counter() - started,
        {
            "n_samples": int(array.shape[0]),
            "n_partitions": int(array.shape[1]),
            "n_base_clusters": n_base_clusters,
            "meta_similarity_cells": n_base_clusters**2,
            "edge_cut": edge_cut,
            "meta_clusters_returned": int(np.unique(meta_labels).size),
            "output_clusters_returned": int(np.unique(labels).size),
            "scheme": "recursive_bisection",
            "seed": int(seed),
            "pymetis_version": importlib.metadata.version("pymetis"),
        },
    )


def hbgf_graph(parts: np.ndarray) -> tuple[sparse.csr_matrix, int]:
    """Classic HBGF bipartite graph with unit sample--base-cluster edges."""

    array = validate_parts(parts)
    membership = canonical_membership(array)
    n, d = array.shape[0], membership.shape[0]
    graph = sparse.bmat(
        [
            [sparse.csr_matrix((n, n), dtype=np.int8), membership.T.astype(np.int8)],
            [membership.astype(np.int8), sparse.csr_matrix((d, d), dtype=np.int8)],
        ],
        format="csr",
        dtype=np.int8,
    )
    return graph, int(d)


def hbgf_metis(parts: np.ndarray, c: int, *, seed: int = 0) -> BaselineResult:
    """Classic HBGF with recursive METIS and sample-vertex output labels."""

    array = validate_parts(parts)
    directed_edges = 2 * int(array.shape[0]) * int(array.shape[1])
    if directed_edges > HBGF_MAX_DIRECTED_EDGES:
        return BaselineResult(
            "HBGF", "HBGF-METIS-PyMetis", None, "RESOURCE_BLOCKED", 0.0,
            {
                "directed_edges": directed_edges,
                "gate": HBGF_MAX_DIRECTED_EDGES,
                "no_approximation": True,
            },
        )
    started = time.perf_counter()
    pymetis = _pymetis()
    graph, n_base_clusters = hbgf_graph(array)
    edge_cut, all_labels = pymetis.part_graph(
        c,
        adjacency=pymetis.CSRAdjacency(
            graph.indptr.astype(np.int64, copy=False),
            graph.indices.astype(np.int64, copy=False),
        ),
        recursive=True,
        options=pymetis.Options(seed=int(seed)),
    )
    labels = np.asarray(all_labels[: array.shape[0]], dtype=np.int32)
    return BaselineResult(
        "HBGF", "HBGF-METIS-PyMetis", labels, "COMPLETED",
        time.perf_counter() - started,
        {
            "n_samples": int(array.shape[0]),
            "n_partitions": int(array.shape[1]),
            "n_base_clusters": n_base_clusters,
            "n_graph_vertices": int(graph.shape[0]),
            "n_undirected_edges": int(graph.nnz // 2),
            "edge_cut": int(edge_cut),
            "output_clusters_returned": int(np.unique(labels).size),
            "edge_weight": 1,
            "scheme": "recursive_bisection",
            "seed": int(seed),
            "pymetis_version": importlib.metadata.version("pymetis"),
        },
    )
