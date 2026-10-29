---
name: os
description: "任务协作 OS：需要多步任务托管、头脑风暴、任务规划、证据审查或跨会话恢复时使用。"
---

# os

在用户授权范围内完成任务，保留核心编排、验证与接力。简单任务直接执行，复杂任务才增加记录与评审。

## 调用与快捷说明

Codex：`$os [模式] [修饰符...] 任务目标`。省略模式时，单点任务用 direct，其余用 managed。

- `direct` 直接执行；`managed` 多步托管；`brainstorm` 方案比较；`plan` 任务规划。
- `review` 只读审查；`recover` 恢复接续。
- 修饰符：`+b` 头脑风暴前置、`+k` OKR/KPI拆解、`+l` 长任务分批、`+v` 验证、`+c` 交付检查、`+n` 目标对账；支持 `+bk`、`+vcn`，规则见 [modifiers](references/modifiers.md)。
- `$os init`：只检查项目与宿主适配，读取 [initialization](references/initialization.md)；显式要求生成/完善指引时才增量维护。
- `$os help`：只输出以上用法、六模式、init、六个修饰符及组合示例，不开始任务；`$os 帮助` 同义。

示例：`$os managed +bk +vcn 制定并推进当前项目目标`；`$os plan +k 只制定迁移计划`。
这些是交给 agent 解释的调用约定，不是参数解析器或输入框逐参数补全。
未知模式或选项先显示帮助，不将它们当作任务目标自动执行。

## 路由与按需读取

- 输入：任务目标，模式可选，已知约束与验收。默认单点 direct，其余 managed。
- 先读 [modes](references/modes.md) 选择任务模式；只有当前模式需要时读对应部分。
- managed / plan / recover 读 [execution](references/execution.md)；复杂任务复用现有记录；需要状态/证据校验时按 execution 使用 [task.py](scripts/task.py)，无 CLI 时可用 [TASK 模板](templates/TASK.md)。
- 调用前缀包含修饰符时先读 [modifiers](references/modifiers.md)，只执行所选项；`help/init/plan/review` 的完成边界优先。
- 涉及模型分工、并行或上下文预算时读 [resources](references/resources.md)。
- 用户要求周期检查时读 [periodic](references/periodic.md)。
- 维护 os、命令入口、关联 skill/agent 或共享规则时读 [quality](references/quality.md)，按变更范围检查契约与行为。

## 执行约定

1. 读取当前项目指引和 Git 状态，保留在途改动；首次进入项目或宿主/入口变化时按 [initialization](references/initialization.md) 检查必要前提，后续仅核变化。确认目标、范围和可观察的完成条件。
2. 按任务模式推进。多步任务先写必要计划；普通可逆工作在授权内持续完成，不逐步索要确认。
3. 先使用项目现有 skill、工具与检查。可委派且获授权时才分配有输入、写域、验收和回传约束的子任务。
4. 以实际产物和与改动相称的检查验证验收项；失败时定向定位、修复、复验，避免重复全量扫描。
5. 输出完成内容、证据与实质限制。跨会话保存目标、约束、状态、关键决策、未决与下一步。

涉及生产写入、破坏性迁移、发布等难撤销动作，执行前读取 execution，核对授权、验证/回退与必要独立复核；条件不齐先完成可审阅产物，停在动作执行前。此规则适用于所有模式。

阻断项不得用“完成”掩盖；工具不支持、多代理不可用、检查没运行须如实说明。仅同会话自审不能签署必要的独立复核。

规则是给 agent 的执行指导；本仓没有 runtime hooks 或工具调用拦截。可选 task.py 校验任务转换、声明验收与文件哈希，不执行检查、不证明陈述真实性或评审独立性，也不是原 agentos flow 引擎。

不运行自进化、长期知识沉淀、外部检索或账号轮转。任务级根因定位和交付证据仍属于任务闭环。

评估入口：skills/os/tests 覆盖任务状态与边界，共享 tests 覆盖仓库契约；行为用例见 [modes](references/modes.md) 的验收场景，需宿主真实运行后才能确认。
