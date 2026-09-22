# Reproducibility

## Path A: rebuild paper summaries from archived scores

Run `python scripts/rebuild_paper_results.py --output-dir runtime_results/rebuilt`. This verifies 10 datasets x 3 pools x 7 methods and reconstructs dataset means and method means. It does not execute a clustering method, use ground-truth labels to recompute metrics, or validate MATLAB.

## Path B: internal/full reproduction from frozen BP pools

This path is not publicly closed end to end. The release distributes the exact three Iris pools and three Mushroom pools under CC BY 4.0 in `frozen_bp/`; their bytes are checked against `data/bp_pool_hashes.csv`. The remaining 24 pools are hash-only. Configure any private inputs through a local ignored file based on `data/local_paths.example.yaml`. Install the pinned third-party sources and revisions from `docs/provenance/BASELINE_CITATION_MAP.csv`; MATLAB methods require their original dependencies. YACHT additionally requires the audited private compatibility helper described in `THIRD_PARTY.md`. New runs must write to `runtime_results/` and must not overwrite `artifacts/paper_revised_core10/`.

The public package has not rerun all MATLAB algorithms from raw data. The archived run reports 300/300 method/pool outputs for ten methods; the paper comparison uses 210 rows for seven methods. Historical development selection is not automatically rerun.

The exploratory Experiment 3 and mixing-geometry scripts are archival analysis entry points. They require private prediction/label inputs supplied through the documented `PSFCE_*` environment variables; their presence does not imply that the public package contains those inputs.

Use `python -m pip install -e .` followed by `python -m pytest -q`. Audit scripts additionally require `requirements-audit.txt` or the `audit` optional dependency.

## Paper artifacts

- Rebuild Figure 1 from its archived full-precision summary with `python artifacts/paper_revised_core10/figures/figure1_parameter_sensitivity/scripts/build_figure1.py --root artifacts/paper_revised_core10/figures/figure1_parameter_sensitivity`. This redraws the figure but does not rerun clustering or reselect parameters.
- Rebuild Table II with `python scripts/rebuild_table2.py`. The script reads the two archived exploratory structural reports, verifies the six revised-Core-10 counts and the no-Chameleon sensitivity, and rewrites the source CSV, LaTeX table, and validation record.
