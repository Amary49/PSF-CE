from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import time
import traceback
from typing import Any

import numpy as np
from scipy.io import loadmat, savemat

from .indicators import canonicalize_labels


COMPATIBLE_BASELINES = ("CEHM", "YACHT", "RANGE", "AWEC")
PROTOCOL_INCOMPATIBLE = ("FSEC",)


@dataclass(frozen=True)
class ExternalBaselineSpec:
    name: str
    status: str
    backend: str
    repo_url: str
    commit: str
    retrieval_date: str
    repo_root: str
    matlab_adapter: str
    adapter_revision: str = "v1"
    timeout_seconds: int = 7200
    license: str = "NOASSERTION"
    notes: str = ""


class ExternalBaselineError(RuntimeError):
    pass


def load_external_registry(path: str | Path) -> dict[str, ExternalBaselineSpec]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    methods = raw.get("methods", raw)
    out: dict[str, ExternalBaselineSpec] = {}
    for name, cfg in methods.items():
        data = dict(cfg or {})
        data.setdefault("name", name)
        spec = ExternalBaselineSpec(**data)
        if name == "DREAM":
            raise ExternalBaselineError("DREAM is forbidden by the V4 protocol")
        out[name] = spec
    return out


def standard_parts_matrix(parts) -> np.ndarray:
    """Return a validated, 1-based ``n x M`` partition matrix."""
    if not parts:
        raise ExternalBaselineError("base partition collection is empty")
    n = len(np.asarray(parts[0]).ravel())
    cols = []
    for index, part in enumerate(parts):
        z = np.asarray(part).ravel()
        if len(z) != n:
            raise ExternalBaselineError(f"partition {index} has length {len(z)}; expected {n}")
        z = canonicalize_labels(z).astype(np.int32) + 1
        if len(np.unique(z)) < 2:
            raise ExternalBaselineError(f"partition {index} has fewer than two nonempty clusters")
        cols.append(z)
    return np.column_stack(cols).astype(np.int32, copy=False)


def base_partition_sha256(parts) -> str:
    bp = standard_parts_matrix(parts)
    h = hashlib.sha256()
    h.update(np.asarray(bp.shape, dtype="<i8").tobytes())
    h.update(np.ascontiguousarray(bp.astype("<i4", copy=False)).tobytes())
    return h.hexdigest()


def parameter_sha256(params: dict[str, Any]) -> str:
    payload = json.dumps(params, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def cache_key(spec: ExternalBaselineSpec, parts, c: int, params: dict[str, Any], seed: int) -> str:
    payload = {
        "schema": "psfce-v4-official-baseline-cache-v1",
        "method": spec.name,
        "repo_url": spec.repo_url,
        "commit": spec.commit,
        "bp_sha256": base_partition_sha256(parts),
        "c": int(c),
        "params_sha256": parameter_sha256(params),
        "seed": int(seed),
    }
    if spec.adapter_revision != "v1":
        payload["adapter_revision"] = spec.adapter_revision
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def _write_batch_bridge_input(path: Path, parts, c: int, seed: int, params_list: list[dict[str, Any]]) -> dict[str, str]:
    bp = standard_parts_matrix(parts)
    meta = {
        "schema": "psfce-v4-fixed-bp-batch-v1",
        "bp_sha256": base_partition_sha256(parts),
        "params_sha256": [parameter_sha256(params) for params in params_list],
    }
    savemat(
        path,
        {
            "base_parts": bp,
            "c": np.asarray([[int(c)]], dtype=np.int32),
            "seed": np.asarray([[int(seed)]], dtype=np.int32),
            "params_json_list": np.asarray(
                [json.dumps(params, sort_keys=True) for params in params_list], dtype=object
            ).reshape(1, -1),
            "input_meta_json": json.dumps(meta, sort_keys=True),
        },
        do_compression=True,
    )
    return meta


def verify_repository(spec: ExternalBaselineSpec) -> dict[str, str]:
    root = Path(spec.repo_root).expanduser().resolve()
    if not root.is_dir():
        raise ExternalBaselineError(f"{spec.name}: repository not found: {root}")
    if not (root / ".git").exists():
        raise ExternalBaselineError(f"{spec.name}: repository must be a pinned Git checkout: {root}")
    cp = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if cp.returncode != 0:
        raise ExternalBaselineError(f"{spec.name}: cannot read repository commit: {cp.stderr.strip()}")
    actual = cp.stdout.strip().lower()
    expected = spec.commit.lower()
    if actual != expected:
        raise ExternalBaselineError(f"{spec.name}: commit mismatch; expected {expected}, found {actual}")
    return {"repo_root": str(root), "commit": actual}


def _write_bridge_input(path: Path, parts, c: int, seed: int, params: dict[str, Any]) -> dict[str, str]:
    bp = standard_parts_matrix(parts)
    meta = {
        "schema": "psfce-v4-fixed-bp-v1",
        "bp_sha256": base_partition_sha256(parts),
        "params_sha256": parameter_sha256(params),
    }
    # Ground-truth labels are deliberately absent.
    savemat(
        path,
        {
            "base_parts": bp,
            "c": np.asarray([[int(c)]], dtype=np.int32),
            "seed": np.asarray([[int(seed)]], dtype=np.int32),
            "params_json": json.dumps(params, sort_keys=True),
            "input_meta_json": json.dumps(meta, sort_keys=True),
        },
        do_compression=True,
    )
    return meta


def bridge_input_keys(path: str | Path) -> set[str]:
    data = loadmat(path)
    return {k for k in data if not k.startswith("__")}


def _load_output(path: Path, n: int) -> tuple[np.ndarray, dict[str, Any]]:
    if not path.exists():
        raise ExternalBaselineError(f"official adapter did not create output: {path}")
    data = loadmat(path)
    if "labels" not in data:
        raise ExternalBaselineError(f"{path}: missing labels")
    labels = canonicalize_labels(np.asarray(data["labels"]).ravel()).astype(np.int32)
    if len(labels) != n:
        raise ExternalBaselineError(f"{path}: label length {len(labels)} != n={n}")
    meta: dict[str, Any] = {}
    if "adapter_meta_json" in data:
        raw = data["adapter_meta_json"]
        try:
            value = raw.item() if np.asarray(raw).size == 1 else raw.ravel()[0]
            meta = json.loads(str(value))
        except Exception:
            meta = {"adapter_meta_parse_error": True}
    return labels, meta


def _matlab_quote(value: str) -> str:
    return str(value).replace("'", "''")


def find_matlab_executable() -> str:
    requested = os.environ.get("MATLAB_EXE", "").strip()
    if requested:
        p = Path(requested)
        if p.exists():
            return str(p)
        found = shutil.which(requested)
        if found:
            return found
        raise ExternalBaselineError(f"MATLAB_EXE does not resolve: {requested}")
    found = shutil.which("matlab")
    if found:
        return found
    raise ExternalBaselineError("MATLAB not found. Set MATLAB_EXE to matlab.exe; prediction fallback is forbidden.")


def build_matlab_expression(spec: ExternalBaselineSpec, input_mat: Path, output_mat: Path, package_root: Path) -> str:
    adapter_root = package_root / "baseline_adapters" / "matlab"
    return (
        f"addpath('{_matlab_quote(str(adapter_root.resolve()))}');"
        f"{spec.matlab_adapter}('{_matlab_quote(str(input_mat.resolve()))}',"
        f"'{_matlab_quote(str(output_mat.resolve()))}',"
        f"'{_matlab_quote(str(Path(spec.repo_root).expanduser().resolve()))}');"
    )


def _run_matlab(spec: ExternalBaselineSpec, parts, c: int, seed: int, params: dict[str, Any], package_root: Path):
    verify_repository(spec)
    matlab_exe = find_matlab_executable()
    with tempfile.TemporaryDirectory(prefix=f"psfce_v4_{spec.name.lower()}_") as td:
        work = Path(td)
        input_mat = work / "input.mat"
        output_mat = work / "output.mat"
        _write_bridge_input(input_mat, parts, c, seed, params)
        expression = build_matlab_expression(spec, input_mat, output_mat, package_root)
        started = time.perf_counter()
        cp = subprocess.run(
            [matlab_exe, "-batch", expression],
            cwd=work,
            capture_output=True,
            text=True,
            timeout=spec.timeout_seconds,
            check=False,
        )
        elapsed = time.perf_counter() - started
        if cp.returncode != 0:
            raise ExternalBaselineError(
                f"{spec.name}: official MATLAB adapter failed ({cp.returncode})\n"
                f"STDOUT:\n{cp.stdout[-6000:]}\nSTDERR:\n{cp.stderr[-6000:]}"
            )
        labels, adapter_meta = _load_output(output_mat, len(parts[0]))
        return labels, elapsed, adapter_meta, cp.stdout[-3000:], cp.stderr[-3000:]


def _matlab_cell_string(value: Any) -> str:
    array = np.asarray(value)
    if array.size == 0:
        return ""
    item = array.item() if array.size == 1 else array.ravel()[0]
    if isinstance(item, np.ndarray):
        if item.dtype.kind in {"U", "S"}:
            return "".join(str(x) for x in item.ravel())
        if item.size == 1:
            return str(item.item())
    return str(item)


def _run_matlab_awec_batch(
    spec: ExternalBaselineSpec,
    parts,
    c: int,
    seed: int,
    params_list: list[dict[str, Any]],
    package_root: Path,
):
    verify_repository(spec)
    matlab_exe = find_matlab_executable()
    with tempfile.TemporaryDirectory(prefix="psfce_v4_awec_batch_") as td:
        work = Path(td)
        input_mat = work / "input.mat"
        output_mat = work / "output.mat"
        _write_batch_bridge_input(input_mat, parts, c, seed, params_list)
        adapter_root = package_root / "baseline_adapters" / "matlab"
        expression = (
            f"addpath('{_matlab_quote(str(adapter_root.resolve()))}');"
            f"psfce_adapter_awec_batch('{_matlab_quote(str(input_mat.resolve()))}',"
            f"'{_matlab_quote(str(output_mat.resolve()))}',"
            f"'{_matlab_quote(str(Path(spec.repo_root).expanduser().resolve()))}');"
        )
        started = time.perf_counter()
        cp = subprocess.run(
            [matlab_exe, "-batch", expression],
            cwd=work,
            capture_output=True,
            text=True,
            timeout=spec.timeout_seconds,
            check=False,
        )
        wall_elapsed = time.perf_counter() - started
        if cp.returncode != 0:
            raise ExternalBaselineError(
                f"{spec.name}: optimized official MATLAB batch adapter failed ({cp.returncode})\n"
                f"STDOUT:\n{cp.stdout[-6000:]}\nSTDERR:\n{cp.stderr[-6000:]}"
            )
        if not output_mat.exists():
            raise ExternalBaselineError(f"{spec.name}: batch adapter did not create {output_mat}")
        data = loadmat(output_mat)
        labels_matrix = np.asarray(data.get("labels_matrix", []))
        if labels_matrix.shape != (len(parts[0]), len(params_list)):
            raise ExternalBaselineError(
                f"{spec.name}: batch label shape {labels_matrix.shape} != "
                f"({len(parts[0])}, {len(params_list)})"
            )
        runtimes = np.asarray(data.get("runtime_seconds", [])).ravel()
        if len(runtimes) != len(params_list):
            runtimes = np.full(len(params_list), wall_elapsed / max(1, len(params_list)))
        raw_meta = np.asarray(data.get("adapter_meta_json_list", []), dtype=object).ravel()
        metas = []
        for index in range(len(params_list)):
            try:
                metas.append(json.loads(_matlab_cell_string(raw_meta[index])))
            except Exception:
                metas.append({"adapter_meta_parse_error": True})
        labels = [
            canonicalize_labels(labels_matrix[:, index]).astype(np.int32)
            for index in range(len(params_list))
        ]
        return labels, runtimes.astype(float).tolist(), metas, cp.stdout[-3000:], cp.stderr[-3000:]


def _cache_path(cache_dir: str | Path, spec: ExternalBaselineSpec, dataset: str, pool: str, key: str) -> Path:
    safe_dataset = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in dataset)
    safe_pool = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in str(pool))
    return Path(cache_dir) / "official_baselines" / spec.name / f"{safe_dataset}__pool{safe_pool}__{key}.npz"


def _read_cache(path: Path, expected_key: str, n: int) -> tuple[np.ndarray, dict[str, Any]]:
    with np.load(path, allow_pickle=False) as data:
        if "labels" not in data or "metadata_json" not in data:
            raise ExternalBaselineError(f"invalid V4 cache: {path}")
        metadata = json.loads(str(np.asarray(data["metadata_json"]).item()))
        if metadata.get("cache_key") != expected_key:
            raise ExternalBaselineError(f"cache-key mismatch: {path}")
        labels = canonicalize_labels(np.asarray(data["labels"]).ravel()).astype(np.int32)
    if len(labels) != n:
        raise ExternalBaselineError(f"cached label length {len(labels)} != n={n}: {path}")
    return labels, metadata


def _write_cache(path: Path, labels: np.ndarray, metadata: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=path.stem + ".", suffix=".npz", dir=str(path.parent))
    os.close(fd)
    temp = Path(temp_name)
    try:
        np.savez_compressed(temp, labels=np.asarray(labels, dtype=np.int32), metadata_json=json.dumps(metadata, sort_keys=True))
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


def run_external_baseline(
    spec: ExternalBaselineSpec,
    parts,
    c: int,
    params: dict[str, Any],
    seed: int,
    dataset: str,
    pool: str,
    cache_dir: str | Path,
    package_root: str | Path | None = None,
) -> dict[str, Any]:
    """Run one pinned author implementation and return the uniform V4 result dictionary."""
    started = time.perf_counter()
    base = {
        "labels": None,
        "runtime": 0.0,
        "status": "error",
        "error": "",
        "backend": spec.backend,
        "repo_url": spec.repo_url,
        "commit": spec.commit,
        "retrieval_date": spec.retrieval_date,
        "license": spec.license,
        "method": spec.name,
        "dataset": dataset,
        "pool": str(pool),
        "seed": int(seed),
        "params": dict(params),
        "params_sha256": parameter_sha256(params),
        "bp_sha256": base_partition_sha256(parts),
        "cache_hit": False,
        "cache_file": "",
        "adapter_meta": {},
        "adapter_revision": spec.adapter_revision,
        "stdout_tail": "",
        "stderr_tail": "",
    }
    try:
        if spec.name in PROTOCOL_INCOMPATIBLE or spec.status == "protocol_incompatible":
            raise ExternalBaselineError(f"{spec.name}: protocol_incompatible; formal execution is forbidden")
        if spec.name not in COMPATIBLE_BASELINES:
            raise ExternalBaselineError(f"{spec.name}: not in the V4 approved baseline set")
        if spec.status != "enabled":
            raise ExternalBaselineError(f"{spec.name}: registry status is {spec.status!r}, expected 'enabled'")
        if spec.backend != "matlab":
            raise ExternalBaselineError(f"{spec.name}: only the official MATLAB backend is allowed; found {spec.backend!r}")

        key = cache_key(spec, parts, c, params, seed)
        path = _cache_path(cache_dir, spec, dataset, pool, key)
        base["cache_file"] = str(path)
        if path.exists():
            labels, metadata = _read_cache(path, key, len(parts[0]))
            base.update(labels=labels, runtime=float(metadata["runtime"]), status="ok", cache_hit=True)
            base["adapter_meta"] = metadata.get("adapter_meta", {})
            return base

        package = Path(package_root or Path(__file__).resolve().parents[1])
        labels, elapsed, adapter_meta, stdout, stderr = _run_matlab(spec, parts, c, seed, params, package)
        metadata = {
            "schema": "psfce-v4-official-baseline-cache-v1",
            "cache_key": key,
            "method": spec.name,
            "repo_url": spec.repo_url,
            "commit": spec.commit,
            "retrieval_date": spec.retrieval_date,
            "bp_sha256": base["bp_sha256"],
            "params_sha256": base["params_sha256"],
            "seed": int(seed),
            "runtime": float(elapsed),
            "adapter_meta": adapter_meta,
            "adapter_revision": spec.adapter_revision,
            "output_sha256": hashlib.sha256(np.asarray(labels, dtype="<i4").tobytes()).hexdigest(),
        }
        _write_cache(path, labels, metadata)
        base.update(
            labels=labels,
            runtime=float(elapsed),
            status="ok",
            adapter_meta=adapter_meta,
            stdout_tail=stdout,
            stderr_tail=stderr,
        )
    except Exception as exc:
        base["runtime"] = float(time.perf_counter() - started)
        base["error"] = f"{type(exc).__name__}: {exc}"
        base["traceback"] = traceback.format_exc()
    return base


def run_external_baseline_batch(
    spec: ExternalBaselineSpec,
    parts,
    c: int,
    params_list: list[dict[str, Any]],
    seed: int,
    dataset: str,
    pool: str,
    cache_dir: str | Path,
    package_root: str | Path | None = None,
) -> list[dict[str, Any]]:
    """Run AWEC settings in one MATLAB session while keeping per-setting caches."""
    if spec.name != "AWEC":
        return [
            run_external_baseline(
                spec, parts, c, params, seed, dataset, pool, cache_dir, package_root
            )
            for params in params_list
        ]
    if spec.status != "enabled" or spec.backend != "matlab":
        raise ExternalBaselineError("AWEC batch execution requires an enabled MATLAB specification")

    results: list[dict[str, Any] | None] = [None] * len(params_list)
    missing_indices: list[int] = []
    paths: list[Path] = []
    keys: list[str] = []
    bp_hash = base_partition_sha256(parts)
    for index, params in enumerate(params_list):
        key = cache_key(spec, parts, c, params, seed)
        path = _cache_path(cache_dir, spec, dataset, pool, key)
        keys.append(key)
        paths.append(path)
        if path.exists():
            labels, metadata = _read_cache(path, key, len(parts[0]))
            results[index] = {
                "labels": labels,
                "runtime": float(metadata["runtime"]),
                "status": "ok",
                "error": "",
                "backend": spec.backend,
                "repo_url": spec.repo_url,
                "commit": spec.commit,
                "retrieval_date": spec.retrieval_date,
                "license": spec.license,
                "method": spec.name,
                "dataset": dataset,
                "pool": str(pool),
                "seed": int(seed),
                "params": dict(params),
                "params_sha256": parameter_sha256(params),
                "bp_sha256": bp_hash,
                "cache_hit": True,
                "cache_file": str(path),
                "adapter_meta": metadata.get("adapter_meta", {}),
                "adapter_revision": spec.adapter_revision,
                "stdout_tail": "",
                "stderr_tail": "",
            }
        else:
            missing_indices.append(index)

    if missing_indices:
        package = Path(package_root or Path(__file__).resolve().parents[1])
        missing_params = [params_list[index] for index in missing_indices]
        try:
            labels_list, runtimes, metas, stdout, stderr = _run_matlab_awec_batch(
                spec, parts, c, seed, missing_params, package
            )
            for local_index, index in enumerate(missing_indices):
                params = params_list[index]
                labels = labels_list[local_index]
                metadata = {
                    "schema": "psfce-v4-official-baseline-cache-v1",
                    "cache_key": keys[index],
                    "method": spec.name,
                    "repo_url": spec.repo_url,
                    "commit": spec.commit,
                    "retrieval_date": spec.retrieval_date,
                    "bp_sha256": bp_hash,
                    "params_sha256": parameter_sha256(params),
                    "seed": int(seed),
                    "runtime": float(runtimes[local_index]),
                    "adapter_meta": metas[local_index],
                    "adapter_revision": spec.adapter_revision,
                    "output_sha256": hashlib.sha256(
                        np.asarray(labels, dtype="<i4").tobytes()
                    ).hexdigest(),
                }
                _write_cache(paths[index], labels, metadata)
                results[index] = {
                    "labels": labels,
                    "runtime": float(runtimes[local_index]),
                    "status": "ok",
                    "error": "",
                    "backend": spec.backend,
                    "repo_url": spec.repo_url,
                    "commit": spec.commit,
                    "retrieval_date": spec.retrieval_date,
                    "license": spec.license,
                    "method": spec.name,
                    "dataset": dataset,
                    "pool": str(pool),
                    "seed": int(seed),
                    "params": dict(params),
                    "params_sha256": parameter_sha256(params),
                    "bp_sha256": bp_hash,
                    "cache_hit": False,
                    "cache_file": str(paths[index]),
                    "adapter_meta": metas[local_index],
                    "adapter_revision": spec.adapter_revision,
                    "stdout_tail": stdout,
                    "stderr_tail": stderr,
                }
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"
            trace = traceback.format_exc()
            for index in missing_indices:
                params = params_list[index]
                results[index] = {
                    "labels": None,
                    "runtime": 0.0,
                    "status": "error",
                    "error": error,
                    "traceback": trace,
                    "backend": spec.backend,
                    "repo_url": spec.repo_url,
                    "commit": spec.commit,
                    "retrieval_date": spec.retrieval_date,
                    "license": spec.license,
                    "method": spec.name,
                    "dataset": dataset,
                    "pool": str(pool),
                    "seed": int(seed),
                    "params": dict(params),
                    "params_sha256": parameter_sha256(params),
                    "bp_sha256": bp_hash,
                    "cache_hit": False,
                    "cache_file": str(paths[index]),
                    "adapter_meta": {},
                    "adapter_revision": spec.adapter_revision,
                    "stdout_tail": "",
                    "stderr_tail": "",
                }
    return [result for result in results if result is not None]
