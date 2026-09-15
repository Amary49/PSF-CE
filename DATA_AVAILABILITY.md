# Data availability

No raw sample matrix, frozen BP matrix, sample label, prediction vector, or dataset archive is included.

`configs/manifests/portable_manifest.csv` is a path template derived from the actual execution manifest. It preserves dataset names, pool identifiers, groups, and split labels but points to a proposed local layout. It is not evidence that the files are redistributable and is not the historical execution file.

The small files in `artifacts/paper_v1/` contain recorded aggregate metrics and provenance needed to rebuild paper tables. Whether BP files or per-sample predictions may be released depends on each source dataset's license, privacy conditions, and the provenance of derived partitions. Online availability alone does not grant redistribution rights.

Before public release, the authors must review dataset-by-dataset licenses and decide whether to provide download/preprocessing scripts, checksums only, or separately hosted derived BP files. Some historical score rows do not contain BP hashes; hashes computed later cannot retroactively authenticate the exact historical inputs.
