# PSF-CE

PSF-CE studies source-aware pairwise interactions for clustering ensembles built from frozen base partitions. This repository-preparation snapshot preserves the implementation used by the current paper and separates executable code from the small, immutable paper-result archive.

## Frozen research scope

- PSF-CE: `q=0.72`, `lambda=0.665`.
- Main paper comparison: CA, Poly2, LinearPair, AggregatePower, CEHM, YACHT, RANGE, and PSF-CE.
- Formal scope: 53 datasets, three frozen BP pools per dataset, normally `M=20`.
- Completed recent baselines: CEHM, YACHT, RANGE.
- The paper-default recent-baseline workflow contains only CEHM, YACHT, and RANGE. Optional experimental adapters and protocol-incompatible methods are outside the public paper entry and have no result in `artifacts/paper_v1`.
- LinearPair in the main table uses its independently frozen `lambda=3.0`. The fixed-strength ablation uses a different setting, `q=1, lambda=0.665`, under the identifier `psf_q1_fixed_lambda`.

The recorded results do not support claims that PSF-CE significantly outperforms every baseline or that the nonlinear response provides a monotone improvement.

## Repository contents

- `psfce/`: frozen Python implementation. Release sanitation removed inactive historical dispatch only; the frozen PSF-CE operator, solver, seeds, numerical settings, and paper results were not changed.
- `baseline_adapters/`: thin MATLAB bridges. Third-party author repositories are not vendored.
- `configs/frozen/`: paper settings and the three-method recent-baseline registry.
- `configs/manifests/`: a portable copy of the 171-row manifest; it contains paths only, not data.
- `artifacts/paper_v1/`: small recorded scores, summaries, statistics, and provenance.
- `figures/`: real aggregated parameter-grid data, editable plotting source, and the paper's vector PDF.
- `scripts/`: frozen execution entry points, result reconstruction, and validation.

The package version is `1.0.0`. This is a release label for the curated repository, not a new experiment or model version.

## Path A: rebuild tables and figures from archived scores

This path does not require MATLAB, datasets, frozen BP matrices, or predictions. It recomputes dataset-balanced summaries from recorded scores; it does **not** rerun clustering or recompute metrics from raw labels.

```powershell
python -m pip install -r requirements.txt
python scripts\rebuild_paper_artifacts.py --output rebuild_output
```

The command validates 53 x 3 coverage, averages the three pools within each dataset, then averages datasets equally. It emits CSV/LaTeX tables and a vector PDF reconstructed from the archived parameter-grid values. The exact paper TikZ source is also retained under `figures/source/`.

## Path B: rerun from frozen BP files

Place data according to `configs/manifests/portable_manifest.csv`, then run from the repository root. These commands read frozen parameters and write to a new untracked directory.

```powershell
python scripts\run_main.py `
  --manifest configs\manifests\portable_manifest.csv `
  --frozen configs\frozen\main_methods.json `
  --config configs\frozen\formal_main.json `
  --output runtime_results\main `
  --workers 1

python scripts\run_recent_main.py `
  --manifest configs\manifests\portable_manifest.csv `
  --registry configs\frozen\recent_baselines_registry.json `
  --frozen configs\frozen\recent_baselines.json `
  --output runtime_results\recent `
  --workers 1
```

Path B requires the licensed MATLAB/toolbox and pinned author repositories described in `THIRD_PARTY.md`. It does not run development tuning. Missing data or dependencies are intended to fail explicitly. Do not use `--force` unless intentionally replacing a separate runtime directory.

To fetch only the three paper-default author repositories at their pinned commits, run:

```powershell
python scripts\bootstrap_official_repos.py
```

See `REPRODUCIBILITY.md`, `DATA_AVAILABILITY.md`, `THIRD_PARTY.md`, and `VALIDATION_REPORT.json` for the exact reproduction and release boundaries.

For local regression tests, install the test dependency set and run:

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

## Release status

This curated package is **ready for public GitHub release** as version `v1.0.0`. Original PSF-CE repository content is released under the MIT License. Complete third-party author repositories and raw data/BP files are intentionally not redistributed; their upstream terms remain separate.

The release status refers to this curated repository snapshot and the archived paper-result summaries. It does not claim that the 53 x 3 algorithms were rerun during packaging, nor does it convert the recorded oracle/diagnostic experiments into frozen test results.
