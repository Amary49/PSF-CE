# Official recent-baseline provenance

All repositories were resolved on 2026-09-14. Release 1.0.0 does not redistribute their source because none contains an explicit license file. Run `scripts/bootstrap_official_repos.py` to clone the three paper-default audited commits locally.

| Method | Paper | Venue | Repository | Commit | Release disposition |
|---|---|---|---|---|---|
| FSEC | Anchor-based Fast Spectral Ensemble Clustering | Information Fusion 113 (2025), 102587; DOI `10.1016/j.inffus.2024.102587` | `https://github.com/zrx11/Anchor-Based-Fast-Spectral-Ensemble-Clustering` | `b12107610b907eb3e5d441aa901e1a6959ed56a0` | `protocol_incompatible`; full method regenerates BPs from features |
| CEHM | k-HyperEdge Medoids for Clustering Ensemble | AAAI 2025; DOI `10.1609/aaai.v39i17.34010` | `https://github.com/FeijiangLi/Code-k-HyperEdge-Medoids-for-Clustering-Ensemble-AAAI` | `29c22fb18e05eed67728eebcb29cd7e9133723f7` | enabled through official `CEHM(clusters,k)` |
| YACHT | Dynamic Anchor-based Ensemble Clustering via Hypergraph Reconstruction | IJCAI 2025; DOI `10.24963/ijcai.2025/750` | `https://github.com/scu-kdde/YACHT` | `44cb0fc35b80ec17befa199879ac947fee15f464` | enabled; official repository contains two opaque P-code optimizer files |
| RANGE | Large-scale Robust Enhanced Ensemble Clustering via Outlier Decoupling | CVPR 2026 | `https://github.com/middle258/RANGE` | `85d93c54d72d500034d05b5ef131bd90630a3632` | enabled on 64-bit Windows MATLAB; official repository contains MEX/P-code |
| AWEC | Enhancing Ensemble Clustering with Adaptive High-Order Topological Weights | AAAI 2024; DOI `10.1609/aaai.v38i14.29552` | `https://github.com/ltyong/awec` | `47b96c9d1b5eb7549f7618b07947248cfbf2fa86` | experimental adapter inventory only; excluded from paper-default execution and results |

`vendor/official/PROVENANCE.json`, generated locally, records origin, actual commit, tree hash, detected license files, and the explicit non-redistribution decision.
