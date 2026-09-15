# Reproducibility

## Version correspondence

The release is labeled `1.0.0`. Its algorithm source comes from the audited integration project, while the authoritative main scores come from the earlier frozen run rather than a stale working copy. CEHM/YACHT/RANGE scores come from the completed MATLAB run, and the fixed-strength ablation is the separately audited 53 x 3 run. Release sanitation removed inactive historical dispatch and narrowed default baseline entry points; it did not alter the frozen PSF-CE operator, solver, parameters, seeds, or archived scores.

## Frozen settings

- Main PSF-CE: `q=0.72`, `lambda=0.665`.
- Formal seed: 2027; `svd_tol=1e-11`; calibration `fro_centered`; strong rounding; K-means `n_init=40`; one BLAS thread.
- Main LinearPair: independently selected `lambda=3.0`.
- Fixed-strength linear-response ablation: `q=1.0`, `lambda=0.665`; this is not the main LinearPair record.
- Recent baselines: settings in `configs/frozen/recent_baselines.json`, selected once on the recorded development split.

## Path A: recorded-score reconstruction

`scripts/rebuild_paper_artifacts.py` checks exact method sets, one row per dataset/pool/method, 53 datasets, three pools per dataset, finite metrics, and the separation of the main LinearPair and fixed-strength ablation. It rebuilds:

- dataset-level means and equal-weight macro means;
- seven PSF-CE paired ACC comparisons with two-sided Wilcoxon and Holm correction;
- the independent two-comparison fixed-strength ablation family;
- the compact ten-dataset ACC/NMI table and full summary tables;
- a vector parameter-grid figure from archived real aggregated values.

This path verifies recorded-score aggregation. It is not a fresh algorithm run and cannot verify the recorded ACC/NMI/ARI/F1 against raw `y` and prediction labels because those are not distributed.

The historical paired-statistics files remain unchanged under `artifacts/paper_v1/statistics/`. New paired-statistics outputs are explicitly suffixed `recomputed_current_env`. This matters for the fixed-strength ablation: current pandas/SciPy floating-point tie handling reproduces the effects and Holm-adjusted conclusion but not one historical raw Wilcoxon p-value bit-for-bit. The current recomputation is not silently substituted into the paper archive.

## Path B: algorithm rerun

The portable manifest is derived from the actual 171-row execution manifest by replacing machine-specific absolute paths with `../../data/frozen_bp/<split>/<filename>`. It is a portability copy, not the historical execution record. The original manifest hash and the transformed manifest hash are recorded in provenance.

The execution scripts load only frozen settings. Development grid scripts are not part of the public main entry. New outputs go to `runtime_results/`; archived `artifacts/paper_v1/` files are never overwritten.

## Baseline boundaries

- CEHM under-cluster outputs are retained as returned; no clusters were added and no low scores were removed.
- YACHT uses a thin fixed-BP adapter and a parameterized walk order of 20 because the released helper hard-codes 10; it is not described as an untouched demo.
- RANGE depends on Windows MEX/P-code supplied by the author repository.
- The optional AWEC adapter remains for audit continuity, but it is marked experimental, excluded from every paper-default registry/audit/report, and has no paper-v1 result.
- FSEC is excluded because its full method regenerates base partitions from features.
- Formal PSF-CE score rows record `commutator_ratio` as a numerical diagnostic. It is not used for parameter, seed, restart, or candidate selection, and finite-precision nonzero values are not treated as proof of exact noncommutation.

## Timing boundary

Python solver runtime and MATLAB adapter runtime are recorded by different execution layers. They should not be interpreted as directly comparable end-to-end wall-clock measurements unless a future controlled timing study standardizes startup, I/O, caching, hardware, and warm-up.

## Verified and unverified

See `VALIDATION_REPORT.json`. Score reconstruction and import/static checks were run for this release. The 53 x 3 algorithms were not rerun during packaging. A missing local test dependency is reported as `SKIPPED`, not counted as a pass. MATLAB availability on the packaging machine is not evidence that every third-party method was rerun in this release environment.
