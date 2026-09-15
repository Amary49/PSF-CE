# Official MATLAB adapter contract

Python creates a temporary MAT file containing exactly:

- `base_parts`: `n x M`, one-based positive integer cluster labels;
- `c`: target number of consensus clusters;
- `seed`: fixed random seed;
- `params_json`: frozen method parameters;
- `input_meta_json`: BP and parameter hashes.

No ground-truth label field is written. Each adapter loads the author repository from the pinned `repo_root`, calls the audited author entry point, and writes `labels` plus `adapter_meta_json`. The Python evaluator sees `y` only after the adapter has returned.

The uniform Python result dictionary contains `labels`, `runtime`, `status`, `error`, `backend`, `repo_url`, `commit`, BP hash, parameter hash, cache state, and adapter metadata. There is no prediction-import or substitute-algorithm backend.

Method routes:

- CEHM: `CEHM(base_parts,c)`.
- YACHT: official hypergraph construction and `solve_YACHT`; the adapter parameterizes the paper's random-walk order because the released helper hard-codes 10 while the paper specifies 20.
- RANGE: official `Gbe -> HFES -> solve_RANGE` route and paper k-means decoder.
- AWEC (experimental, not paper-default): official `Gbe -> CA -> high-order connections -> solver_AWTP`, followed by the predeclared AWEC-H decoder.
- FSEC: no adapter by design; executing only its final `consensus_function` would not reproduce the full published method.
