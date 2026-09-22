from __future__ import annotations

import numpy as np
from scipy import sparse
from sklearn.cluster import AgglomerativeClustering, KMeans

from .indicators import normalized_indicator_sparse


def normalized_ca(parts):
    hs = [normalized_indicator_sparse(p) for p in parts]
    n = hs[0].shape[0]
    A = np.zeros((n, n), dtype=np.float64)
    for h in hs:
        A += (h @ h.T).toarray()
    return A / len(hs)


def spectral_cluster_dense(A, c, seed=0, n_init=20):
    vals, vecs = np.linalg.eigh(np.asarray(A, dtype=np.float64))
    U = vecs[:, np.argsort(vals)[-c:][::-1]]
    U /= np.maximum(np.linalg.norm(U, axis=1, keepdims=True), 1e-12)
    return KMeans(n_clusters=c, n_init=n_init, random_state=seed).fit_predict(U).astype(np.int32)


def cspa(parts, c, seed=0, n_init=20, max_dense_n=8000):
    n = len(parts[0])
    if n > max_dense_n:
        raise MemoryError(f"CSPA dense control disabled for n={n} > {max_dense_n}")
    A = normalized_ca(parts)
    return spectral_cluster_dense(A, c, seed=seed, n_init=n_init)


def eac(parts, c, max_dense_n=6000):
    n = len(parts[0])
    if n > max_dense_n:
        raise MemoryError(f"EAC dense control disabled for n={n} > {max_dense_n}")
    A = normalized_ca(parts)
    D = np.maximum(1.0 - A, 0.0)
    np.fill_diagonal(D, 0.0)
    return AgglomerativeClustering(n_clusters=c, metric="precomputed", linkage="average").fit_predict(D).astype(np.int32)


def hbgf(parts, c, seed=0, n_init=20):
    hs = [normalized_indicator_sparse(p) for p in parts]
    H = sparse.hstack(hs, format="csr")
    # The left singular subspace of H is the normalized bipartite sample embedding.
    from scipy.sparse.linalg import svds
    k = min(c, min(H.shape) - 1)
    if k < c:
        U, _, _ = np.linalg.svd(H.toarray(), full_matrices=False)
        U = U[:, :c]
    else:
        U, s, _ = svds(H, k=c, which="LM", return_singular_vectors=True)
        U = U[:, np.argsort(s)[::-1]]
    U /= np.maximum(np.linalg.norm(U, axis=1, keepdims=True), 1e-12)
    return KMeans(n_clusters=c, n_init=n_init, random_state=seed).fit_predict(U).astype(np.int32)


def mcla(parts, c, max_meta_clusters=5000):
    n = len(parts[0])
    members = []
    for z in parts:
        zz = np.asarray(z)
        for q in np.unique(zz):
            members.append(np.flatnonzero(zz == q))
    d = len(members)
    if d > max_meta_clusters:
        raise MemoryError(f"MCLA meta-cluster count {d} > limit {max_meta_clusters}")
    X = np.zeros((d, n), dtype=np.int32)
    for j, idx in enumerate(members):
        X[j, idx] = 1
    inter = X @ X.T  # int32: no uint8 overflow
    sz = X.sum(axis=1).astype(np.float64)
    union = sz[:, None] + sz[None, :] - inter
    sim = inter / np.maximum(union, 1.0)
    dist = 1.0 - sim
    np.fill_diagonal(dist, 0.0)
    meta = AgglomerativeClustering(n_clusters=c, metric="precomputed", linkage="average").fit_predict(dist)
    assoc = np.zeros((n, c), dtype=np.float64)
    for r in range(c):
        cols = np.flatnonzero(meta == r)
        if len(cols):
            assoc[:, r] = X[cols].mean(axis=0)
    return np.argmax(assoc, axis=1).astype(np.int32)
