---
description: os·主入口：自动定档执行任务，可选验证修饰符
---

执行任务：$ARGUMENTS

修饰符：`+v` 完成后过 decision-verify 验证。

档位自动切换（不问你）：
- 单点任务/小改动 → 直接做
- 多步工程/跨文件 → 托管推进，只报关键节点
- 调研/探索/学习类 → 主控直接分析（结论全挂证据链）；spawn 档位硬规则：单点 spawn=0 主控直做，多步 1-3 只读臂并行+写侧串行主控
- 需求探索澄清 → 主控按 decision-explore 流程直接问，不 spawn
- 多角色共识/对抗 → 本仓未启用，主控自做正反两臂分析后裁决

通用：开工查 `decisions/postmortems/BACKLOG.md` 尾部+PENDING 同题防撞车；结论可溯源落盘数据；收尾只报新增/变更/异常/待决策，附文件指针。
沉淀：重大决策走 decision-record；失败复盘走 decision-improve；验证走 decision-verify。
