# Baseline fairness audit

All seven methods consume the same frozen n-by-20 BP pool for each dataset/pool cell. Parameters and implementation identities are fixed globally; revised Core-10 labels are not used for method-specific tuning or retries. Scores are aggregated by pool-within-dataset first and dataset-equal weighting second.

The comparison is reproducible but not perfectly symmetric: MCLA/HBGF are modern controlled reimplementations; CEHM/YACHT/RANGE/GPEC use author source through adapters; YACHT has a compatibility patch; RANGE uses a historically selected global setting; GPEC uses a frozen-pool wrapper and a hash-locked source snapshot without a verified commit. These differences are disclosed rather than hidden. Native failures and returned-k deviations are retained.
