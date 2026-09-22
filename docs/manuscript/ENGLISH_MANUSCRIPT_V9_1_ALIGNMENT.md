# English manuscript V9.1 alignment

This public repository is aligned with `PSFCE-MANUSCRIPT-ENGLISH-REVISED-CORE10-V9.1-FINALFORMAT-20260922`. The manuscript archive itself is not redistributed here; its identity and SHA-256 are recorded in `ENGLISH_MANUSCRIPT_V9_1_LOCK.json`.

## Version separation

- Scientific evidence: `PSFCE-MANUSCRIPT-REVISED-CORE10-V5-20260922`.
- Active English manuscript: `PSFCE-MANUSCRIPT-ENGLISH-REVISED-CORE10-V9.1-FINALFORMAT-20260922`.
- Public repository: `PSFCE-GITHUB-REVISED-CORE10-V9-PUBLIC-20260922`.

Repository V9 does not change an algorithm, frozen parameter, prediction, score, cohort member, figure value, or table value. It aligns the public-facing documentation and claim contract with the final-format English manuscript.

## Claim alignment

The active paper and repository support the following bounded statements:

- PSF-CE has the highest descriptive mean NMI and third-highest descriptive mean ACC on revised Core-10.
- No paired NMI comparison remains significant after Holm correction.
- The exploratory partition diagnostics show favorable MI and AMI directions for 5/6 and 4/6 comparators, respectively.
- The structural diagnostics describe associations in returned partitions and do not identify a unique upstream causal component.

The phrase “positive NMI differences are MI-dominant overall” is not part of the active claim set. The archived evidence supports directional comparator counts, not that stronger decomposition claim.

## Artifact alignment

- Table I: `artifacts/paper_revised_core10/tables/revised_main_table.tex` and the full-precision score CSV files.
- Figure 1: `artifacts/paper_revised_core10/figures/figure1_parameter_sensitivity/`.
- Table II: `artifacts/paper_revised_core10/tables/table2_partition_structure.tex` and its source CSV.
- Citation and execution provenance: `docs/provenance/` and `docs/fairness/`.

The repository bibliography is a provenance bibliography for baselines and datasets; it is not a copy of the manuscript bibliography. Manuscript V9.1 uses 21 citation keys, while this repository retains the broader provenance records needed to audit code and data identities.
