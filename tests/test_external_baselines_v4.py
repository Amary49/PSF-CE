from pathlib import Path
import json

import numpy as np

from psfce.external_baselines import (
    ExternalBaselineSpec,
    _write_bridge_input,
    base_partition_sha256,
    bridge_input_keys,
    cache_key,
    load_external_registry,
    run_external_baseline,
    standard_parts_matrix,
)


def heterogeneous_parts(n=300):
    ks = [4, 5, 6, 8, 10] * 4
    parts = [np.arange(n, dtype=np.int32) % k for k in ks]
    return parts, ks


def spec(name="CEHM", commit="a" * 40):
    return ExternalBaselineSpec(
        name=name,
        status="enabled" if name != "FSEC" else "protocol_incompatible",
        backend="matlab",
        repo_url=f"https://example.invalid/{name}.git",
        commit=commit,
        retrieval_date="2026-09-14",
        repo_root="missing",
        matlab_adapter=f"psfce_adapter_{name.lower()}",
    )


def test_standard_matrix_supports_heterogeneous_k():
    parts, ks = heterogeneous_parts()
    matrix = standard_parts_matrix(parts)
    assert matrix.shape == (300, 20)
    assert [len(np.unique(matrix[:, j])) for j in range(20)] == ks
    assert matrix.min() == 1


def test_bridge_contains_no_ground_truth(tmp_path: Path):
    parts, _ = heterogeneous_parts()
    path = tmp_path / "input.mat"
    _write_bridge_input(path, parts, 5, 2027, {"alpha": 0.95})
    keys = bridge_input_keys(path)
    assert keys == {"base_parts", "c", "seed", "params_json", "input_meta_json"}
    assert not ({"y", "Y", "gt", "labels", "ground_truth"} & keys)


def test_cache_key_binds_bp_commit_params_and_seed():
    parts, _ = heterogeneous_parts()
    base = cache_key(spec(), parts, 5, {"x": 1}, 7)
    changed_parts = [p.copy() for p in parts]
    changed_parts[0][0] = changed_parts[0][0] + 1
    assert base != cache_key(spec(), changed_parts, 5, {"x": 1}, 7)
    assert base != cache_key(spec(commit="b" * 40), parts, 5, {"x": 1}, 7)
    assert base != cache_key(spec(), parts, 5, {"x": 2}, 7)
    assert base != cache_key(spec(), parts, 5, {"x": 1}, 8)
    revised = spec()
    object.__setattr__(revised, "adapter_revision", "v2")
    assert base != cache_key(revised, parts, 5, {"x": 1}, 7)
    assert len(base_partition_sha256(parts)) == 64


def test_fsec_is_hard_blocked_without_invoking_backend(tmp_path: Path):
    parts, _ = heterogeneous_parts()
    result = run_external_baseline(spec("FSEC"), parts, 5, {}, 7, "toy", "0", tmp_path)
    assert result["status"] == "error"
    assert "protocol_incompatible" in result["error"]
    assert result["labels"] is None


def test_registry_rejects_dream(tmp_path: Path):
    path = tmp_path / "registry.json"
    data = {"methods": {"DREAM": {
        "status": "enabled", "backend": "matlab", "repo_url": "x", "commit": "x",
        "retrieval_date": "x", "repo_root": "x", "matlab_adapter": "x"
    }}}
    path.write_text(json.dumps(data), encoding="utf-8")
    try:
        load_external_registry(path)
    except Exception as exc:
        assert "DREAM" in str(exc)
    else:
        raise AssertionError("DREAM registry entry must be rejected")


def test_shipped_registry_has_exact_paper_default_set():
    root = Path(__file__).resolve().parents[1]
    registry = load_external_registry(root / "configs" / "recent_baselines_registry.json")
    assert set(registry) == {"CEHM", "YACHT", "RANGE"}
    assert all(registry[m].status == "enabled" for m in registry)
    assert all(registry[m].backend == "matlab" for m in registry)
