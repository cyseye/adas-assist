---
name: effect-governance
description: "战略评估部统管五职能组（含进化统管）。触发词：效果回填/闭环检查/验证对账/效果审计/评估服务/周评估/证据链审计/对抗验证调度/进化统管/复盘统筹。"
---

# effect-governance · 效果评估与闭环

检查目标、基线、实测、证据与后续动作。主控串行执行；运行约定见 [runtime-conventions](../_shared/runtime-conventions.md)，判据见 [assessment-protocol](../_shared/assessment-protocol.md)。

## 输入与产物

输入：本次评估范围、目标值、同口径基线、实测记录及来源。复用项目任务计划记录：评估项、分母、结果、证据、负责人、下一步；缺数据记 `no_data`，不估算收益。

## 五项功能

| 功能 | 检查与处置 |
|---|---|
| 效果回填 | 逐项对账 expect/measured，列出未回填项与分母；有实测和可复算口径才回填，观察项注明到期条件 |
| 周评估 | 用户要求时消费已提供的周期报告，核召回、打扰、转化、输入输出和主模型会话占比；定义与参考线取共享协议及预算，不复制数值 |
| 证据链审计 | 核逐结论溯源、预测预注册、阳性对照、置信度、不利数据和无数据项；不合格则补证据或降为假设 |
| 对抗验证调度 | 按评估协议分流至共识、反方挑战或产物验证；必要独立执行上下文缺失时保留待验 |
| 进化与复盘统筹 | 核目标、实验、实测责任人、CAPA兑现率、跨项冲突及测量有效性；只提改进建议，实施走对应技能 |

## 执行步骤

1. 核范围与证据时效，复用已有评估，只补本次变化。
2. 按五项功能选择适用检查；指标保持相同样本、分母和口径。
3. 实测低于 expect×50% 或越参考线时，按 [效果验证协议](../_shared/evolution-discipline.md) 提出保留、观察或回退建议。
4. 失败标签按 [failure-taxonomy](../decision-improve/references/failure-taxonomy.md) 归类；CAPA输入来自 [decision-improve](../decision-improve/SKILL.md)。
5. 对争议结论核原始证据；推翻已有实测须给出反证路径。记录整改与定向复验，不用对账分代替真实效果。

## 工具与边界

- 预算单源：[io-budgets](../_shared/io-budgets.json)；证据纪律：[analysis-methodology](../_shared/analysis-methodology.md)。
- memory回放使用 [memory-governance](../memory-governance/SKILL.md) 的显式输入，与本次同口径基线比较。
- 只消费本次明确提供的日志、探针或基线；缺数据标 no_data，不补造事件。
- 产物验收归 [decision-verify](../decision-verify/SKILL.md) / [finish-check](../finish-check/SKILL.md)；共识归 [decision-consensus](../decision-consensus/SKILL.md)，反方挑战归 [devils-panel](../devils-panel/SKILL.md)。
- 周期检查由用户请求触发；回退、真实数据写入与后台操作按当前授权执行。评估不自动注册采集、调度或记忆接线。
