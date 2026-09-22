# Paper evidence: revised Core-10

The archive contains the smallest public-safe result set needed to reconstruct the revised Core-10 main table and inspect the exploratory partition-structure analyses. It contains no raw feature data or per-sample prediction archives. Six separately licensed Iris/Mushroom frozen-BP files are stored at repository root under `frozen_bp/`; the other 24 pools remain hash-only.

Main scores are formal frozen outputs. Experiment 3, homogeneity diagnostics, and cluster-mixing geometry are exploratory structural analyses. They must not be described as causal proof. The `homogeneity_boundary` report is retained because it records why a stronger inter-class-mixing claim was rejected.

The `figures/figure1_parameter_sensitivity/` directory contains the revised-Core-10 post-freeze parameter diagnostic and its complete plotting evidence. The `tables/` directory contains both the main comparison and the exploratory partition-structure Table II. Table II is generated from the archived Experiment 3 and cluster-mixing geometry reports by `scripts/rebuild_table2.py`.
