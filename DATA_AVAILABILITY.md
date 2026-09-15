# Data availability

No raw sample matrix, frozen BP matrix, sample label, prediction vector, or dataset archive is redistributed in this repository.

`configs/manifests/portable_manifest.csv` is a portability template derived from the actual execution manifest. It preserves dataset names, pool identifiers, groups, and split labels but points to a proposed local layout. It is not the historical execution file and does not itself grant redistribution rights to any underlying data.

The small files in `artifacts/paper_v1/` contain recorded aggregate metrics and provenance needed to rebuild the paper tables and figures. They do not contain the raw sample matrices or frozen BP arrays.

To rerun the algorithms, users must obtain the datasets from their original providers and prepare the corresponding frozen base-partition files according to their applicable terms. Dataset/source notes are provided for reproducibility, but online availability is not treated as blanket redistribution permission.

Some historical score rows do not contain BP hashes; hashes computed later cannot retroactively authenticate the exact historical inputs. The release keeps that limitation explicit rather than claiming byte-level historical identity that the archived records do not establish.

If derived BP files or per-sample predictions are distributed in a future release, their dataset-specific redistribution conditions must be reviewed separately before publication.
