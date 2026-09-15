# PSF-CE 公开发布检查清单

## 当前状态

- 私有仓库准备：**READY_FOR_PRIVATE_REPOSITORY**。
- 公开发布准备：**READY_FOR_PUBLIC_RELEASE**。
- 项目许可证：**MIT License**（仅覆盖本仓库原创 PSF-CE 内容与独立编写的适配层）。
- 第三方完整作者仓库：**未随本仓库再分发**。
- 原始数据、完整 BP、逐样本预测：**未随本仓库再分发**。

## 可以上传到公开 GitHub 仓库

- 本目录的源码、测试、冻结配置、文档和小型 `artifacts/paper_v1/`。
- `figures/` 中的真实汇总数据、绘图源码和矢量 PDF。
- 我们独立编写的薄 adapter、固定 commit 获取脚本和第三方来源说明。
- `LICENSE`、`THIRD_PARTY.md`、`DATA_AVAILABILITY.md`、`REPRODUCIBILITY.md` 与 `VALIDATION_REPORT.json`。

## 不上传

- `release_private_audit/`。
- 原始数据、完整 BP、逐样本标签、预测缓存和 MATLAB 临时文件。
- `.venv`、cache、runtime results、下载的第三方完整仓库及 MEX/P-code 二进制。
- 含本机绝对路径、用户名、凭据或投稿编号的原始日志。

## 发布边界

- CEHM、YACHT、RANGE 为论文中已完成的近期基线；完整上游源码由用户按 `THIRD_PARTY.md` 自行获取。
- AWEC 仅作为实验适配器库存保留，默认运行、抓取、审计和报告均不包含 AWEC，也没有 paper-v1 正式结果。
- FSEC 因 fixed-BP 协议不兼容，不属于 paper-v1 正式结果。
- `NOASSERTION` 仅表示本发布不替上游作者声明许可证；上游代码并未被 vendoring 到本仓库。
- 当前验证报告是发布包、冻结配置、记录分数与表图重建的验证，不等于重新执行 53 x 3 算法。

## 上传前最后核对

1. GitHub Desktop 中确认没有 `release_private_audit/`、数据/BP、缓存、第三方下载目录。
2. README 首页显示正常。
3. `LICENSE`、`THIRD_PARTY.md`、`DATA_AVAILABILITY.md` 可直接打开。
4. Release tag 使用 `v1.0.0`。
5. 结果附件与源码仓库分开发布。
