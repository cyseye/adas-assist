# 进化门控规则

> **原则**：进化要克制，默认不动；不合适宁可不做。稳定优先于完美。

## §1 接入条件（满足才接入，不强制所有 skill）

- 已积累 **≥2 轮真实问题**（产物审计 / 用户反馈 / 调用日志信号）
- 具备可观察效果信号（全局调用日志趋势 / 周评估指标 / 用户反馈，评估引擎退役后的现行判据）
- **有固定可重复的测试集**：同一输入集可重复执行、产物可对比、存在客观正误标准——「执行对象每次不同」的 skill（如 dev-implement、dev-plan）不满足此条件，不适合接入当前版本

> **不适合的情形**：每次执行对象不同（不同任务/模块）、产物为自然语言且无客观评分维度（如 spec-generator）。这类 skill 更适合「人工判断 + memory 记录反馈」。

### 接入方式

- `EVOLUTION.md`：按 `{skill_dir}/templates/EVOLUTION.template.md` 记录本 skill 进化历史
- 历史注：评估引擎已退役，见 `evaluation-flow.md` §头；接入现状仅剩 EVOLUTION.md 留痕 + 人工判断

## §2-§4 通用门控（触发 / 不动清单 / 风险评级 / 量化门槛）

> 已上提为公共 canonical：[`_shared/evolution-discipline.md`](../../_shared/evolution-discipline.md)（触发条件 / 「不动」清单 / 风险评级 / 量化门槛）。本文件只保留 skill-evolution 特有的 §1 接入条件。
