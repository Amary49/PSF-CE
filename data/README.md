# Portable data entry

This directory contains metadata and placement examples, not redistributed research data.

1. Read `dataset_manifest.csv` and `sources.csv`.
2. Obtain each dataset under its own license and reproduce the documented local variant.
3. Place frozen BP pools under a user-selected directory and verify them against `bp_pool_hashes.csv`.
4. Copy `local_paths.example.yaml` to an ignored `local_paths.local.yaml` and edit only that local file.

The supplied hashes authenticate the inputs used by the archived run. They do not retroactively prove upstream lineage where the manifest says that lineage is incomplete.
