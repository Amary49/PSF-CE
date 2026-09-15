# Experiment governance

1. **Development broad/strong search** may use labels to select global hyperparameters. It must be disjoint from the 53 formal datasets by both `name` and `source_id`.
2. **Freeze** happens once from `dev_strong.csv`; the resulting JSON stores the development CSV SHA-256.
3. **Frozen formal main** uses only the sealed parameter file and strong spectral solver.
4. **Formal oracle** is diagnostic only. Its strong stage contains the frozen setting and uses the same strong spectral solver, so transfer-gap comparisons are solver matched.
5. **Relocation** is not part of the frozen main method. It is run only as an optional solver ablation / convergence experiment.
6. Oracle-capacity staircase is allowed because the parameter domains are nested; frozen results are never forced to be monotone.
