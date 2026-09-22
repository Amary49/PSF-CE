# 发布检查清单

## 当前状态

`READY_FOR_PUBLIC_GITHUB_UPLOAD`。V9 已补齐项目许可证、许可范围说明、第三方依赖说明，并与英文稿 V9.1 的最新证据口径对齐；既有算法、预测、分数、参数、图表和正式数据集均未改变。

## 可以直接公开上传

- 本目录中的项目源码、适配器、冻结配置、文档、引用表、公开安全的聚合分数、探索性分析摘要、revised Core-10 图一证据目录和表二源码/审计。
- `frozen_bp/` 中 Iris/Mushroom 六个精确 BP 文件；它们按上游 UCI CC BY 4.0 条款单独署名发布。
- 根目录 `LICENSE` 只覆盖项目原创材料；数据例外见 `NOTICE.md` 与 `frozen_bp/NOTICE_CC_BY_4.0.md`。
- 上传时让本目录内容直接成为 GitHub 仓库根目录，不要再套一层同名目录。

## 不要加入公开仓库

- 私有审计目录、绝对路径映射、原始特征数据、其余 24 个 BP、逐样本预测。
- YACHT 私有兼容 helper、第三方完整仓库、未核权的 MATLAB P-code/MEX/二进制、MATLAB 许可证信息、凭据。

## 后续新增内容时必须重新核对

- 新增任何数据、BP、第三方源码或二进制时，重新核对其许可和再分发条款。
- 若以后希望公开 YACHT 端到端运行能力，需另行确认 `psfce_v4_yacht_walk` 的代码来源与可再分发性；V9 不包含该 helper。
- Path B 目前只对 Iris/Mushroom 的 BP 输入闭合；其余八个任务仍不可公开端到端复现。这个边界不影响源码和 Path A 证据公开。
- 最终论文题目、DOI 和 GitHub URL 尚未确定，因此 `CITATION.cff` 不虚构这些字段。

## 发布前最后一条命令

运行 `python scripts/validate_release.py`，并确认 `python -m pytest -q` 通过。V9 的归档 ZIP 必须按上述规则重新生成 manifest 和 SHA-256；不得把私有审计、旧版 ZIP 或本机路径映射一并上传。
