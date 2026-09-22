# Known limitations

- Revised Core-10 is a post-freeze revised formal cohort, not a clean independent holdout.
- Exact processed lineage is incomplete for BBCSport, the two leukemia tasks, Caltech101-20, and ACM-3025.
- The replacement panel contains five separately frozen candidates. Heart has an official UCI source but its reported processed task identity remains unresolved; only Iris and Mushroom were admitted.
- MCLA/Chameleon returns k=4 rather than c=5 in two pools; native outputs are retained without repair.
- No NMI comparison reaches Holm-corrected significance.
- Fragmentation and mixing-geometry analyses are exploratory and do not establish causal mediation or an upstream mechanism.
- Common-8 prediction drift affected historical-vs-revised attribution for MCLA and HBGF; no replacement-effect claim is made.
- Figure 1 is a post-freeze one-factor diagnostic recomputed on revised Core-10; it was not used for parameter reselection.
- MATLAB execution was not rerun during packaging; AWEC is outside the seven-method formal comparison.
- Public Path B is not end-to-end for all ten datasets: only the six Iris/Mushroom pools are redistributed; the other 24 remain hash-only and no byte-identical public generator is claimed.
- The public YACHT adapter excludes the audited private compatibility helper and therefore cannot run until the user supplies that helper and the upstream solver locally.
- Public source release is licensed and notice-complete for the material actually distributed here; this does not make Path B end-to-end for all ten datasets or grant rights to omitted upstream repositories/data.
