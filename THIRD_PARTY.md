# Third-party methods

This repository does **not** redistribute complete third-party author repositories, P-code, MEX binaries, or other upstream software. It contains only independently written interoperability adapters, pinned source metadata, and bootstrap instructions needed to obtain the upstream implementations separately.

The original PSF-CE repository is licensed under the MIT License. That license does not apply to software fetched from the upstream repositories below. Users are responsible for complying with the terms supplied by the respective upstream authors. When the audited upstream snapshot did not expose an explicit license, this release records `NOASSERTION` and makes no license claim on the author's behalf.

| Method | Repository | Pinned commit | Paper-v1 status | Release boundary |
|---|---|---|---|---|
| CEHM | https://github.com/FeijiangLi/Code-k-HyperEdge-Medoids-for-Clustering-Ensemble-AAAI | `29c22fb18e05eed67728eebcb29cd7e9133723f7` | 53 x 3 completed | Upstream source not included; fetched separately; upstream license `NOASSERTION` in the audited snapshot |
| YACHT | https://github.com/scu-kdde/YACHT | `44cb0fc35b80ec17befa199879ac947fee15f464` | 53 x 3 completed | Upstream source/P-code not included; fetched separately; upstream license `NOASSERTION` in the audited snapshot |
| RANGE | https://github.com/middle258/RANGE | `85d93c54d72d500034d05b5ef131bd90630a3632` | 53 x 3 completed | Upstream source/MEX/P-code not included; fetched separately; upstream license `NOASSERTION` in the audited snapshot |
| AWEC | https://github.com/ltyong/awec | `47b96c9d1b5eb7549f7618b07947248cfbf2fa86` | Experimental adapter only; no paper-v1 formal result | Excluded from all paper-default fetch/run/report paths; upstream source not included |
| FSEC | https://github.com/zrx11/Anchor-Based-Fast-Spectral-Ensemble-Clustering | `b12107610b907eb3e5d441aa901e1a6959ed56a0` | Protocol-incompatible with the frozen-BP paper benchmark | Not a paper-v1 result; upstream source not included |

`python scripts/bootstrap_official_repos.py` reads `configs/official_repositories.json` and fetches only the paper-default CEHM, YACHT, and RANGE repositories at their pinned commits. The broader files under `configs/examples/` are explicit audit/experimental inventories and are not default execution paths.
