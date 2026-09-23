from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {
    ".bib", ".cff", ".csv", ".json", ".m", ".md", ".py", ".svg",
    ".tex", ".toml", ".txt", ".yaml", ".yml",
}
TEXT_NAMES = {".gitattributes", ".gitignore", ".gitkeep"}
ROOT_GENERATED = {"SOURCE_MAP.csv", "RELEASE_MANIFEST.json", "SHA256SUMS.txt"}
EXCLUDED_DIR_NAMES = {".git", ".venv", "__pycache__", ".pytest_cache"}


def root_public_files():
    for path in ROOT.rglob("*"):
        rel_parts = path.relative_to(ROOT).parts
        if path.is_file() and not any(part in EXCLUDED_DIR_NAMES for part in rel_parts):
            yield path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_text_lf(path: Path, text: str) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(text)


def write_json_lf(path: Path, obj: object) -> None:
    write_text_lf(path, json.dumps(obj, ensure_ascii=False, indent=2) + "\n")


def normalize_text_files() -> int:
    changed = 0
    for path in sorted(root_public_files()):
        if path.parent == ROOT and path.name in ROOT_GENERATED:
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES and path.name not in TEXT_NAMES:
            continue
        raw = path.read_bytes()
        text = raw.decode("utf-8-sig")
        normalized = text.replace("\r\n", "\n").replace("\r", "\n")
        encoded = normalized.encode("utf-8")
        if encoded != raw:
            path.write_bytes(encoded)
            changed += 1
    return changed


def update_freeze_locks() -> None:
    freeze_dir = ROOT / "configs" / "frozen"
    freeze_path = freeze_dir / "REVISED_CORE10_FORMAL_FREEZE.json"
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    freeze["source_locks"] = {
        name: sha256_file(freeze_dir / name)
        for name in sorted(freeze["source_locks"])
    }
    write_json_lf(freeze_path, freeze)
    artifact_copy = ROOT / "artifacts" / "paper_revised_core10" / "provenance" / freeze_path.name
    write_json_lf(artifact_copy, freeze)


def update_figure1_hash_contracts() -> None:
    fig_root = ROOT / "artifacts" / "paper_revised_core10" / "figures" / "figure1_parameter_sensitivity"
    source_paths = {
        "cache.py": ROOT / "psfce" / "cache.py",
        "metrics.py": ROOT / "psfce" / "metrics.py",
        "models.py": ROOT / "psfce" / "models.py",
        "pair_spectrum.py": ROOT / "psfce" / "pair_spectrum.py",
        "solver.py": ROOT / "psfce" / "solver.py",
        "REVISED_CORE10_FORMAL_FREEZE.json": ROOT / "artifacts" / "paper_revised_core10" / "provenance" / "REVISED_CORE10_FORMAL_FREEZE.json",
        "main_pool_scores.csv": ROOT / "artifacts" / "paper_revised_core10" / "scores" / "main_pool_scores.csv",
    }
    computation_path = fig_root / "audit" / "FIG1_COMPUTATION_AUDIT.json"
    computation = json.loads(computation_path.read_text(encoding="utf-8"))
    for entry in computation["source_manifest"]:
        path = source_paths[entry["file_name"]]
        entry["sha256"] = sha256_file(path)
        entry["size_bytes"] = path.stat().st_size
    write_json_lf(computation_path, computation)

    freeze_hash = sha256_file(source_paths["REVISED_CORE10_FORMAL_FREEZE.json"])
    protocol_path = fig_root / "protocol" / "FIG1_REVISED_CORE10_PROTOCOL.json"
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    protocol["source_freeze_sha256"] = freeze_hash
    write_json_lf(protocol_path, protocol)

    build_path = fig_root / "audit" / "FIG1_BUILD_AUDIT.json"
    build = json.loads(build_path.read_text(encoding="utf-8"))
    build["source_csv_sha256"] = sha256_file(fig_root / "data" / "fig1_source.csv")
    build["pdf_sha256"] = sha256_file(fig_root / "figures" / "fig1_revised_core10_postfreeze_sensitivity.pdf")
    build["svg_sha256"] = sha256_file(fig_root / "figures" / "fig1_revised_core10_postfreeze_sensitivity.svg")
    build["png_sha256"] = sha256_file(fig_root / "figures" / "fig1_revised_core10_postfreeze_sensitivity.png")
    build["tex_sha256"] = sha256_file(fig_root / "figures" / "fig1_revised_core10_postfreeze_sensitivity.tex")
    write_json_lf(build_path, build)

    package_path = fig_root / "PACKAGE_MANIFEST.json"
    members = sorted(
        p for p in fig_root.rglob("*")
        if p.is_file() and p.name not in {"PACKAGE_MANIFEST.json", "SHA256SUMS.txt"}
    )
    package = {
        "package": "PSF_CE_FIG1_REVISED_CORE10_INTEGRATED_V9",
        "protocol_id": "PSFCE-FIG1-REVISED-CORE10-POSTFREEZE-20260922-V1",
        "scope": "native-column Figure 1 evidence integrated into the V9 public repository; no raw feature data, prediction archives, machine paths, or private paths",
        "file_count": len(members),
        "files": [
            {
                "path": "core10/figures/figure1_parameter_sensitivity/" + p.relative_to(fig_root).as_posix(),
                "size_bytes": p.stat().st_size,
                "sha256": sha256_file(p),
            }
            for p in members
        ],
    }
    write_json_lf(package_path, package)

    sum_members = sorted(
        p for p in fig_root.rglob("*")
        if p.is_file() and p.name != "SHA256SUMS.txt"
    )
    prefix = "core10/figures/figure1_parameter_sensitivity/"
    lines = [
        f"{sha256_file(p)}  {prefix}{p.relative_to(fig_root).as_posix()}"
        for p in sum_members
    ]
    write_text_lf(fig_root / "SHA256SUMS.txt", "\n".join(lines) + "\n")


def category(path: Path) -> str:
    if path.suffix.lower() in {".py", ".m"}:
        return "source"
    if path.suffix.lower() in {".pdf", ".png", ".svg"}:
        return "figure"
    if path.parts and path.parts[0] == "frozen_bp":
        return "redistributed_frozen_bp"
    if "artifacts" in path.parts:
        return "paper_evidence"
    return "documentation_or_config"


def build_root_manifests() -> None:
    source_excluded = ROOT_GENERATED | {"VALIDATION_REPORT.json"}
    source_files = sorted(
        p for p in root_public_files()
        if p.is_file() and p.name not in source_excluded
    )
    source_map_path = ROOT / "SOURCE_MAP.csv"
    with source_map_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=["path", "role", "origin", "sha256"],
            lineterminator="\n",
        )
        writer.writeheader()
        for path in source_files:
            writer.writerow({
                "path": path.relative_to(ROOT).as_posix(),
                "role": category(path),
                "origin": "current V10 public-release material; scientific results unchanged from the frozen revised Core-10 archive",
                "sha256": sha256_file(path),
            })

    manifest_path = ROOT / "RELEASE_MANIFEST.json"
    manifest_files = sorted(
        p for p in root_public_files()
        if p.is_file() and p.name not in {"RELEASE_MANIFEST.json", "SHA256SUMS.txt"}
    )
    manifest = {
        "schema": "psfce-release-manifest-v10",
        "release_package_id": "PSFCE-GITHUB-REVISED-CORE10-V10-PUBLIC-20260924",
        "scientific_evidence_version": "PSFCE-MANUSCRIPT-REVISED-CORE10-V5-20260922",
        "active_english_manuscript_version": "PSFCE-MANUSCRIPT-ENGLISH-REVISED-CORE10-V9.3-FINAL-AUDIT-20260924",
        "portability_cleanup_only": False,
        "public_boundary_update": True,
        "public_release_ready": True,
        "project_license": "MIT",
        "algorithms_predictions_frozen_settings_and_scores_changed": False,
        "path_format": "POSIX forward slashes",
        "text_format": "UTF-8 without BOM; LF line endings",
        "file_count_excluding_manifest_and_sums": len(manifest_files),
        "files": [
            {
                "path": p.relative_to(ROOT).as_posix(),
                "sha256": sha256_file(p),
                "bytes": p.stat().st_size,
                "category": category(p),
                "public_scope": True,
            }
            for p in manifest_files
        ],
    }
    write_json_lf(manifest_path, manifest)

    sum_files = sorted(p for p in root_public_files() if p.name != "SHA256SUMS.txt")
    lines = [f"{sha256_file(p)}  {p.relative_to(ROOT).as_posix()}" for p in sum_files]
    write_text_lf(ROOT / "SHA256SUMS.txt", "\n".join(lines) + "\n")


def main() -> None:
    changed = normalize_text_files()
    update_freeze_locks()
    update_figure1_hash_contracts()
    normalize_text_files()
    build_root_manifests()
    print(f"PASS: normalized {changed} text files and rebuilt portable hash contracts")


if __name__ == "__main__":
    main()
