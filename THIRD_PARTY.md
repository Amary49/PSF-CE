# Third-party software and methods

This repository contains project-written adapters and reimplementations, not vendored author repositories. The root MIT License applies only to project-authored material and does not relicense upstream software.

## Baseline implementations

- **MCLA and HBGF:** controlled project reimplementations using PyMetis; no historical author code is redistributed.
- **CEHM:** intended to run against the author MATLAB source at commit `29c22fb18e05eed67728eebcb29cd7e9133723f7` through a thin project adapter. The author repository is not vendored.
- **YACHT:** intended to run against the author MATLAB source at commit `44cb0fc35b80ec17befa199879ac947fee15f464` with the disclosed walk-order compatibility patch and opaque dependencies. The audited helper `psfce_v4_yacht_walk` is not redistributed. The public adapter fails explicitly unless the user supplies it at `<YACHT_REPO>/psfce_local_overrides/psfce_v4_yacht_walk.m`. Archived formal scores and hashes are unchanged; this restriction affects public rerun availability, not the recorded outputs.
- **RANGE:** intended to run against the author MATLAB source at commit `85d93c54d72d500034d05b5ef131bd90630a3632`; the project-wide frozen lambda differs from the paper default. The author repository is not vendored.
- **GPEC:** uses an author MATLAB snapshot authenticated by archive/tree hashes; the Git commit identity is not verified. The author source is not redistributed.

See `docs/provenance/BASELINE_CITATION_MAP.csv` and `docs/fairness/BASELINE_FAIRNESS_AUDIT.csv` for execution identity and limitations. Upstream repository license fields that remain `NOASSERTION` are intentionally not guessed because those repositories are not redistributed here.

## Separately installed Python dependencies

No Python dependency source or binary wheel is vendored in this repository. Installation obtains these packages separately, and each package remains under its own upstream license. The release records the following license metadata for the dependencies used by the public workflows:

| Dependency | Role | Recorded upstream license |
|---|---|---|
| NumPy | runtime | BSD-style / BSD-3-Clause family |
| SciPy | runtime | BSD-3-Clause |
| scikit-learn | runtime | BSD-3-Clause |
| pandas | runtime | BSD-3-Clause |
| Matplotlib | runtime / figure rebuild | Matplotlib project license (BSD-compatible) |
| threadpoolctl | runtime | BSD-3-Clause |
| h5py | optional audit | BSD-3-Clause |
| pytest | test | MIT |
| PyMetis 2025.2.2 | classic baselines | `MIT AND Apache-2.0` in PyPI package metadata |

The PyMetis 2025.2.2 license expression above was verified from the PyPI release metadata on 2026-09-22. The other entries summarize the licenses reported by their upstream package/project metadata; no dependency license is being granted by this repository.

PyMetis is intentionally kept in `requirements-classic.txt` rather than the default runtime requirements because it is needed only for the controlled classic baselines. A downstream distributor who bundles dependency binaries should review the license files shipped by those distributions; this source-only repository does not bundle them.
