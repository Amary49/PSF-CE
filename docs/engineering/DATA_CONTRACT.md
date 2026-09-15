# Frozen data contract

The source package contains no experimental datasets or base-partition archives. Provide one manifest CSV with columns `name,pool,path,group,split` and optional `source_id,task_family`.

Each `path` must reference an NPZ file with:

- `y`: shape `(n,)`, evaluator-only ground truth;
- `parts`: shape `(M,n)` or `(n,M)`, with `M=20` for the frozen protocol.

The formal split must contain exactly 53 distinct datasets and three pools per dataset (159 rows). Development dataset names and `source_id` values must be disjoint from the formal split. Heterogeneous cluster counts across the 20 base partitions are supported.

V4 does not regenerate, replace, filter, or label-select formal base partitions. Canonical relabeling changes identifiers only, not memberships.
