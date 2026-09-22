# Release and license notice

This repository is prepared for direct public source release.

- Project-authored source code, adapters, scripts, configurations, documentation, and generated paper-support artifacts are released under the MIT License in the root `LICENSE`, unless a file or directory states otherwise.
- The six frozen base-partition artifacts under `frozen_bp/iris/` and `frozen_bp/mushroom/` are data-derived artifacts redistributed under the upstream UCI Creative Commons Attribution 4.0 International terms. See `frozen_bp/NOTICE_CC_BY_4.0.md`. The root MIT License does not relicense those files.
- Third-party author repositories, MATLAB binaries/P-code/MEX components, raw feature data, the other 24 frozen base-partition pools, prediction archives, and the audited YACHT compatibility helper are not redistributed here.
- Python dependencies are installed separately and retain their upstream licenses. See `THIRD_PARTY.md`.

The public reproducibility boundary is intentional: score-level paper reconstruction is public for the full revised Core-10 cohort, while exact frozen-BP reruns are publicly closed only for Iris and Mushroom.
