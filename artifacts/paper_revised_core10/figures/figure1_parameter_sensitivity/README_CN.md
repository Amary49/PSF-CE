# Revised Core-10 Fig. 1 证据包

本目录保存 PSF-CE 在 revised Core-10 上的 post-freeze one-factor sensitivity diagnostic。该扫描只用于检查冻结工作点附近的响应形态，不用于重新选择参数。

## 冻结协议

- 左图：扫描 `q = {0.3, 0.72, 1, 6, 12}`，固定 `lambda = 0.665`。
- 右图：扫描 `lambda = {0.1, 0.5, 0.665, 1, 4, 12}`，固定 `q = 0.72`。
- 每个数据集使用相同的 3 个 frozen BP pools，每个 pool 含 20 个基划分。
- 其余设置保持冻结：seed 2027、K-means n_init 40、strong rounding、fro_centered calibration。
- 先在每个数据集内平均 3 个 pools，再对 10 个数据集等权平均。
- 横轴使用等间距 categorical positions；参数数值之间的几何距离不代表真实数值距离。

## 目录内容

- `data/fig1_source.csv`：论文作图使用的全精度 11 行汇总数据。
- `data/fig1_dataset_means.csv`：每个参数点的 10 个数据集级均值。
- `data/fig1_pool_level.csv`：每个参数点的 pool-level 指标及预测哈希，不含逐样本预测。
- `data/frozen_point_vs_formal.csv`：冻结点与正式主实验逐 pool 一致性核验。
- `scripts/build_figure1.py`：从 `fig1_source.csv` 重建 PDF/SVG/PNG。
- `figures/fig1_revised_core10_postfreeze_sensitivity.pdf`：论文使用的矢量图。
- `figures/fig1_revised_core10_postfreeze_sensitivity.tex`：Overleaf 插入代码和冻结图注。
- `audit/VALIDATION_REPORT.json`：覆盖、数值和 PDF 渲染验证。

## 重建命令

在安装 `numpy`、`pandas` 和 `matplotlib` 后，于本目录上一级执行：

```powershell
python scripts/build_figure1.py --root .
```

本包可以重建图，但不包含 frozen BP、逐样本预测缓存或完整算法运行环境。重新执行 300 个唯一的 pool-level 预测需要主 PSF-CE 工程与合法获得的数据/BP 文件。

## 结果边界

该图支持的表述是：在预先冻结的稀疏扫描网格上，ACC 与 NMI 对单因素变化的响应幅度有限，冻结点不是孤立尖峰。冻结点并非 revised Core-10 扫描中的最优点，因而不得将该图写成调参结果、最优性证明或机制证据。
