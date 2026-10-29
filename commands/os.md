# /os

涉及记忆/决策时先按 [AGENTS 本仓入口](../AGENTS.md) 路由：`memory/MEMORY.md` → memory 正文，`decisions/KNOWLEDGE.md` → ADR/复盘正文；分别使用 memory-governance / decision-record。宿主记忆只保留定位指针，不另存正文。

执行本次参数 `$ARGUMENTS`，使用 [os](../skills/os/SKILL.md)。Codex 可用 `$os`；本文件作为按需读取的命令说明。

本文件是命令正文；Codex 当前使用 `$os` 适配，目录中的 Markdown 不自动注册为斜杠命令或原生代理。角色读取与委派见 [项目指引](../AGENTS.md#共享规则命令与角色)。

模式、help、init 与修饰符用法统一见 [os 入口](../skills/os/SKILL.md)。示例：`$os plan +bk +vcn 制定本仓迁移计划`。

初始化见 [initialization](../skills/os/references/initialization.md)；规则见 [modes](../skills/os/references/modes.md)；执行与接力见 [execution](../skills/os/references/execution.md)。任务记录复用 [任务计划](../doc/GOVERNANCE-PLAN.md)。

维护 os 或关联 skill、agents、共享规则时，按 [质量清单](../skills/os/references/quality.md) 检查入口、角色交接、工具与宿主行为，结果写回既有任务记录。普通业务任务只核受影响链路；文件检查与真实宿主验收分别报告。
