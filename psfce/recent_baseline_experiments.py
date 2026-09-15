from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict
from itertools import product
from pathlib import Path
import hashlib
import json
import traceback

import numpy as np
import pandas as pd

from .dataio import DatasetRecord, load_pool_npz
from .external_baselines import (
    base_partition_sha256,
    load_external_registry,
    run_external_baseline,
    run_external_baseline_batch,
)
from .metrics import evaluate_clustering
from .utils import atomic_json_dump, safe_name, stable_hash


def _row(record: DatasetRecord, method: str, params: dict) -> dict:
    return {
        "dataset": record.name,
        "pool": record.pool,
        "group": record.group,
        "task_family": record.task_family,
        "split": record.split,
        "source_id": record.source_id,
        "method": method,
        "params": json.dumps(params, sort_keys=True),
        "status": "error",
        "error": "",
    }


def _grid(settings: dict) -> list[dict]:
    if not settings:
        return [{}]
    keys = list(settings)
    values = [value if isinstance(value, list) else [value] for value in settings.values()]
    return [dict(zip(keys, combo)) for combo in product(*values)]


def expand_baseline_search(config: dict) -> list[dict]:
    out = []
    for method, spec in config.get("methods", {}).items():
        if not spec.get("enabled", True):
            continue
        defaults = dict(spec.get("defaults", {}))
        for choice in _grid(spec.get("grid", {})):
            params = dict(defaults)
            params.update(choice)
            out.append({"name": method, "params": params})
    return out


def run_recent_for_record(record_dict, settings, registry_path, options):
    record = DatasetRecord(**record_dict)
    # y is loaded here for evaluation but never passed to run_external_baseline or MATLAB.
    y, parts = load_pool_npz(record.path)
    c = len(np.unique(y))
    registry = load_external_registry(registry_path)
    awec_positions = [index for index, setting in enumerate(settings) if setting["name"] == "AWEC"]
    awec_results = {}
    if awec_positions:
        batch = run_external_baseline_batch(
            registry["AWEC"],
            parts,
            c,
            [dict(settings[index].get("params", {})) for index in awec_positions],
            int(options.get("seed", 2027)),
            record.name,
            record.pool,
            cache_dir=options["cache_dir"],
            package_root=options.get("package_root"),
        )
        awec_results = dict(zip(awec_positions, batch))
    rows = []
    for setting_index, setting in enumerate(settings):
        method = setting["name"]
        params = dict(setting.get("params", {}))
        row = _row(record, method, params)
        try:
            if method == "AWEC":
                result = awec_results[setting_index]
            else:
                result = run_external_baseline(
                    registry[method],
                    parts,
                    c,
                    params,
                    int(options.get("seed", 2027)),
                    record.name,
                    record.pool,
                    cache_dir=options["cache_dir"],
                    package_root=options.get("package_root"),
                )
            row.update(
                n=len(y),
                c=c,
                M=len(parts),
                runtime_seconds=float(result["runtime"]),
                backend=result["backend"],
                repo_url=result["repo_url"],
                commit=result["commit"],
                retrieval_date=result["retrieval_date"],
                license=result["license"],
                bp_sha256=result["bp_sha256"],
                params_sha256=result["params_sha256"],
                cache_hit=bool(result["cache_hit"]),
                cache_file=result["cache_file"],
                adapter_meta=json.dumps(result.get("adapter_meta", {}), sort_keys=True),
                adapter_revision=result.get("adapter_revision", "v1"),
                error=result["error"],
            )
            if result["status"] == "ok":
                row.update(evaluate_clustering(y, result["labels"]))
                row["status"] = "ok"
            else:
                row["traceback"] = result.get("traceback", "")
        except Exception as exc:
            row.update(
                n=len(y),
                c=c,
                M=len(parts),
                error=f"{type(exc).__name__}: {exc}",
                traceback=traceback.format_exc(),
            )
        rows.append(row)
    return rows


def _file_sha256(path: str | Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run_parallel(records, settings, registry_path, options, output_dir, experiment_name, workers=1, force=False):
    output_dir = Path(output_dir)
    shard_dir = output_dir / "shards" / experiment_name
    shard_dir.mkdir(parents=True, exist_ok=True)
    signature = stable_hash(
        {
            "schema": "psfce-v4-shard-v1",
            "settings": settings,
            "registry_sha256": _file_sha256(registry_path),
            "options": options,
        }
    )
    all_rows = []
    pending = []
    for record in records:
        _, shard_parts = load_pool_npz(record.path)
        input_bp_sha256 = base_partition_sha256(shard_parts)
        shard = shard_dir / f"{safe_name(record.name)}__{safe_name(record.pool)}__{signature}__{input_bp_sha256[:16]}.json"
        if shard.exists() and not force:
            payload = json.loads(shard.read_text(encoding="utf-8"))
            if payload.get("config_sig") != signature or payload.get("input_bp_sha256") != input_bp_sha256:
                raise RuntimeError(f"stale shard signature: {shard}")
            all_rows.extend(payload["rows"])
        else:
            pending.append((record, shard, input_bp_sha256))

    def consume(record, shard, input_bp_sha256, rows):
        atomic_json_dump({"record": asdict(record), "config_sig": signature, "input_bp_sha256": input_bp_sha256, "rows": rows}, shard)
        all_rows.extend(rows)

    args = (settings, str(registry_path), options)
    if workers <= 1:
        for record, shard, input_bp_sha256 in pending:
            consume(record, shard, input_bp_sha256, run_recent_for_record(asdict(record), *args))
    else:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(run_recent_for_record, asdict(record), *args): (record, shard, input_bp_sha256)
                for record, shard, input_bp_sha256 in pending
            }
            for future in as_completed(futures):
                record, shard, input_bp_sha256 = futures[future]
                consume(record, shard, input_bp_sha256, future.result())

    frame = pd.DataFrame(all_rows)
    out = output_dir / f"{experiment_name}.csv"
    frame.to_csv(out, index=False)
    return frame, out


def freeze_recent(dev_csv: str | Path, config_path: str | Path, output_json: str | Path, metric="ACC"):
    config = json.loads(Path(config_path).read_text(encoding="utf-8"))
    frame = pd.read_csv(dev_csv)
    expected_records = frame[["dataset", "pool"]].drop_duplicates().shape[0]
    required_methods = [m for m, v in config.get("methods", {}).items() if v.get("enabled", True)]
    successful = frame[(frame.status == "ok") & np.isfinite(frame[metric])].copy()
    if successful.empty:
        raise ValueError("no successful official-baseline development runs")
    frozen = {}
    scores = {}
    coverage = {}
    for method in required_methods:
        group = successful[successful.method == method]
        if group.empty:
            raise ValueError(f"{method}: no successful development runs")
        per_setting = []
        for params, rows in group.groupby("params"):
            observed = rows[["dataset", "pool"]].drop_duplicates().shape[0]
            if observed != expected_records:
                continue
            per_dataset = rows.groupby("dataset", as_index=False)[["ACC", "NMI", "ARI", "F1"]].mean(numeric_only=True)
            means = per_dataset[["ACC", "NMI", "ARI", "F1"]].mean().to_dict()
            per_setting.append((params, means))
        if not per_setting:
            raise ValueError(f"{method}: no parameter setting covers every development dataset/pool")
        per_setting.sort(key=lambda item: (item[1][metric], item[1]["NMI"], item[1]["ARI"]), reverse=True)
        params_json, method_scores = per_setting[0]
        frozen[method] = json.loads(params_json)
        scores[method] = {k: float(v) for k, v in method_scores.items()}
        coverage[method] = {"successful_records": expected_records, "expected_records": expected_records}
    payload = {
        "schema": "psfce-v4-frozen-recent-baselines-v1",
        "selection_metric": metric,
        "methods": frozen,
        "dev_scores": scores,
        "coverage": coverage,
        "source": str(dev_csv),
        "source_sha256": _file_sha256(dev_csv),
    }
    Path(output_json).parent.mkdir(parents=True, exist_ok=True)
    Path(output_json).write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return payload
