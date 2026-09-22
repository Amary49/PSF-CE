from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DATASETS = [
    "BBC News Sport", "Leukemia", "Caltech101-20", "Leukemia2",
    "Chameleon", "Amazon Photo", "ORL", "ACM", "Iris", "Mushroom",
]
METHODS = ["MCLA", "HBGF", "CEHM", "YACHT", "RANGE", "GPEC", "PSF-CE"]
errors: list[str] = []


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


required = [
    "VERSION_LOCK.json", "MANUSCRIPT_SOURCE_OF_TRUTH.md", "LICENSE", "LICENSE_STATUS.md", "NOTICE.md", "THIRD_PARTY.md",
    "PAPER_CLAIMS_CONTRACT.md", "PAPER_CLAIMS_CONTRACT.csv", "CITATION.cff", "ENVIRONMENT_LOCK.json",
    "docs/manuscript/ENGLISH_MANUSCRIPT_V9_1_LOCK.json",
    "docs/manuscript/ENGLISH_MANUSCRIPT_V9_1_ALIGNMENT.md",
    "psfce/__init__.py", "configs/frozen/REVISED_CORE10_FORMAL_FREEZE.json",
    "data/dataset_manifest.csv", "data/dataset_manifest_candidate52.csv",
    "data/bp_pool_hashes.csv", "data/cohorts/candidate52.txt",
    "data/cohorts/replacement_candidates5.txt", "docs/provenance/COHORT_SELECTION.md",
    "docs/provenance/REPLACEMENT_CANDIDATE_SCREENING.csv",
    "docs/provenance/BASELINE_CITATION_MAP.csv",
    "docs/provenance/DATASET_CITATION_MAP.csv",
    "docs/provenance/refs_baselines_datasets_verified.bib",
    "artifacts/paper_revised_core10/scores/main_pool_scores.csv",
    "artifacts/paper_revised_core10/figures/figure1_parameter_sensitivity/data/fig1_source.csv",
    "artifacts/paper_revised_core10/figures/figure1_parameter_sensitivity/scripts/build_figure1.py",
    "artifacts/paper_revised_core10/figures/figure1_parameter_sensitivity/figures/fig1_revised_core10_postfreeze_sensitivity.pdf",
    "artifacts/paper_revised_core10/figures/figure1_parameter_sensitivity/audit/VALIDATION_REPORT.json",
    "artifacts/paper_revised_core10/tables/table2_partition_structure.tex",
    "artifacts/paper_revised_core10/tables/revised_main_table.tex",
    "artifacts/paper_revised_core10/tables/table2_partition_structure_source.csv",
    "artifacts/paper_revised_core10/tables/TABLE2_VALIDATION.json",
    "scripts/rebuild_table2.py",
    "frozen_bp/README.md", "frozen_bp/NOTICE_CC_BY_4.0.md",
    "frozen_bp/REDISTRIBUTION_STATUS.csv",
]
for rel in required:
    if not (ROOT / rel).is_file():
        errors.append("missing: " + rel)

text_extensions = {".py", ".md", ".json", ".csv", ".tex", ".yaml", ".yml", ".toml", ".txt", ".cff"}
portable_text_extensions = text_extensions | {".bib", ".m", ".svg"}
portable_text_names = {".gitattributes", ".gitignore", ".gitkeep"}
drive_path = re.compile(r"(?i)\b[A-Z]:[\\/]+")
forbidden_names = {".env", "id_rsa", "id_ed25519", "credentials.json", "secrets.json"}
archive_suffixes = {".zip", ".7z", ".rar", ".tar", ".tgz", ".gz"}
for path in ROOT.rglob("*"):
    rel_parts = path.relative_to(ROOT).parts
    if any(part in {".git", ".venv", "__pycache__", ".pytest_cache"} for part in rel_parts):
        errors.append("forbidden path: " + path.relative_to(ROOT).as_posix())
    if path.is_symlink():
        errors.append("symlink not allowed in public archive: " + path.relative_to(ROOT).as_posix())
    if path.is_file() and path.name.lower() in forbidden_names:
        errors.append("sensitive filename: " + path.relative_to(ROOT).as_posix())
    if path.is_file() and path.suffix.lower() in archive_suffixes:
        errors.append("nested archive: " + path.relative_to(ROOT).as_posix())
    if path.is_file() and path.stat().st_size > 90 * 1024 * 1024:
        errors.append("file exceeds 90 MiB public-release guard: " + path.relative_to(ROOT).as_posix())
    if path.is_file() and (path.suffix.lower() in portable_text_extensions or path.name in portable_text_names):
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        if drive_path.search(text):
            errors.append("machine path: " + path.relative_to(ROOT).as_posix())
        for pattern in (
            r"AKIA[0-9A-Z]{16}", r"gh[pousr]_[A-Za-z0-9_]{20,}",
            r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
            r"sk-[A-Za-z0-9_-]{20,}", r"AIza[0-9A-Za-z_-]{35}",
            r"xox[baprs]-[0-9A-Za-z-]{20,}",
        ):
            if re.search(pattern, text):
                errors.append("possible secret: " + path.relative_to(ROOT).as_posix())
    if path.is_file() and (path.suffix.lower() in portable_text_extensions or path.name in portable_text_names):
        raw = path.read_bytes()
        if raw.startswith(b"\xef\xbb\xbf"):
            errors.append("UTF-8 BOM in portable text: " + path.relative_to(ROOT).as_posix())
        if b"\r" in raw:
            errors.append("non-LF line ending: " + path.relative_to(ROOT).as_posix())

pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
init_text = (ROOT / "psfce/__init__.py").read_text(encoding="utf-8")
if 'version = "1.0.0"' not in pyproject or "__version__='1.0.0'" not in init_text:
    errors.append("Python package version mismatch")
if 'include = ["psfce*", "baseline_adapters*"]' not in pyproject:
    errors.append("baseline_adapters excluded from package discovery")

license_text = (ROOT / "LICENSE").read_text(encoding="utf-8")
license_status_text = (ROOT / "LICENSE_STATUS.md").read_text(encoding="utf-8")
readme_text = (ROOT / "README.md").read_text(encoding="utf-8")
third_party_text = (ROOT / "THIRD_PARTY.md").read_text(encoding="utf-8")
if not license_text.startswith("MIT License\n") or "Permission is hereby granted, free of charge" not in license_text:
    errors.append("root MIT license missing or malformed")
if "READY_FOR_PUBLIC_GITHUB_UPLOAD" not in readme_text or "Public source release status: READY" not in license_status_text:
    errors.append("public-release readiness wording missing")
if "MIT AND Apache-2.0" not in third_party_text or "not vendored" not in third_party_text.lower():
    errors.append("third-party dependency notice incomplete")
if 'license = {file = "LICENSE"}' not in pyproject:
    errors.append("Python project license metadata missing")
if "version: 1.0.1" not in (ROOT / "CITATION.cff").read_text(encoding="utf-8"):
    errors.append("CITATION.cff release version mismatch")

current_text_files = [
    ROOT / "README.md", ROOT / "LICENSE_STATUS.md", ROOT / "RELEASE_CHECKLIST_CN.md", ROOT / "KNOWN_LIMITATIONS.md"
]
for current_file in current_text_files:
    current = current_file.read_text(encoding="utf-8")
    for stale in ("NOT_READY_FOR_PUBLIC_RELEASE", "BLOCKED_PENDING_PROJECT_LICENSE", "project license not yet selected", "Public release remains blocked"):
        if stale in current:
            errors.append(f"stale public blocker in {current_file.name}: {stale}")

bib_text = (ROOT / "docs/provenance/refs_baselines_datasets_verified.bib").read_text(encoding="utf-8")
for required_bib in (
    "author={Greene, Derek},title={{BBC} Datasets}",
    "note={Art. no. cnab014}",
    "author={{Jhy1993}},title={{HAN}: Heterogeneous Graph Neural Network}",
    "title={Iris},publisher={UCI Machine Learning Repository},year={1936}",
    "title={Mushroom},publisher={UCI Machine Learning Repository},year={1981}",
):
    if required_bib not in bib_text:
        errors.append("bibliography public-release correction missing: " + required_bib)

version_lock = json.loads((ROOT / "VERSION_LOCK.json").read_text(encoding="utf-8"))
if version_lock.get("version_id") != "PSFCE-MANUSCRIPT-REVISED-CORE10-V5-20260922":
    errors.append("V5 manuscript evidence lock mismatch")
if version_lock.get("release_package_id") != "PSFCE-GITHUB-REVISED-CORE10-V9-PUBLIC-20260922":
    errors.append("V9 release package lock mismatch")
if version_lock.get("active_english_manuscript_version") != "PSFCE-MANUSCRIPT-ENGLISH-REVISED-CORE10-V9.1-FINALFORMAT-20260922":
    errors.append("V9.1 English manuscript lock mismatch")
if version_lock.get("active_english_manuscript_archive_sha256") != "b832b9bbc83cb663f5aa84ce51e3d7bad359e1f18d59db6d79ec7f1f8b768656":
    errors.append("V9.1 English manuscript archive hash mismatch")
if version_lock.get("active_manuscript_citation_count") != 21:
    errors.append("V9.1 manuscript citation-count lock mismatch")
if version_lock.get("public_release_status") != "READY_FOR_PUBLIC_GITHUB_UPLOAD":
    errors.append("public release status lock mismatch")
if version_lock.get("project_license") != "MIT":
    errors.append("project license lock mismatch")

manuscript_link = json.loads((ROOT / "docs/manuscript/ENGLISH_MANUSCRIPT_V9_1_LOCK.json").read_text(encoding="utf-8"))
if manuscript_link.get("manuscript_version") != version_lock.get("active_english_manuscript_version"):
    errors.append("manuscript-link version mismatch")
if manuscript_link.get("archive_sha256") != version_lock.get("active_english_manuscript_archive_sha256"):
    errors.append("manuscript-link archive hash mismatch")
if manuscript_link.get("compatible_repository_release") != version_lock.get("release_package_id"):
    errors.append("manuscript-link repository compatibility mismatch")
if manuscript_link.get("manuscript_source_included") is not False:
    errors.append("manuscript-source inclusion boundary mismatch")

source_truth_text = (ROOT / "MANUSCRIPT_SOURCE_OF_TRUTH.md").read_text(encoding="utf-8")
if "whose positive-NMI decomposition is MI-dominant overall" in source_truth_text:
    errors.append("stale MI-dominance assertion in MANUSCRIPT_SOURCE_OF_TRUTH.md")
claims_md_text = (ROOT / "PAPER_CLAIMS_CONTRACT.md").read_text(encoding="utf-8")
active_claim_sections = claims_md_text.split("## Forbidden", 1)[0]
if "MI-dominant overall" in active_claim_sections:
    errors.append("stale MI-dominance assertion in active claim sections")
claims_csv_text = (ROOT / "PAPER_CLAIMS_CONTRACT.csv").read_text(encoding="utf-8")
if "C-DECOMP-01,FORBIDDEN" not in claims_csv_text or "no MI-dominance claim" not in claims_csv_text:
    errors.append("claim-contract MI-dominance boundary missing")

freeze_path = ROOT / "configs/frozen/REVISED_CORE10_FORMAL_FREEZE.json"
freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
for name, expected in freeze.get("source_locks", {}).items():
    target = ROOT / "configs/frozen" / name
    if not target.is_file():
        errors.append("missing source lock target: " + name)
    elif sha256_file(target).lower() != str(expected).lower():
        errors.append("source lock mismatch: " + name)
artifact_freeze = ROOT / "artifacts/paper_revised_core10/provenance/REVISED_CORE10_FORMAL_FREEZE.json"
if artifact_freeze.is_file():
    artifact_freeze_obj = json.loads(artifact_freeze.read_text(encoding="utf-8-sig"))
    if artifact_freeze_obj != freeze:
        errors.append("formal freeze public copies differ")

recent = json.loads((ROOT / "configs/frozen/recent_frozen_methods.json").read_text(encoding="utf-8"))
if recent.get("source") != "results/recent_dev.csv":
    errors.append("recent-baseline source path is not portable")

rows = list(csv.DictReader((ROOT / "artifacts/paper_revised_core10/scores/main_pool_scores.csv").open(encoding="utf-8-sig")))
keys = {(row["dataset"], int(row["pool"]), row["method"]) for row in rows}
expected_keys = {(dataset, pool, method) for dataset in DATASETS for pool in range(3) for method in METHODS}
if len(rows) != 210 or keys != expected_keys:
    errors.append(f"score coverage rows={len(rows)} missing={len(expected_keys-keys)} extra={len(keys-expected_keys)}")
under = [row for row in rows if row["dataset"] == "Chameleon" and row["method"] == "MCLA" and int(row["returned_k"]) != int(row["target_c"])]
if {(int(row["pool"]), int(row["returned_k"]), int(row["target_c"])) for row in under} != {(0, 4, 5), (2, 4, 5)}:
    errors.append("MCLA/Chameleon native-output audit drift")

baseline_map = list(csv.DictReader((ROOT / "docs/provenance/BASELINE_CITATION_MAP.csv").open(encoding="utf-8-sig")))
dataset_map = list(csv.DictReader((ROOT / "docs/provenance/DATASET_CITATION_MAP.csv").open(encoding="utf-8-sig")))
if {row["method"] for row in baseline_map} != set(METHODS):
    errors.append("baseline citation coverage")
if {row["project_name"] for row in dataset_map} != set(DATASETS):
    errors.append("dataset citation coverage")
if any(not row["citation_keys"] or not row["official_source"] for row in dataset_map):
    errors.append("dataset citation/source blank")
candidate52 = [line.strip() for line in (ROOT / "data/cohorts/candidate52.txt").read_text(encoding="utf-8-sig").splitlines() if line.strip()]
replacement5 = [line.strip() for line in (ROOT / "data/cohorts/replacement_candidates5.txt").read_text(encoding="utf-8-sig").splitlines() if line.strip()]
candidate_manifest = list(csv.DictReader((ROOT / "data/dataset_manifest_candidate52.csv").open(encoding="utf-8-sig")))
screening = list(csv.DictReader((ROOT / "docs/provenance/REPLACEMENT_CANDIDATE_SCREENING.csv").open(encoding="utf-8-sig")))
if len(candidate52) != 52 or len(set(candidate52)) != 52 or len(candidate_manifest) != 52:
    errors.append("Candidate-52 coverage")
if replacement5 != ["Ecoli", "Dermatology", "Iris", "Heart", "Mushroom"] or len(screening) != 5:
    errors.append("replacement-candidate coverage/order")
admitted = {row["candidate"] for row in screening if row["admitted_to_revised_core10"].lower() == "true"}
if admitted != {"Iris", "Mushroom"}:
    errors.append("replacement admission drift")
heart = next((row for row in screening if row["candidate"] == "Heart"), None)
if not heart or heart["provenance_status"] != "PROVENANCE_UNRESOLVED":
    errors.append("Heart provenance boundary lost")

bp_rows = list(csv.DictReader((ROOT / "data/bp_pool_hashes.csv").open(encoding="utf-8-sig")))
status_rows = list(csv.DictReader((ROOT / "frozen_bp/REDISTRIBUTION_STATUS.csv").open(encoding="utf-8-sig")))
if len(bp_rows) != 30 or len(status_rows) != 30:
    errors.append("frozen-BP status coverage")
bp_lookup = {(r["dataset"], int(r["pool"])): r for r in bp_rows}
public_rows = [r for r in status_rows if r["redistribution_status"] == "PUBLIC_CC_BY_4_0"]
hash_only_rows = [r for r in status_rows if r["redistribution_status"] == "HASH_ONLY"]
if {(r["dataset"], int(r["pool"])) for r in public_rows} != {(d, p) for d in ("Iris", "Mushroom") for p in range(3)}:
    errors.append("public frozen-BP scope drift")
if len(hash_only_rows) != 24:
    errors.append("hash-only frozen-BP count drift")
for row in public_rows:
    target = ROOT / row["public_relative_path"]
    key = (row["dataset"], int(row["pool"]))
    if not target.is_file() or sha256_file(target) != bp_lookup[key]["bp_file_sha256"]:
        errors.append("public frozen-BP hash mismatch: " + row["public_relative_path"])
        continue
    with np.load(target, allow_pickle=False) as obj:
        expected_n = int(row["n"])
        if set(obj.files) != {"y", "parts"} or obj["y"].shape not in {(expected_n,), (expected_n, 1)} or obj["parts"].shape != (20, expected_n):
            errors.append("public frozen-BP array contract mismatch: " + row["public_relative_path"])
if any(row["public_relative_path"] for row in hash_only_rows):
    errors.append("hash-only frozen-BP row exposes a public path")

yacht_text = (ROOT / "baseline_adapters/matlab/psfce_adapter_yacht.m").read_text(encoding="utf-8")
if "function R = psfce_v4_yacht_walk" in yacht_text:
    errors.append("private YACHT helper embedded in public adapter")
if "PSFCE:YACHT:MissingPrivateCompatibilityHelper" not in yacht_text:
    errors.append("public YACHT adapter lacks explicit missing-helper failure")

source_map = ROOT / "SOURCE_MAP.csv"
if source_map.is_file():
    source_rows = list(csv.DictReader(source_map.open(encoding="utf-8-sig")))
    if any(row.get("path") == "SOURCE_MAP.csv" for row in source_rows):
        errors.append("SOURCE_MAP.csv self-reference")
    for row in source_rows:
        if "\\" in row.get("path", ""):
            errors.append("SOURCE_MAP non-POSIX path: " + row.get("path", ""))
        target = ROOT / row.get("path", "")
        if not target.is_file():
            errors.append("SOURCE_MAP missing target: " + row.get("path", ""))
        elif sha256_file(target).lower() != row.get("sha256", "").lower():
            errors.append("SOURCE_MAP hash mismatch: " + row.get("path", ""))

release_manifest = ROOT / "RELEASE_MANIFEST.json"
if release_manifest.is_file():
    release_obj = json.loads(release_manifest.read_text(encoding="utf-8"))
    if release_obj.get("schema") != "psfce-release-manifest-v9":
        errors.append("RELEASE_MANIFEST schema mismatch")
    if release_obj.get("release_package_id") != version_lock.get("release_package_id"):
        errors.append("RELEASE_MANIFEST release-package mismatch")
    if release_obj.get("active_english_manuscript_version") != version_lock.get("active_english_manuscript_version"):
        errors.append("RELEASE_MANIFEST manuscript-version mismatch")
    if release_obj.get("public_release_ready") is not True:
        errors.append("RELEASE_MANIFEST public-readiness mismatch")
    release_rows = release_obj.get("files", [])
    if release_obj.get("file_count_excluding_manifest_and_sums") != len(release_rows):
        errors.append("RELEASE_MANIFEST file count mismatch")
    for row in release_rows:
        rel = row.get("path", "")
        if "\\" in rel:
            errors.append("RELEASE_MANIFEST non-POSIX path: " + rel)
            continue
        target = ROOT / rel
        if not target.is_file():
            errors.append("RELEASE_MANIFEST missing target: " + rel)
        elif sha256_file(target).lower() != row.get("sha256", "").lower():
            errors.append("RELEASE_MANIFEST hash mismatch: " + rel)
        elif target.stat().st_size != int(row.get("bytes", -1)):
            errors.append("RELEASE_MANIFEST size mismatch: " + rel)

sums_path = ROOT / "SHA256SUMS.txt"
if sums_path.is_file():
    seen = set()
    for line in sums_path.read_text(encoding="utf-8").splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  (.+)", line)
        if not match:
            errors.append("malformed SHA256SUMS line: " + line[:80])
            continue
        expected_hash, rel = match.groups()
        if "\\" in rel:
            errors.append("SHA256SUMS non-POSIX path: " + rel)
            continue
        target = ROOT / rel
        seen.add(rel)
        if not target.is_file():
            errors.append("SHA256SUMS missing target: " + rel)
        elif sha256_file(target).lower() != expected_hash:
            errors.append("SHA256SUMS hash mismatch: " + rel)
    expected_sum_paths = {
        p.relative_to(ROOT).as_posix() for p in ROOT.rglob("*")
        if p.is_file() and p.name != "SHA256SUMS.txt"
    }
    if seen != expected_sum_paths:
        errors.append("SHA256SUMS coverage mismatch")

exp1 = (ROOT / "artifacts/paper_revised_core10/mechanism/experiment1/PART1_INFORMATION_MECHANISM_REPORT.md").read_text(encoding="utf-8")
for forbidden in (
    "frozen confirmatory mechanism analysis",
    "unchanged score-free exact-cluster-count cohort",
    "supporting an information-preservation interpretation",
):
    if forbidden in exp1:
        errors.append("old Experiment 1 narrative: " + forbidden)

with tempfile.TemporaryDirectory() as temp_dir:
    completed = subprocess.run(
        [sys.executable, "-B", str(ROOT / "scripts/rebuild_paper_results.py"), "--output-dir", temp_dir],
        capture_output=True, text=True,
    )
    if completed.returncode:
        errors.append("Path A rebuild failed: " + completed.stderr[-500:])

fig_root = ROOT / "artifacts/paper_revised_core10/figures/figure1_parameter_sensitivity"
fig_rows = list(csv.DictReader((fig_root / "data/fig1_source.csv").open(encoding="utf-8-sig")))
if len(fig_rows) != 11 or {row["panel"] for row in fig_rows} != {"q", "lambda"}:
    errors.append("Figure 1 source coverage")
if any(int(row["n_datasets"]) != 10 or int(row["n_pools"]) != 30 for row in fig_rows):
    errors.append("Figure 1 aggregation coverage")
q_grid = [float(row["parameter"]) for row in fig_rows if row["panel"] == "q"]
lambda_grid = [float(row["parameter"]) for row in fig_rows if row["panel"] == "lambda"]
if q_grid != [0.3, 0.72, 1.0, 6.0, 12.0] or lambda_grid != [0.1, 0.5, 0.665, 1.0, 4.0, 12.0]:
    errors.append("Figure 1 parameter grid/order")
fig_audit = json.loads((fig_root / "audit/VALIDATION_REPORT.json").read_text(encoding="utf-8-sig"))
if fig_audit.get("status") != "PASS" or fig_audit.get("parameter_reselection_performed") is not False:
    errors.append("Figure 1 audit boundary")
fig_build = json.loads((fig_root / "audit/FIG1_BUILD_AUDIT.json").read_text(encoding="utf-8-sig"))
if fig_build.get("native_canvas_inches") != [3.39, 1.82] or float(fig_build.get("minimum_configured_font_pt", 0)) < 9 or fig_build.get("manuscript_downscaling_required") is not False:
    errors.append("Figure 1 native-size/9-pt contract")
with tempfile.TemporaryDirectory() as temp_dir:
    temp_root = Path(temp_dir)
    (temp_root / "data").mkdir()
    shutil.copy2(fig_root / "data/fig1_source.csv", temp_root / "data/fig1_source.csv")
    completed = subprocess.run(
        [sys.executable, "-B", str(fig_root / "scripts/build_figure1.py"), "--root", str(temp_root)],
        capture_output=True, text=True,
    )
    rebuilt_pdf = temp_root / "figures/fig1_revised_core10_postfreeze_sensitivity.pdf"
    if completed.returncode or not rebuilt_pdf.is_file():
        errors.append("Figure 1 rebuild failed: " + completed.stderr[-500:])
    elif b"/Subtype /Image" in rebuilt_pdf.read_bytes():
        errors.append("Figure 1 PDF contains raster image objects")

completed = subprocess.run(
    [sys.executable, "-B", str(ROOT / "scripts/rebuild_table2.py")],
    capture_output=True, text=True,
)
if completed.returncode:
    errors.append("Table II rebuild failed: " + completed.stderr[-500:])
table_rows = list(csv.DictReader((ROOT / "artifacts/paper_revised_core10/tables/table2_partition_structure_source.csv").open(encoding="utf-8-sig")))
if [int(row["favorable_comparators"]) for row in table_rows] != [5, 5, 5, 5, 5, 1]:
    errors.append("Table II count drift")
if any(row["analysis_status"] != "EXPLORATORY_NOT_CONFIRMATORY" for row in table_rows):
    errors.append("Table II exploratory boundary")
if any(row["core9_same_count"].lower() != "true" for row in table_rows):
    errors.append("Table II no-Chameleon sensitivity drift")
table_tex = (ROOT / "artifacts/paper_revised_core10/tables/table2_partition_structure.tex").read_text(encoding="utf-8")
for required_text in (
    r"\caption{Exploratory partition-structure directional profiles",
    r"\label{tab:partition_structure}",
    "not significance-test counts",
    r"\geq 4/6",
    "consistent with localized residual mixing",
):
    if required_text not in table_tex:
        errors.append("Table II missing text: " + required_text)
if table_tex.count("{") != table_tex.count("}"):
    errors.append("Table II unbalanced braces")
main_table_tex = (ROOT / "artifacts/paper_revised_core10/tables/revised_main_table.tex").read_text(encoding="utf-8")
for name, text_value in (("Table I", main_table_tex), ("Table II", table_tex)):
    if r"\fontsize{9}{10.2}\selectfont" not in text_value:
        errors.append(name + " lacks explicit 9-pt body")
    if re.search(r"\\fontsize\{(?:[0-8](?:\.\d+)?)\}", text_value):
        errors.append(name + " contains sub-9-pt text")

if errors:
    print("FAIL")
    print("\n".join(errors))
    raise SystemExit(1)
print(
    "PASS: portable LF text, POSIX manifests, root checksums, structure, source locks, 210-cell coverage, citation coverage, "
    "Candidate-52 plus replacement-panel provenance, native under-k preservation, "
    "machine-path/secret scan, narrative guard, package version, Path A rebuild, "
    "Figure 1 rebuild, Table II evidence reconstruction, and V9 public-license/readiness guards"
)
