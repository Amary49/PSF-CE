# Third-party methods

The release contains our thin adapters and retrieval metadata, not complete author repositories or binaries. At the recorded retrieval date, the inspected repositories did not provide an explicit redistribution license; their status is therefore `NOASSERTION`.

| Method | Repository | Pinned commit | Public-result status | Redistribution |
|---|---|---|---|---|
| CEHM | https://github.com/FeijiangLi/Code-k-HyperEdge-Medoids-for-Clustering-Ensemble-AAAI | `29c22fb18e05eed67728eebcb29cd7e9133723f7` | 53 x 3 completed | Author source not included; license confirmation required |
| YACHT | https://github.com/scu-kdde/YACHT | `44cb0fc35b80ec17befa199879ac947fee15f464` | 53 x 3 completed | Author source/P-code not included; license confirmation required |
| RANGE | https://github.com/middle258/RANGE | `85d93c54d72d500034d05b5ef131bd90630a3632` | 53 x 3 completed | Author source/MEX/P-code not included; license confirmation required |
| AWEC | https://github.com/ltyong/awec | `47b96c9d1b5eb7549f7618b07947248cfbf2fa86` | Experimental adapter only; no paper-v1 formal result | Excluded from default fetch/run/report paths; author source not included |
| FSEC | https://github.com/zrx11/Anchor-Based-Fast-Spectral-Ensemble-Clustering | `b12107610b907eb3e5d441aa901e1a6959ed56a0` | Protocol-incompatible | Not a paper-v1 result; author source not included |

Running `python scripts/bootstrap_official_repos.py` uses `configs/official_repositories.json` and fetches only CEHM, YACHT, and RANGE. The broader `configs/examples/official_repositories_all_adapters.json` is an explicit inventory for audit or manual experimental work; it is not the paper-default configuration. Users remain responsible for license compliance. MATLAB, toolboxes, MEX, and P-code are not distributed here.
