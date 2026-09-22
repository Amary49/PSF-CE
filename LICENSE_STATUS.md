# License status

**Public source release status: READY.**

The authors selected the MIT License for project-authored source code, adapters, scripts, configurations, documentation, and generated paper-support artifacts in this repository. The license text is in the root `LICENSE`.

This project license does not override separately identified material:

- The six Iris/Mushroom frozen-BP files are redistributed as UCI-derived data artifacts under CC BY 4.0 with attribution in `frozen_bp/NOTICE_CC_BY_4.0.md`.
- Third-party author repositories and binary dependencies are not vendored. Users obtain them separately under their upstream terms.
- The audited YACHT compatibility helper `psfce_v4_yacht_walk` is not present in the public tree. Public YACHT execution requires the user to supply the audited helper locally at `<YACHT_REPO>/psfce_local_overrides/psfce_v4_yacht_walk.m`. No authorship or redistribution right is inferred from filenames or code similarity.

Raw feature data, per-sample prediction archives, the other 24 frozen-BP pools, credentials, and private path maps are excluded. The repository can therefore be uploaded directly to a public GitHub repository with the documented reproduction boundaries intact.
