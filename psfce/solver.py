from __future__ import annotations

from dataclasses import dataclass
import numpy as np
from scipy import sparse


@dataclass
class RelocationConfig:
    max_sweeps: int = 30
    tolerance: float = 1e-11
    order_restarts: int = 2
    fb_dtype: str = "float64"
    max_fb_bytes: int = 2_500_000_000


class FactorOperator:
    """Exact symmetric G = H W H^T with sparse H and dense FB=H W.

    FB is the only n x d dense work array. It may be float32 to cut memory;
    all cluster sufficient statistics are accumulated in float64.
    """

    def __init__(self, H: sparse.csr_matrix, W: np.ndarray, fb_dtype="float64", max_fb_bytes=2_500_000_000):
        self.H = H.tocsr()
        self.W = np.asarray(W, dtype=np.float64)
        self.n, self.d = self.H.shape
        dt = np.dtype(fb_dtype)
        estimated = self.n * self.d * dt.itemsize
        if estimated > int(max_fb_bytes):
            raise MemoryError(
                f"H@W factor would require {estimated/2**30:.2f} GiB > limit {max_fb_bytes/2**30:.2f} GiB"
            )
        self.FB = np.asarray(self.H @ self.W, dtype=dt)
        # exact diagonal h_i W h_i^T; mixed dtype multiplication accumulates in float64 here
        self.diag = np.asarray(self.H.multiply(self.FB).sum(axis=1)).ravel().astype(np.float64)

    def objective(self, labels, c=None) -> float:
        z = np.asarray(labels, dtype=np.int32)
        if c is None:
            c = int(z.max()) + 1
        n = len(z)
        Z = sparse.csr_matrix((np.ones(n), (np.arange(n), z)), shape=(n, c))
        T = np.asarray(self.H.T @ Z.toarray(), dtype=np.float64)
        TB = np.asarray(self.FB.T @ Z.toarray(), dtype=np.float64)
        sizes = np.bincount(z, minlength=c).astype(np.float64)
        S = np.sum(T * TB, axis=0)
        return float(np.sum(S / sizes))


def exact_relocation(
    operator: FactorOperator,
    init_labels,
    c: int,
    max_sweeps=30,
    tolerance=1e-11,
    order_seed=0,
    record_history=False,
):
    z = np.asarray(init_labels, dtype=np.int32).copy()
    if len(np.unique(z)) != c:
        raise ValueError("initialization must contain exactly c nonempty clusters")
    n = len(z)
    sizes = np.bincount(z, minlength=c).astype(np.int64)
    Z = sparse.csr_matrix((np.ones(n), (np.arange(n), z)), shape=(n, c))
    Z_dense = Z.toarray()
    T = np.asarray(operator.H.T @ Z_dense, dtype=np.float64)
    TB = np.asarray(operator.FB.T @ Z_dense, dtype=np.float64)
    S = np.sum(T * TB, axis=0)
    history = [float(np.sum(S / sizes))] if record_history else None
    moves_history = [] if record_history else None
    rng = np.random.default_rng(order_seed)
    total_moves = 0

    for sweep in range(max_sweeps):
        moved = 0
        for i in rng.permutation(n):
            source = int(z[i])
            if sizes[source] <= 1:
                continue
            # G_{i,C_q} = (H_i W) (H^T 1_Cq) = FB_i T_q
            gsum = np.asarray(operator.FB[i], dtype=np.float64) @ T
            diagonal = operator.diag[i]
            remove = (
                (S[source] - 2.0 * gsum[source] + diagonal) / (sizes[source] - 1)
                - S[source] / sizes[source]
            )
            best, best_delta = source, tolerance
            for target in range(c):
                if target == source:
                    continue
                add = (
                    (S[target] + 2.0 * gsum[target] + diagonal) / (sizes[target] + 1)
                    - S[target] / sizes[target]
                )
                delta = remove + add
                if delta > best_delta:
                    best, best_delta = target, float(delta)
            if best == source:
                continue

            target = best
            S[source] = S[source] - 2.0 * gsum[source] + diagonal
            S[target] = S[target] + 2.0 * gsum[target] + diagonal
            row = operator.H.getrow(i)
            T[row.indices, source] -= row.data
            T[row.indices, target] += row.data
            # TB must track FB^T Z as well.
            fbi = np.asarray(operator.FB[i], dtype=np.float64)
            TB[:, source] -= fbi
            TB[:, target] += fbi
            sizes[source] -= 1
            sizes[target] += 1
            z[i] = target
            moved += 1
            total_moves += 1

        if record_history:
            history.append(float(np.sum(S / sizes)))
            moves_history.append(int(moved))
        if moved == 0:
            break

    return z, {
        "sweeps": int(sweep + 1),
        "moves": int(total_moves),
        "objective": float(np.sum(S / sizes)),
        "history": history,
        "moves_history": moves_history,
    }


def refine_multistart(family, init_labels_list, c, lam, q, config: RelocationConfig, energy_preserve=True):
    W = family.total_W(lam, q, energy_preserve=energy_preserve)
    try:
        op = FactorOperator(
            family.H,
            W,
            fb_dtype=config.fb_dtype,
            max_fb_bytes=config.max_fb_bytes,
        )
    except MemoryError as exc:
        # Explicitly report that the exact discrete stage was skipped rather than silently approximating it.
        z = np.asarray(init_labels_list[0], dtype=np.int32)
        return z, {
            "refined": False,
            "skip_reason": str(exc),
            "objective": np.nan,
            "sweeps": 0,
            "moves": 0,
            "history": None,
            "moves_history": None,
        }

    best_z, best_info = None, None
    for j, init in enumerate(init_labels_list):
        for r in range(max(1, config.order_restarts)):
            z, info = exact_relocation(
                op,
                init,
                c,
                max_sweeps=config.max_sweeps,
                tolerance=config.tolerance,
                order_seed=7919 * (j + 1) + r,
                record_history=True,
            )
            if best_info is None or info["objective"] > best_info["objective"] + 1e-12:
                best_z, best_info = z, info
    best_info = dict(best_info)
    best_info["refined"] = True
    best_info["skip_reason"] = ""
    return best_z, best_info
