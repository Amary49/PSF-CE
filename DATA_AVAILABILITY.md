# Data availability

No raw feature matrix or per-sample prediction archive is distributed here. `data/dataset_manifest.csv` gives the ten task identities, source links, preprocessing/variant boundaries, local artifact hashes where available, and redistribution status. `data/bp_pool_hashes.csv` authenticates all 30 frozen BP inputs used in the revised formal run.

The selection provenance is represented separately: `data/cohorts/candidate52.txt` records the historical Candidate-52 names, while `data/cohorts/replacement_candidates5.txt` and `docs/provenance/REPLACEMENT_CANDIDATE_SCREENING.csv` record the separately frozen five-dataset replacement panel and its admission outcomes. These files are metadata, not redistributed datasets.

The six exact Iris and Mushroom pool files are included in `frozen_bp/` with attribution because both upstream UCI datasets are licensed CC BY 4.0. Each NPZ contains `y` and a 20-by-n `parts` array; no feature matrix is included. The other eight tasks have incomplete derived-artifact lineage or unresolved redistribution terms, so their 24 pools remain hash-only. `frozen_bp/REDISTRIBUTION_STATUS.csv` records the policy pool by pool.

The source release supports score-level reconstruction (Path A) and exact BP-level reruns for Iris/Mushroom where the required method dependencies are available. It does not support a public end-to-end ten-dataset rerun because the other 24 pools and prediction archives are not distributed. This is an explicit reproducibility boundary rather than a claim of full public reproduction.
