# adas-assist v1.0 · Codex

先读 `README.md`、`doc/GOVERNANCE-PLAN.md` 与相关设计，当前开发分支为 `v1.0`。

- 根 `skills/`、`commands/`、`agents/` 与 `standards/` 是维护单源，不维护独立分发包；边界见 `doc/MIGRATION-BOUNDARY.md`。
- 开工看 Git 状态、指引与实现。只改本批文件，保留其他在途工作；未授权不提交、推送、发布或启动后台任务。
- 改 os 后运行 `python3 -B -m unittest discover -s skills/os/tests -v`；共享入口或规则变化另运行 `python3 -B -m unittest discover -s skills/_shared/tests -v`。
- 模型选择用宿主原生能力；仅按已验证的 Codex 配置使用模型、代理及工具；读取文档不会自动注册运行能力。
- task.py 的单 JSON 为任务状态源；证据与输入哈希不能证明陈述真实、业务正确或评审独立性。
- 真实宿主发现/调用与纯文件工具测试分开验收。仅支持 Codex，不修改用户既有配置。

## 本仓共用能力的 Codex 入口

`.agents/skills/` 中的原版技能和辅助目录通过相对软链接指向根 `skills/`，共用正文，不维护 Codex 副本。按本次任务选择技能，读取对应 `SKILL.md` 后沿其引用按需读规则、模板和脚本；不要整库注入。各技能直接复用根资产，不维护第二套正文。

| 场景 | 共用正文（支持宿主发现后可用同名 `$技能名`） |
|---|---|
| 需求探索 / 多角色共识 | [decision-explore](skills/decision-explore/SKILL.md)、[decision-consensus](skills/decision-consensus/SKILL.md) |
| 决策记录 / 复盘改进 | [decision-record](skills/decision-record/SKILL.md)、[decision-improve](skills/decision-improve/SKILL.md) |
| 资产存废 / 技能优化 | [decision-lifecycle](skills/decision-lifecycle/SKILL.md)、[skill-evolution](skills/skill-evolution/SKILL.md) |
| 产物验证 / 交付检查 / 反方挑战 | [decision-verify](skills/decision-verify/SKILL.md)、[finish-check](skills/finish-check/SKILL.md)、[devils-panel](skills/devils-panel/SKILL.md) |
| 效果 / I/O / 数据采集 / 记忆治理 | [effect-governance](skills/effect-governance/SKILL.md)、[io-governance](skills/io-governance/SKILL.md)、[info-collection](skills/info-collection/SKILL.md)、[memory-governance](skills/memory-governance/SKILL.md) |

### 共享规则、命令与角色

- 分析取证读 [analysis-methodology](skills/_shared/analysis-methodology.md)；运行目录与接力读 [runtime-conventions](skills/_shared/runtime-conventions.md)；委派与长输出读 [io-protocol](skills/_shared/io-protocol.md)，预算值查 [io-budgets](skills/_shared/io-budgets.json)；表达读 [report-protocol](skills/_shared/report-protocol.md)。
- 共用流程按需读 [socratic-inquiry](skills/_shared/socratic-inquiry.md)、[pcf-execution-flow](skills/_shared/pcf-execution-flow.md)、[review-gate-skeleton](skills/_shared/review-gate-skeleton.md)、[assessment-protocol](skills/_shared/assessment-protocol.md)。Codex 的手动执行、指标及双根路径约定以 [runtime-conventions §0](skills/_shared/runtime-conventions.md) 为准。
- 进化任务读 [evolution-discipline](skills/_shared/evolution-discipline.md)；安全与外发读 [security-protocol](standards/security-protocol.md)。命名、知识索引、生命周期和失败降级规则按需读 [standards/common](standards/common/)。具体技能的细则以其 `references/` 为准。本仓没有独立 `rules/` 目录，不另复制规则正文。
- 需要原版命令时，明确读取 [commands/os.md](commands/os.md) 或 [commands/evolve.md](commands/evolve.md) 执行本次请求，`$ARGUMENTS` 指用户本次参数；它们不会自动成为 Codex 的斜杠命令。`/os` 路由新版 os；`/evolve` 用于本仓手动维护。
- 需要角色时，读取 [review-rule](agents/review-rule.md)、[pcf-proposer](agents/pcf-proposer.md)、[pcf-critic](agents/pcf-critic.md)、[pcf-finalizer](agents/pcf-finalizer.md) 或 [exec-review-fixer-blue](skills/decision-verify/agents/exec-review-fixer-blue.md)，再按当前支持的代理工具和授权委派。Markdown 角色是职责正文，不是 Codex 原生角色注册。

### 本仓记忆与决策入口（含 os）

- `$os` 或本次 `/os` 请求涉及记忆时，先读 [memory/MEMORY.md](memory/MEMORY.md)，按主题打开它指向的正文，再按 [memory-governance](skills/memory-governance/SKILL.md) 执行。索引仅保留标题、相对路径和检索词；记忆正文唯一落在本仓 `memory/`，不复制进指引、任务摘要或宿主记忆。
- 宿主记忆如需保存本仓信息，只保留本仓路径及上述索引指向；具体写入仍遵守该宿主工具、权限及本次授权，不假定已自动保存或召回。不从宿主全局目录搬取正文。
- 决策先读 [decisions/KNOWLEDGE.md](decisions/KNOWLEDGE.md)，再打开索引指向的 ADR/复盘正文；沉淀走 [decision-record](skills/decision-record/SKILL.md)，实际落点按其归域规则。决策正文保留在 `decisions/` 等既有权威目录，memory 只引用、不复制正文。规则正文仍在共享协议、references、`standards/`，不迁入 memory。
- 本次获授权的记忆更新先改正文，再同步 `memory/MEMORY.md` 的指向、检索词及计数；决策更新同步 `decisions/KNOWLEDGE.md` 与协议要求的双向链。改名/合并先核引用；没有实际内容不建空条目或伪造 ADR。不把索引扫描无信号当作语义正确或自动召回证明。

### 路径与执行

- Markdown 链接相对当前文件；反引号中的 `skills/`、`agents/`、`standards/`、`decisions/`、`memory/` 及命令相对仓库根。执行命令前切到仓库根。
- 技能的 `references/`、`templates/`、`scripts/` 相对该技能目录。缺依赖按技能降级规则处理，不回退用户全局目录。
- 用户记忆、会话日志与配置使用显式授权的输入路径；本地工具不得默认访问宿主全局数据。必要独立评审缺失时保持待验。

### os

多步任务可用 [.agents/skills/os/SKILL.md](.agents/skills/os/SKILL.md)；入口未发现时读 [源码](skills/os/SKILL.md)。按模式读其 `references/`。`skills/os/` 是维护源，`.agents/skills/os` 使用相对软链接，不需要同步副本。新会话核验实际发现与命中路径；文件可读不等于原生调用已通过。

复杂任务继续用 `doc/GOVERNANCE-PLAN.md` 记录本批结果、未决与下一步，不另建长期治理体系。

首次进入项目或宿主/入口变化时用 `$os init` 检查，见 [初始化契约](skills/os/references/initialization.md)。按契约只读核 Git 状态、适用指引、链接和真实宿主命中路径，无独立初始化脚本。完善指引只增量补充，不覆盖用户规则，不注册或替代 Codex 原生 `/init`。

当宿主把 `/init` 或项目初始化请求交给 agent 时，沿上述初始化契约检查本仓维护源、技能/共享规则/角色路由、memory/决策索引与既有验证命令；需要生成指引时增量维护 AGENTS。若客户端直接处理原生命令，使用 `$os init` 取得本体系检查，不声称已覆盖该客户端实现。
