# Changelog

## 1.0.0 — 2026-09-16

- Curated the frozen PSF-CE source and completed CEHM/YACHT/RANGE adapters into a repository-root layout.
- Preserved the frozen PSF-CE operator, solver, seeds, numerical settings, and archived scores.
- Changed only the default paths of `run_main.py` and `run_recent_main.py` so frozen configs and new runtime outputs are the safe defaults.
- Removed inactive historical-method dispatch from the public package without changing any paper-default method.
- Restricted default recent-baseline configuration, auditing, reporting, and smoke testing to completed CEHM/YACHT/RANGE results.
- Retained the unfinished optional adapter only as explicitly marked experimental code outside the paper-default entry.
- Added the missing `configs/official_repositories.json` used by the bootstrap command.
- Added a portable manifest copy without altering the historical execution manifest.
- Added recorded-score reconstruction, validation, provenance, release documentation, and Git ignore rules.
- Archived the eight-method paper scores, fixed-strength ablation, and real parameter-grid figure inputs.
- Excluded raw data, BP matrices, predictions, caches, downloaded third-party repositories, historical-method results, and incomplete experimental results.

No model equation, numerical operator, normalization, calibration, candidate rule, random seed logic, solver budget, or recorded score was changed.
