# /evolve

按本次参数 `$ARGUMENTS` 检查和改进本仓资产。流程见 [skill-evolution](../skills/skill-evolution/SKILL.md)，执行约定见 [runtime-conventions](../skills/_shared/runtime-conventions.md)。

| 参数 | 功能 |
|---|---|
| 空 / `自审` | 检查技能健康与现有改进信号 |
| `help` / `帮助` | 显示参数与示例，不执行检查 |
| `状态` | 只读汇总已有日志、待办与评估结果 |
| `正向` | 查找缺失能力与断链 |
| `逆向` | 核对矛盾规则与近期回归 |
| `减负` | 查找重复内容和无引用资产 |
| `联审` | 使用 [effect-governance](../skills/effect-governance/SKILL.md) 与 [io-governance](../skills/io-governance/SKILL.md) 对账 |
| `决策` | 汇总待决项，转 [decision-consensus](../skills/decision-consensus/SKILL.md)；记录用 [decision-record](../skills/decision-record/SKILL.md) |
| `画像` | 仅分析用户明确提供的输入样本 |
| `all` | 顺序执行正向、逆向、减负并去重 |

示例：`/evolve 状态`；`/evolve 逆向`。未知参数显示帮助。检查以仓库根为工作目录；复用 [任务计划](../doc/GOVERNANCE-PLAN.md) 记录问题与复验结果。可选日志或工具缺失时记 `no_data` / 未运行；不能据此判定健康或零积压。

改动先取基线，后运行对应检查。删除、发布、标签、后台及多代理按当前任务授权与宿主能力执行。真实用户记忆和配置不作为默认检查对象。
