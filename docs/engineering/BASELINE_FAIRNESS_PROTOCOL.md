# Baseline fairness protocol

1. One frozen ensemble instance = one `(dataset,pool)` NPZ. Every method receives exactly that instance.
2. Ground-truth `y` is used only in the common Python evaluator.
3. PSF-CE parameters come from the audited frozen study and were never changed after recent baselines were added.
4. Baseline parameters are either the released/default setting or development-only frozen settings.
5. No formal label may be used to select baseline parameters, iteration count, random seed, or rounding.
6. Dataset-level statistics first average the three pools, then compare methods across datasets. This prevents datasets with more pools from carrying more inferential weight.
7. Main paper reports ACC/NMI/ARI, mean rank, W/T/L and Holm-adjusted paired tests. Oracle capacity remains a mechanism diagnostic and is not mixed into the SOTA table.
8. Failed runs remain failed; there is no imputation by another algorithm.
9. If a method's official algorithm requires original features or regenerates the ensemble, it cannot be silently reported as a frozen-BP decision-only baseline. Mark it `protocol_incompatible` and omit it from rankings and significance tests.
10. Only pinned author repositories may execute. Private implementations, imported predictions, placeholder algorithms, and fallback substitutions are forbidden.
11. A cached output is reusable only when repository commit, BP content hash, target cluster count, parameters, and seed all match.
12. A method enters the final report only after all 159 formal dataset/pool rows succeed and pass `scripts/audit_formal_protocol.py`.
