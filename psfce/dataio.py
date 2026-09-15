from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import numpy as np
import pandas as pd

from .indicators import canonicalize_labels


@dataclass(frozen=True)
class DatasetRecord:
    name: str
    pool: str
    path: str
    group: str = "unspecified"
    split: str = "formal"
    source_id: str = ""
    task_family: str = ""


def _orient_parts(parts: np.ndarray, n: int) -> np.ndarray:
    parts = np.asarray(parts)
    if parts.ndim != 2:
        raise ValueError("parts must be 2D with shape (M,n) or (n,M)")
    if parts.shape[1] == n:
        return parts
    if parts.shape[0] == n:
        return parts.T
    raise ValueError(f"cannot orient parts shape {parts.shape} against n={n}")


def load_pool_npz(path: str | Path):
    path = Path(path)
    with np.load(path, allow_pickle=False) as data:
        if "y" not in data or "parts" not in data:
            raise KeyError(f"{path}: expected keys 'y' and 'parts'")
        y = canonicalize_labels(np.asarray(data["y"]).ravel())
        parts_arr = _orient_parts(data["parts"], len(y))
    parts = [canonicalize_labels(parts_arr[m]) for m in range(parts_arr.shape[0])]
    if len(np.unique(y)) < 2:
        raise ValueError(f"{path}: ground truth has <2 classes")
    if any(len(np.unique(p)) < 2 for p in parts):
        raise ValueError(f"{path}: every base partition must have >=2 nonempty clusters")
    return y, parts


def save_pool_npz(path: str | Path, y, parts):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    yy = canonicalize_labels(y)
    pp = np.vstack([canonicalize_labels(p) for p in parts]).astype(np.int32)
    np.savez_compressed(path, y=yy.astype(np.int32), parts=pp)


def load_manifest(path: str | Path) -> list[DatasetRecord]:
    path = Path(path)
    df = pd.read_csv(path).fillna("")
    required = {"name", "pool", "path"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"manifest missing columns: {sorted(missing)}")
    base = path.parent
    records = []
    for row in df.to_dict("records"):
        p = Path(str(row["path"]))
        if not p.is_absolute():
            p = (base / p).resolve()
        records.append(DatasetRecord(
            name=str(row["name"]), pool=str(row["pool"]), path=str(p),
            group=str(row.get("group", "unspecified") or "unspecified"),
            split=str(row.get("split", "formal") or "formal"),
            source_id=str(row.get("source_id", "") or ""),
            task_family=str(row.get("task_family", "") or ""),
        ))
    return records


def validate_manifest(records: list[DatasetRecord], require_disjoint=True, expected_M: int | None = None):
    seen = set()
    for r in records:
        key = (r.name, r.pool, r.split)
        if key in seen:
            raise ValueError(f"duplicate dataset/pool/split row: {key}")
        seen.add(key)
        if not Path(r.path).exists():
            raise FileNotFoundError(r.path)
        if expected_M is not None:
            _, parts = load_pool_npz(r.path)
            if len(parts) != expected_M:
                raise ValueError(f"{r.name}/{r.pool}: expected M={expected_M}, found {len(parts)}")
    if require_disjoint:
        dev = [r for r in records if r.split.lower() in {"dev", "development"}]
        formal = [r for r in records if r.split.lower() in {"formal", "test", "heldout"}]
        dn, fn = {r.name.lower() for r in dev}, {r.name.lower() for r in formal}
        overlap = sorted(dn & fn)
        if overlap:
            raise ValueError(f"development/formal dataset-name overlap: {overlap}")
        ds = {r.source_id.lower() for r in dev if r.source_id}
        fs = {r.source_id.lower() for r in formal if r.source_id}
        so = sorted(ds & fs)
        if so:
            raise ValueError(f"development/formal source_id overlap: {so}")


def inspect_pool(path: str | Path) -> dict:
    y, parts = load_pool_npz(path)
    return {
        "n": len(y), "c": int(len(np.unique(y))), "M": len(parts),
        "k_min": int(min(len(np.unique(p)) for p in parts)),
        "k_max": int(max(len(np.unique(p)) for p in parts)),
    }


def write_manifest_metadata(records, output_path: str | Path):
    rows=[]
    for r in records:
        rows.append({**r.__dict__, **inspect_pool(r.path)})
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(output_path, index=False)
