---
name: skill-evolution
description: "基于真实问题检查和改进本仓技能：写作体检、语义审查、方案取舍、回归与改进记录。"
---

# skill-evolution

用户要求检查或改进指定技能时使用；执行技能业务任务时仍走该技能。无自动进化、全局调用日志或定时评估。

运行约定见 [runtime-conventions](../_shared/runtime-conventions.md)，改进边界见 [evolution-discipline](../_shared/evolution-discipline.md)。

## 流程

1. 明确目标目录、真实问题、当前授权和可观察验收，取得基线。
2. 按 [authoring-checklist](references/authoring-checklist.md) 体检；关键语义变更安排真实独立 reviewer，输出问题、位置、证据和复验要求。格式错误让原角色重发一次，仍失败则待验。
3. 按 [gate-rules](references/gate-rules.md) 判断是否适合持续改进；不满足固定测试集条件的编排技能只做本次问题修复，不冒充效果进化。
4. 按 [evaluation-flow](references/evaluation-flow.md) 核根因、影响面和取舍；必要 PCF 遵守共享交接协议，不能按 Markdown 名称假装注册角色。
5. 在 [隔离工作区](references/worktree-sop.md) 实施与回归；真实效果比较需同口径基线及至少一个换面复测。没有数据只报告静态/工具结果。
6. 用 [模板](templates/EVOLUTION.template.md) 记录改进；重大决策转 decision-record；按 [cleanup-rules](references/cleanup-rules.md) 清理本批可重建产物。

定期反思仅在用户要求时按 [reflection-guide](references/reflection-guide.md) 执行，不注册后台任务。必要独立审查缺失时不签通过；主控自审须如实标明来源。
