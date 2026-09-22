# Experiment 1 — NMI Decomposition Diagnostic

## Material Passport

- Artifact type: frozen exploratory diagnostic analysis
- Cohort: revised Core-10, three frozen BP pools per dataset, `M=20`
- Statistical unit: dataset mean after averaging the three pools (`n=10`)
- Methods: six external baselines, PSF-CE, and three internal controls
- AggregatePower identity: historical formal `q_after=6.0` faithful replay
- AWEC: excluded before endpoint computation
- Run-config SHA-256: `7e6bbae6a6548db1ed768ecb9222e6199a37e636f6efdacf34e2b20c10bd16ab`
- Verification status: `ANALYZED_FROM_FROZEN_PREDICTIONS`

## 1. Input and provenance audit

The source audit passed for all 300 dataset–pool–method keys. Every prediction and true-label source was re-hashed against `INPUT_PROVENANCE.csv` immediately before calculation. Each of the ten methods contributes exactly 30 pool predictions. No prediction was repaired, substituted, regenerated for convenience, or selected using the mechanism endpoints.

AWEC was excluded before this mechanism analysis according to the documented parameter-fairness audit.

## 2. Metric consistency audit

- ACC records reproduced: 300/300; maximum absolute delta `5.551e-17`.
- Arithmetic NMI records reproduced: 300/300; maximum absolute delta `2.914e-15`.
- `H(Y)>0`, `H(Z)>0`, finite values, and matching sample counts: 300/300.
- Frozen consistency tolerance: `1.0e-10`.

ACC was used only as an integrity check. This experiment does not analyze why ACC is or is not high.

## 3. Information-identity audit

All 300 pool records passed the five prespecified identities at tolerance `1.0e-12`. The largest absolute residual was `2.220e-16`.

## 4. External decomposition

Under the pre-endpoint directional gate, favorable comparator profiles were observed for:

- NMI: 4/6 comparators (`>=4` required).
- Homogeneity: 5/6 comparators (`>=4` required).
- Completeness: 4/6 comparators (`>=4` required).

| Group | Comparator | ΔNMI mean | NMI W/T/L | Δh mean | h W/T/L | Δc mean | c W/T/L |
|---|---|---:|---:|---:|---:|---:|---:|
| External | MCLA | 0.0230 | 5/0/5 | 0.0119 | 5/0/5 | 0.0374 | 5/0/5 |
| External | HBGF | 0.0422 | 7/0/3 | 0.0217 | 7/0/3 | 0.0677 | 9/0/1 |
| External | CEHM | 0.0083 | 4/1/5 | 0.0119 | 5/1/4 | -0.0027 | 3/1/6 |
| External | YACHT | 0.0539 | 6/0/4 | 0.0359 | 6/0/4 | 0.0771 | 7/0/3 |
| External | RANGE | 0.0221 | 6/0/4 | 0.0037 | 6/0/4 | 0.0457 | 6/0/4 |
| External | GPEC | 0.0197 | 6/0/4 | 0.0087 | 6/0/4 | 0.0343 | 6/0/4 |

## 5. Internal attribution

| Group | Comparator | ΔNMI mean | NMI W/T/L | Δh mean | h W/T/L | Δc mean | c W/T/L |
|---|---|---:|---:|---:|---:|---:|---:|
| Internal | CA | -0.0090 | 3/4/3 | -0.0091 | 3/4/3 | -0.0083 | 3/4/3 |
| Internal | AggregatePower (q_after=6) | -0.0094 | 2/3/5 | -0.0095 | 2/3/5 | -0.0086 | 2/3/5 |
| Internal | q1-fixed | -0.0052 | 3/3/4 | -0.0052 | 4/3/3 | -0.0048 | 3/3/4 |

- Filter-before-fusion attribution: **INCONCLUSIVE**.
- Nonlinear `q!=1` attribution: **INCONCLUSIVE**.

These labels follow the frozen gate requiring a positive or negative directional profile plus Holm-adjusted `p<0.05` in homogeneity and/or completeness. Descriptive direction alone is reported but does not upgrade attribution.

## 6. Normalization diagnostic

`rho_H=H(Z)/H(Y)` is reported only as an explanatory diagnostic in `PART1_ENTROPY_NORMALIZATION_DIAGNOSTIC.csv`. No threshold for a “marked” entropy shift was preregistered, so no standalone significance or performance claim is made from `rho_H`.

## 7. Statistical results

Paired two-sided Wilcoxon signed-rank tests use the 10 dataset means. Holm correction is applied separately to six external comparisons and three internal comparisons for each of NMI, homogeneity, and completeness. Pools are never treated as independent statistical samples.

After Holm correction, 0/6 external NMI comparisons, 0/6 external homogeneity comparisons, and 0/6 external completeness comparisons reached `p<0.05`. The corresponding internal counts were 0/3, 0/3, and 0/3. Accordingly, the primary A/B/C/D label is a prespecified cross-comparator directional classification, not a claim that all or most individual comparisons are statistically significant.

## 8. Diagnostic interpretation

**Directional diagnostic: the revised-cohort NMI profile is accompanied by broadly favorable homogeneity and completeness directions.**

This is an exploratory association under the revised frozen Core-10 diagnostic. It is not a causal intervention, a confirmatory mechanism result, or evidence of universal superiority. No external comparison reached Holm-adjusted `p<0.05` for NMI, homogeneity, or completeness.

## 9. Explicit limitations

- The historical 53-dataset archive first became Candidate-52 after excluding the provenance-conflicted binary Isolet variant. The revised Core-10 was subsequently formed by removing USPS3568 and Handwritten for disclosed development-provenance overlap and admitting Iris and Mushroom from a separately frozen five-dataset replacement-candidate panel. It is not claimed to be a canonical benchmark or an independent holdout.
- The analysis is post-hoc and label-assisted even though its protocol and endpoints were frozen before calculation.
- There are only 10 statistical units, so paired tests have limited power.
- CA and AggregatePower labels are faithful-replay reconstructions verified against archived pool metrics; no original historical prediction hashes existed.
- AggregatePower uses the historical formal `q_after=6.0`, whereas PSF-CE uses `q=0.72`; this contrast does not isolate operation order under a matched exponent.
- `rho_H` has no preregistered inferential threshold.
- The findings cannot establish that the operator causes the observed information profile.

## 10. Exact statement safe for the paper

> On the revised frozen Core-10 cohort, the NMI-oriented profile of PSF-CE was accompanied by broadly favorable homogeneity and completeness directions across external comparators. This exploratory diagnostic does not establish a causal mechanism, and no individual external comparison was significant after Holm correction.

## 11. Statements not supported

- “PSF-CE proves or guarantees better information preservation.”
- “PSF-CE universally outperforms all clustering-ensemble methods.”
- “This experiment explains the ACC behavior.”
- “The `rho_H` diagnostic is a new performance ranking or independent significance endpoint.”
- “AWEC supports or contradicts a confirmatory mechanism result.”
- “The replay artifacts are the original historical prediction arrays.”

## Final verdict

**The revised-cohort NMI profile is directionally accompanied by both homogeneity and completeness; causal and confirmatory interpretations are not established.**

Filter-before-fusion attribution: **INCONCLUSIVE**
Nonlinear `q!=1` attribution: **INCONCLUSIVE**
