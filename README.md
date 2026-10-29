# adas-assist · v1.0

面向 Codex 的任务协作资产：直接维护根目录技能、命令、角色和共享规则，不维护独立分发包。

| 入口 | 用途 |
|---|---|
| [os](skills/os/SKILL.md) | 六模式、init/help 与 +b/+k/+l/+v/+c/+n 修饰符 |
| [Codex 指引](AGENTS.md) | 技能、命令、角色、记忆及决策路由 |
| [任务工具](skills/os/references/execution.md) | 可选单任务状态与证据校验 |
| [初始化](skills/os/references/initialization.md) | 只读项目检查与增量完善指引 |
| [架构设计](doc/SYSTEM-DESIGN.md) | 资产、状态与宿主边界 |
| [治理记录](doc/GOVERNANCE-PLAN.md) | 验证结果、未决与下一步 |

`.agents/skills/` 通过相对软链接指向根 `skills/`，所有技能只改根维护源。Codex 发现后使用 `$os`；`commands/` 是可读取的流程入口，`agents/` 是角色职责正文，均不因存在文件而自动注册原生命令或代理。

在仓库根运行与本次改动相关的检查：

```sh
python3 -B -m unittest discover -s skills/os/tests -v
python3 -B -m unittest discover -s skills/_shared/tests -v
python3 -B -m unittest discover -s skills/memory-governance/tests -v
python3 -B -m unittest discover -s skills/scripts/tests -v
```

测试覆盖任务文件行为、共享契约与路径边界，不能替代新会话中的技能发现和模型行为验收。无需运行安装器、更新副本或配置后台任务；不修改用户全局配置。初始化用 `$os init`，不覆盖宿主原生 `/init`。
