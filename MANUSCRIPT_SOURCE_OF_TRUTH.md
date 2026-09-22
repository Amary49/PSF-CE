# Manuscript Source of Truth V5 (public repository release V8)

This directory is the only active source for writing the PSF-CE manuscript after 2026-09-22.

## Active formal scope

- Cohort: revised Core-10 = BBC News Sport, Leukemia, Caltech101-20, Leukemia2, Chameleon, Amazon Photo, ORL, ACM, Iris, Mushroom.
- Methods: MCLA, HBGF, CEHM, YACHT, RANGE, GPEC, and PSF-CE.
- Three frozen base-partition pools per dataset, with M=20 partitions per pool.
- PSF-CE: q=0.72, lambda=0.665, seed=2027, strong rounding, 40 K-means initializations, Frobenius-centered calibration.
- Aggregation: average the three pools within each dataset, then give the ten datasets equal weight.

## What the evidence supports

PSF-CE has the highest descriptive mean NMI and the third-highest descriptive mean ACC in the revised Core-10 table. None of its six NMI comparisons is significant after Holm correction. Exploratory analyses associate the NMI-oriented profile with (i) reduced true-class fragmentation, (ii) macro-level cluster purification with localized residual mixing, and (iii) favorable MI/AMI directions whose positive-NMI decomposition is MI-dominant overall. These are partition-level structural associations, not causal mediation or proof of an upstream component.

Safe manuscript sentence:

> The NMI-oriented performance profile of PSF-CE is associated with two complementary patterns of partition geometry: reduced true-class fragmentation and macro-level cluster purification with localized residual mixing.

## Active paper artifacts

- Figure 1 is the revised Core-10 post-freeze one-factor sensitivity diagnostic under `artifacts/paper_revised_core10/figures/figure1_parameter_sensitivity/`. Across the prespecified grids, ACC varies by 0.60 percentage points in the q sweep and 0.76 percentage points in the lambda sweep; the corresponding NMI ranges are 0.81 and 1.69 percentage points. The sweep is not parameter selection and the frozen point is not labeled optimal.
- Table II is `artifacts/paper_revised_core10/tables/table2_partition_structure.tex`. It is explicitly exploratory. Its counts are comparator-level directional profiles, not counts of significant tests, and all six displayed counts are unchanged in the no-Chameleon Core-9 sensitivity analysis.

## Required limitations

- Revised Core-10 must not be called an independent holdout. It is a post-freeze revised formal cohort with disclosed development provenance.
- Only the six exact Iris/Mushroom frozen-BP files are public under CC BY 4.0. The remaining 24 formal pools are authenticated by hash but not redistributed.
- The public YACHT adapter requires a separately supplied audited compatibility helper; the helper is not included in V8.
- Chameleon/MCLA pool 0 and pool 2 return four clusters for a five-class task. These native outputs remain in all reported scores.
- Exact-c was used only for performance-blind replacement-candidate admission with MCLA and CEHM; it is not a promise that every final method returns c clusters.
- The cluster-geometry evidence is exploratory and does not establish causality.
- Any parameter-sensitivity figure based on the old cohort remains superseded; only the revised-Core-10 Figure 1 in the active artifact directory may be used.

## Superseded material

Core-11/Isolet, the old Core-10 with USPS3568 and Handwritten, and the early `SCIENTIFIC_UPDATE_NOT_ACCEPTED` decision are retained only as historical audit records outside this active handoff.
