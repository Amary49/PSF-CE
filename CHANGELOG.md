# Changelog

Public GitHub releases use semantic tags (`v1.0.0`, `v1.1.0`, and the current `v1.2.0`). The V4--V10 headings retained below are internal audit-package revisions, not additional public GitHub releases.

## v1.2.0 repository and manuscript synchronization — 2026-09-24

- Replaced the active V9.1 manuscript pointer with the final-audit English manuscript V9.3 lock.
- Recorded the V9.3 Overleaf archive and verification-PDF SHA-256 values without redistributing either artifact in the code repository.
- Closed the repository-to-paper citation boundary: all five additional dataset keys required by `DATASET_CITATION_MAP.csv` are now among the manuscript's 26 used keys.
- Updated release manifests, checksums, validation guards, and current-facing documentation; frozen algorithms, parameters, predictions, scores, figures, tables, and scientific conclusions are unchanged.
- Kept V9 and earlier entries below as historical changelog records; they are not current manuscript locks.

## V9 manuscript-alignment and release-integrity pass — 2026-09-22

- Declared English manuscript V9.1, scientific evidence V5, and public repository V9 as three separate version identities.
- Removed the unsupported “MI-dominant overall” wording from every active manuscript and claim-contract entry; retained only the archived MI 5/6 and AMI 4/6 directional counts.
- Added a machine-readable V9.1 manuscript lock and an evidence-alignment note without redistributing the manuscript source inside the code repository.
- Strengthened the release validator with manuscript-lock, stale-claim, private-file, nested-archive, and GitHub-size guards.
- Preserved every frozen algorithm, prediction, score, parameter, cohort member, figure value, and table value from V8.

## V8 direct public-release cleanup — 2026-09-22

- Selected the MIT License for project-authored code, adapters, scripts, configurations, documentation, and generated paper-support artifacts.
- Added an explicit root release notice separating MIT project material from the six UCI-derived CC BY 4.0 frozen-BP artifacts.
- Closed the dependency-notice blocker without vendoring third-party packages: PyMetis and the public Python stack remain separately installed under their upstream licenses; author baseline repositories remain external.
- Corrected repository bibliography metadata for BBCSport, the Journal of Complex Networks article identifier, the HAN repository, and current UCI citation years.
- Updated release identifiers, public-readiness documents, manifest generation, and validator guards to V8.
- Preserved every frozen algorithm, prediction, score, parameter, cohort member, figure value, table value, and scientific conclusion from V7.

## V7 public-boundary and typography revision — 2026-09-22

- Preserved every frozen algorithm, prediction, score, parameter, cohort member, and scientific conclusion from V6/V4.
- Rebuilt Figure 1 at the native 3.39-inch ICASSP column width with a configured minimum font size of 9 pt.
- Re-typeset the main table and exploratory Table II at 9 pt without changing displayed values or directional counts.
- Added the six exact Iris/Mushroom frozen-BP files with UCI CC BY 4.0 attribution; the other 24 pools remain hash-only.
- Removed the privately audited YACHT compatibility helper from the public source tree and made the adapter fail explicitly until a local audited helper is supplied.
- Recorded the currently inspected MATLAB installation while keeping the historical formal-run MATLAB version marked unrecorded.
- Corrected the portable frozen-source path `results/recent_dev.csv` and regenerated all source locks, manifests, and checksums.

## V6 portability and narrative cleanup — 2026-09-22

- Converted repository text files to UTF-8/LF and regenerated every affected source lock, manifest, and checksum.
- Standardized all paths in `SOURCE_MAP.csv`, `RELEASE_MANIFEST.json`, Figure 1 manifests, and `SHA256SUMS.txt` to POSIX `/` form.
- Added validator checks for CRLF drift, backslashes in portable manifests, release-manifest hashes, and root checksum integrity.
- Removed current-document wording that described superseded V4/V5 states; historical changes remain in this changelog.
- Classified private frozen-BP access as an explicit Path B reproducibility boundary rather than a source-release blocker.
- Kept public release blocked on the project-license decision, YACHT helper origin/redistribution review, and third-party notice obligations.

## V5 paper artifacts — 2026-09-22

- Added the revised-Core-10 post-freeze Figure 1 with full-precision source CSV, plotting code, vector PDF, preview formats, and computation/build audits.
- Added the evidence-linked exploratory Table II and a deterministic rebuild script that verifies all six displayed counts against the archived reports.
- Preserved the scientific evidence version, algorithms, predictions, and frozen parameters; this is a paper-artifact update only.
- Added a test-only headless Matplotlib backend configuration so reporting tests run without Tcl/Tk; plotting values and production code are unchanged.
- Kept public-release blockers unchanged: no project license decision, unresolved YACHT helper origin, and no public frozen-BP redistribution.

## V4 cleanup — 2026-09-22

- Removed public machine paths from the MCLA/Chameleon and exploratory Experiment 3 audit records.
- Replaced the old Experiment 1 confirmatory/information-preservation narrative with an exploratory NMI-decomposition diagnostic boundary.
- Corrected and validator-checked all frozen source-lock hashes.
- Added Candidate-52 plus five-dataset replacement-panel provenance and screening outcomes.
- Separated Python package version `1.0.0`, scientific evidence V3, and GitHub cleanup release V4.
- Added formal-environment evidence, audit dependencies, portable archival-script input contracts, citation metadata, and truthful Path B limitations.
- Excluded Fig. 1 and manuscript Table II changes from V4; they are introduced separately in V5.

## V3 revised Core-10 (2026-09-22)

- Replaced the old overlap-affected Core-10 with the frozen revised cohort: removed USPS3568 and Handwritten; added Iris and Mushroom under the performance-blind exact-c candidate rule.
- Adopted the later validated exploratory Experiment 3 and cluster-mixing geometry as the current structural evidence, while preserving their non-causal status.
- Retained MCLA/Chameleon under-k native outputs and added a no-Chameleon sensitivity audit.
- Rebuilt method/dataset citations for the revised cohort.
- Corrected RANGE's CVPR 2026 page range from 39691--39699 to 39691--39700 after checking the official PDF.
- Excluded the old parameter-sensitivity figure because it was not recomputed on revised Core-10.
- Marked the early `SCIENTIFIC_UPDATE_NOT_ACCEPTED` decision as superseded rather than deleting it.
