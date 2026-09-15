# Development set 设计原则

V1 的主要失败不是 formal oracle 没容量，而是全局冻结参数迁移不足。V2 因此要求 development set 满足：

- 与正式 53 数据集在 `name` 和 `source_id` 上完全不重叠；
- 尽量覆盖正式实验中的任务类型，而不是只用经典 UCI tabular；
- `task_family` 建议至少区分：classic/tabular、image、text/multiview、graph/relation、omics/single-cell、其他高维结构数据；
- 每个 family 至少 2 个 development datasets 更稳妥；
- development 的 BP 生成协议应和 formal 一致，但随机 pool 独立；
- freeze policy 在看 formal 结果前锁定。

`family_robust` 会先对每个 task family 内的数据集求平均，再让 family 等权进入选参分数；它的目标是降低 development family 数量不均造成的 transfer 偏置。

不要为了让最终 q 不等于 1 而排除 q=1。若更合理的 development 设计和尺度校准以后仍冻结到 q=1，应当接受这一结果并重新评估模型，而不是在代码里强制 nonlinear q。
