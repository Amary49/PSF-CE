# PSF-CE 发布检查清单

## 可以先上传到私有 GitHub 仓库

- 本目录的源码、测试、冻结配置、文档和小型 `artifacts/paper_v1/`。
- `figures/` 中的真实汇总数据、绘图源码和矢量 PDF。
- 我们编写的薄 adapter、固定 commit 获取脚本和第三方依赖说明。

## 不可以上传

- `release_private_audit/`。
- 原始数据、完整 BP、逐样本标签、预测缓存和 MATLAB 临时文件。
- `.venv`、cache、runtime results、下载的第三方完整仓库及 MEX/P-code 二进制。
- 历史方法材料、协议不兼容方法材料、未完成实验结果和 oracle 逐池大文件。
- 含本机绝对路径、用户名、凭据或投稿编号的原始日志。

## 仍需作者确认

- PSF-CE 项目许可证和贡献者授权。
- 作者顺序、单位、论文题目、DOI/录用状态和最终引用格式。
- 数据、BP、预测和图表的逐项再分发权。
- 第三方仓库无明确许可证时 adapter/补丁的公开边界。

## 当前状态

- 私有仓库准备：**READY_FOR_PRIVATE_REPOSITORY**。
- 公开发布准备：**NOT_READY_FOR_PUBLIC_RELEASE**。
- 未自动创建远端、未 push、未上传数据。
