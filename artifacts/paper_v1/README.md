# Paper-v1 artifacts

This directory contains small, reviewed files needed to reproduce paper numbers without redistributing datasets or predictions.

- `scores/`: separate frozen main, recent-baseline, and fixed-strength-ablation pool-level scores.
- `summaries/`: dataset means and equal-weight 53-dataset summaries.
- `statistics/`: paired ACC tests and ranks; dataset is the unit of analysis.
- `provenance/`: frozen parameters and protocol audits.

The main eight-method record is the union of five frozen internal methods and three completed recent baselines. Historical-method rows are intentionally absent. Oracle capacity is not merged into frozen results. The parameter figure uses only its archived aggregated grid, not oracle maxima as main scores.

Files in `statistics/` are the preserved historical outputs. Running the release reconstruction creates separately named `*_recomputed_current_env.csv` files; it never overwrites this directory.
