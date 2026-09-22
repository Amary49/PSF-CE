# Cohort selection provenance

The cohort history has three distinct layers and must not be compressed into an undocumented claim that Core-10 was selected from one homogeneous 57-dataset pool.

1. The historical archive contained 53 tasks. The binary Isolet variant was excluded because its identity conflicted with the standard 26-class task and its exact provenance could not be closed. This produced `Candidate-52`.
2. A separately frozen replacement panel contained Ecoli, Dermatology, Iris, Heart, and Mushroom. Candidate order and the exact-cluster-count admission rule were fixed before performance endpoints were read. Iris and Mushroom passed; Heart remained provenance-unresolved.
3. The revised formal Core-10 removes USPS3568 and Handwritten from the old formal cohort because their source families overlap historical development tasks, retains the other eight formal tasks, and adds Iris and Mushroom.

Thus the defensible shorthand is **Candidate-52 plus a separately frozen five-dataset replacement panel, yielding the revised formal Core-10**. It is not an independent holdout, a canonical benchmark, or a claim that all 57 candidates underwent one identical historical screen.

See `data/cohorts/candidate52.txt`, `data/cohorts/replacement_candidates5.txt`, `docs/provenance/REPLACEMENT_CANDIDATE_SCREENING.csv`, and `configs/frozen/REVISED_CORE10_FORMAL_FREEZE.json`.
