# English manuscript V9.3 alignment

This public repository is aligned with `PSFCE-MANUSCRIPT-ENGLISH-REVISED-CORE10-V9.3-FINAL-AUDIT-20260924`. The manuscript archive and verification PDF are not redistributed here; their filenames and SHA-256 identities are recorded in `ENGLISH_MANUSCRIPT_V9_3_LOCK.json`.

## Version separation

- Scientific evidence: `PSFCE-MANUSCRIPT-REVISED-CORE10-V5-20260922`.
- Active English manuscript: `PSFCE-MANUSCRIPT-ENGLISH-REVISED-CORE10-V9.3-FINAL-AUDIT-20260924`.
- Public repository: `PSFCE-GITHUB-REVISED-CORE10-V10-PUBLIC-20260924`.

Repository V10 changes manuscript linkage, citation closure, and release-integrity metadata only. It does not change an algorithm, frozen parameter, prediction, score, cohort member, figure value, table value, or scientific conclusion.

## Citation closure

The active manuscript uses 26 citation keys. In addition to the 21 keys already used by V9.1, V9.3 cites the five dataset records required by `docs/provenance/DATASET_CITATION_MAP.csv`:

- `Caltech101Dataset2022` for Caltech101-20;
- `Rozemberczki2021MUSAE` for Chameleon;
- `ORLDatabase` for AT&T/ORL;
- `HANDatasetRelease` for ACM-3025;
- `Fisher1936Iris` for UCI Iris.

All 26 manuscript keys resolve in the manuscript bibliography. The repository bibliography remains a broader provenance bibliography rather than a copy of the paper bibliography.

## Claim and artifact alignment

- PSF-CE has the highest descriptive mean NMI and third-highest descriptive mean ACC on revised Core-10.
- No paired NMI comparison remains significant after Holm correction.
- The exploratory partition diagnostics report favorable MI and AMI directions for 5/6 and 4/6 comparators, respectively, without a causal claim.
- Table I, Figure 1, Table II, and all full-precision result sources remain unchanged; the V9.3 paper only restores the missing underline on GPEC's 82.00 Iris ACC cell.

V9.1 and earlier manuscript locks remain ordinary Git history only. They are superseded by the V9.3 lock on the current branch and should not be presented as current submission artifacts.
