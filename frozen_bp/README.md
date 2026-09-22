# Frozen base-partition release boundary

This directory publishes only the six frozen formal-pool files for UCI Iris and UCI Mushroom. Their official UCI records identify the datasets as CC BY 4.0, which permits sharing and adaptation with attribution:

- Iris: https://archive.ics.uci.edu/dataset/53/iris, DOI `10.24432/C56C76`.
- Mushroom: https://archive.ics.uci.edu/dataset/73/mushroom, DOI `10.24432/C5959T`.

Each NPZ is byte-identical to the corresponding formal input authenticated in `data/bp_pool_hashes.csv`. It contains two integer arrays: `parts` with shape `M x n` and `y` with shape `n`. It contains no feature matrix. The files are provided for research reproducibility under the attribution terms summarized in `NOTICE_CC_BY_4_0.md`.

The other 24 revised-Core-10 pools are not redistributed. Their identities remain locked by dataset name, pool ID, shape, and SHA-256 in `data/bp_pool_hashes.csv` and `REDISTRIBUTION_STATUS.csv`. `HASH_ONLY` does not imply that the upstream data are unavailable; it means that this project has not established a complete redistribution chain for the exact local benchmark variant and frozen artifact.

Do not infer that the root MIT software license applies to these data-derived files. Their CC BY 4.0 terms are documented in `NOTICE_CC_BY_4.0.md`; project source licensing is summarized in `LICENSE_STATUS.md`.
