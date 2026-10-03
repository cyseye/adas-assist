# io-protocol — 运行治理部 IO 组底层协议

> 职能部门化组织（ADR `decisions/adr/meta/organization-evolution-consolidated.md`）四部门之一。只收**机器可执行条款**（数值/schema/字段义务/触发条件）；叙述性原则留原处。数值单源=`_shared/io-budgets.json`（io-governance 唯一写者），本文件与各 hook 脚本只引用不复写。

## 1. 注入预算（全部引用 io-budgets.json）

> **平衡纪律（2026-09-13 暴力测试实证）**：常驻注入面已电报化（压缩天花板 ~6%，压 hook 关键词伤召回锚点）——token 优化的主战场在**取用侧**（跳数×单次读量）：新资产落位先补路由表行（防路由黑洞）、高频对象进速查头 1 跳直达、撤零引用死节对冲体积。「为凑指标压注入面」被证伪为伤召回，禁用。

| 面 | 上限 | 现有执行者 |
|---|---|---|
| knowledge-recall 注入 | io-budgets.recall_injection（max_items/summary_max_chars） | knowledge-recall.py |
| PENDING 积压注入 | io-budgets.pending_injection（max_lines/muted_after_reminds/digest_days） | session-start.py |
| 周评估报告注入 | io-budgets.weekly_report（max_lines/节流/analysis_max_lines） | weekly-eval.py + session-start.py |
| AskUserQuestion | io-budgets.ask_user（max_questions_per_batch/max_batches） | handoff-modes/socratic-inquiry（2026-09-26 勘误：原行宣称二者「引用」实为零命中，系宣称性指针失实，现仅为数值登记读口） |

铁律：动态注入**只尾部追加**不改前缀（cache-hygiene.md 本仓未包含，铁律以本行为正本承载；引用路径一律可直接 Read 的绝对路径）。

## 2. spawn prompt 装配

- 正文 ≤100 行（io-budgets.spawn_prompt）；超限一律写 `.build/` 传路径，协议文件按「路径传递、agent 自 Read」优先，全文内联为降级路径且须标注。
- 例外登记：小输入 ≤1 段话内联（pcf-execution-flow 未包含，主控自判）；私有 agent「全文作 prompt」沿用 runtime-conventions §4 但同样受 100 行限。

## 3. 回传与产物 schema

- subagent 回传统一（**schema 正文唯一单源=本节**；io-budgets.json `subagent_return` 键仅承载参数值 risks_max/inline_findings_max_lines/read_files_required）：`{status, file_path, read_files(实际读过的文件清单,审计/核验类必填), 关键计数, risks≤3}`（fixer 契约为基；read_files 系 2026-09-19 P2 增补，2026-09-27 自 io-budgets 回灌消分叉；finish-check inline 压缩索引 ≤15 行为登记特化）。
- 报告命名契约：`{skill}.round.{N}.*.json` / `report.{skill}.final.json`（review-gate-skeleton 未包含，§产物 schema 单源，consensus/dev-design 特化已登记）。
- 新增报告 schema 须在对应 skeleton 登记特化，禁 third format。

## 4. 工具输出纪律

- Bash stdout >100 行只留退出码/产物路径/关键计数/首错（条款升元层；项目 CLAUDE.md 改指针防双源，2026-09-15 落地）；文件 Read 不设限。
- hook 注入全部留痕 reflex-hooks.jsonl（召回/积压已做，新增注入面须同埋点），供周评估打扰度对账。

## 4a. 运行时节奏纪律（2026-09-15 自项目 CLAUDE.md 上收，跨项目通用）

- **长跑熔断**：子 agent 轮数预算 ≤40 轮（或单次输入 >100k，单源登记 io-budgets.subagent_context_fuse）到线即收口交付，主控摘要接力 spawn；仅适用无状态可摘要接力任务，审查/裁决类重上下文任务禁拆。
- **工具调用密度**：探活/轮询/状态查询合并批量执行（每条小命令触发一次全上下文安全分类=吞吐税）；长等待一律后台任务+完成通知，禁 sleep 轮询。
- **配额窗口**：战役/实验/进化轮（quota-tracker 本仓未包含）开工前评估当日配额余量，紧张时停新 spawn 只做收敛；cache_read 同样占配额，优化目标是总吞吐。

## 4b. 读取纪律（fail-closed，P0-1 配套条款）

- 消费 io-budgets 的脚本/能力：数值读取失败**禁代码侧兜底常量**——按 fail-closed 跳过受控行为（注入/截断/写入）并 stderr 留痕；行为开关类保守侧处理（如周评估视为到期）。
- 本条款是 `shared_state.io_budget` 及一切后续预算消费方的唯一降级语义定义处；改语义须本节与消费方同批。

## 5. 审计入口

io-governance：对照 io-budgets 审计注入/回传/命名合规（数值唯一写者与单源声明见本文件头部）。

## 归口登记

部门归属见 `~/.claude/AGENTOS-MAP.md §组织架构`；成员 agent：exec-json-fixer。
