# PSF-CE: revised Core-10 research release

This repository contains the PSF-CE implementation, audited baseline adapters, frozen configuration metadata, portable data-entry manifests, and redacted public-release evidence for the revised Core-10 study.

## Current version

The manuscript evidence version is `PSFCE-MANUSCRIPT-REVISED-CORE10-V5-20260922`; the current repository package is `PSFCE-GITHUB-REVISED-CORE10-V8-PUBLIC-20260922`. V8 preserves the frozen algorithms, predictions, settings, and scores while closing the public-release packaging boundary: the project-authored material is MIT-licensed, separately licensed data artifacts are explicitly carved out, dependency notices are documented, and the public YACHT adapter does not embed the privately audited compatibility helper. Read `VERSION_LOCK.json` before using any number or claim.

Authors: Haiyun Zhang (Zhejiang University; Shanxi University), Luoqi Wang (Shanxi University), and Liang Du (Shanxi University). The final paper title, DOI, and public repository URL remain pending and are not fabricated here.

**Release status:** `READY_FOR_PUBLIC_GITHUB_UPLOAD`. Upload the contents of this directory at the repository root. Read `LICENSE_STATUS.md`, `NOTICE.md`, and `THIRD_PARTY.md` before adding any new data or third-party code.

The revised Core-10 cohort contains BBC News Sport, Leukemia, Caltech101-20, Leukemia2, Chameleon, Amazon Photo, ORL, ACM, Iris, and Mushroom. The comparison contains MCLA, HBGF, CEHM, YACHT, RANGE, GPEC, and PSF-CE. Three frozen BP pools are averaged within each dataset before equal-weight averaging across datasets.

PSF-CE has the highest descriptive mean NMI and third-highest descriptive mean ACC. No NMI comparison is significant after Holm correction. Exploratory diagnostics associate the NMI-oriented profile with reduced true-class fragmentation and localized residual mixing; they do not prove a causal upstream mechanism.

The paper-artifact directory now includes (i) a post-freeze one-factor sensitivity figure rebuilt on revised Core-10 and (ii) an exploratory Table II whose six profile counts are generated from the archived structural reports. The sensitivity sweep is diagnostic only and is not used for parameter reselection. See `artifacts/paper_revised_core10/figures/figure1_parameter_sensitivity/` and `artifacts/paper_revised_core10/tables/table2_partition_structure.tex`.

## Cohort provenance

The historical 53-dataset archive became `Candidate-52` after exclusion of the provenance-conflicted binary Isolet variant. A separately frozen replacement panel contained Ecoli, Dermatology, Iris, Heart, and Mushroom. Iris and Mushroom passed the performance-blind exact-cluster-count admission rule; Heart remained provenance-unresolved. The revised formal Core-10 removes USPS3568 and Handwritten for disclosed development-provenance overlap and adds Iris and Mushroom. See `docs/provenance/COHORT_SELECTION.md` and `docs/provenance/REPLACEMENT_CANDIDATE_SCREENING.csv`.

## Reproduction paths

- Path A: `python scripts/rebuild_paper_results.py --output-dir runtime_results/rebuilt` rebuilds the main summaries from archived pool scores. It requires no raw data or MATLAB and does not rerun clustering.
- Path B is only partially public. The six exact Iris and Mushroom frozen-BP pools are redistributed under their upstream CC BY 4.0 terms in `frozen_bp/`; the other 24 pools remain hash-only and private. A full ten-dataset rerun therefore still requires locally supplied, legally obtained inputs and the third-party environments listed in `THIRD_PARTY.md`.

Install the source checkout with `python -m pip install -e .`; install audit-only dependencies with `python -m pip install -e ".[audit,test]"`; run tests with `python -m pytest -q`.

## Important boundaries

- Revised Core-10 is not called an independent holdout because of the disclosed historical development provenance.
- MCLA/Chameleon pool 0 and pool 2 return four clusters for a five-class task. Native outputs are retained.
- Raw feature data, per-sample prediction archives, the other 24 frozen-BP pools, third-party repositories, credentials, and private path maps are excluded. The six public NPZ files do contain the class labels and twenty frozen partitions used for Iris or Mushroom; this is disclosed in `frozen_bp/README.md`.
- **Public release status: READY_FOR_PUBLIC_GITHUB_UPLOAD.** Project-authored material is released under the root MIT `LICENSE`; the six redistributed UCI-derived frozen-BP files remain under CC BY 4.0 as documented in `frozen_bp/NOTICE_CC_BY_4.0.md`. Third-party repositories and dependency binaries are not vendored; see `THIRD_PARTY.md`. The YACHT compatibility helper is excluded, so YACHT reruns require a separately supplied audited local override and the upstream solver.
