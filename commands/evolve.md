---
description: agentos 自主进化快捷入口——多方向进化轮（正向/逆向/减负/联审/外参/决策/自审/画像/状态/all）
argument-hint: "[方向: 正向|逆向|减负|联审|外参|决策|自审|画像|状态|all] (缺省=按信号分档轻量轮)"
---

# /evolve — agentos 自主进化快捷入口

参数：$ARGUMENTS

你是 agentos 体系的中控（Boss=主模型调度）。按下面路由执行进化轮，全程遵守 `skills/_shared/evolution-discipline.md`（进化周期三档+信号消化分级）与 `io-budgets` 预算。本指令缺省路径是轻量档（本仓无战役机制，全力档=多 Explore 并行）。

## 路由表（按参数分发，可组合）

| 参数 | 动作 | 档位 |
|------|------|------|
| （空）| **信号分档轻量轮**：读 `<repo>/.claude/.build/evolution-daily.log` 尾部 + `~/.claude/decisions/postmortems/PENDING.md`，按 signal-tiers 三档消化（low 自动/mid 批量确认/high AskUser），无信号则汇报「零积压」即收。**含立版检查**（2026-09-27，ADR version-release-discipline：读+判定未立版行为变更集；有→升进化分档 L2/L3 执行快照+tag+基线对照行，无→跳过） | L1 |
| `状态` | 只读汇报：daily log 摘要 + PENDING 计数 + 周评估报告结论（`weekly-eval-report.md`）+ 联审锚距今天数 + 外部资讯扫描（内建 WebSearch 如可用则 ≤5 条带 URL，不可用则跳过），不动任何文件。**本行资讯扫描即外参节律的唯一轻量通道** | L0 |
| `外参` | 外参调研轮（对 `状态` 行资讯扫描的升档替代，非新增）：spawn 1 个 agent 单方向外参检索（内建 WebSearch 如可用；不可用则本轮跳过并汇报），low 档机械入 PENDING 不直写 ADR/KNOWLEDGE；执行后 touch last-external-action.marker。节律单源=evolution-discipline 三档表「外参节律」行 | L1（全力=L3/战役） |
| `决策` | 手动拉起 14 天决策批（第三入口，与 session-start 指针/自动兜底同门）：读 PENDING 高风险攒批项，**批次门一次 multiSelect 确认**（与决策档同一门，不建第二确认面）；确认后 low 自动/mid 批量/high 按裁决执行 | L1 |
| `自审` | 单域自审（本仓只保留 skill 资产域，治理部门未包含）：skill-evolution 体检（gate-rules）+ 周评估证据链核对；落点三分（超线→PENDING/机械→low/体系分歧→decision-record） | L1 |
| `正向` | 增强探索：spawn 1 个 Explore agent 按「缺失能力/断链环节/值得补的增量」扫体系（元层 `~/.claude` + 当前项目层），每条发现须真实信号证据；回传后主控复核，low 档直做、其余入 PENDING | L1 |
| `逆向` | 对抗审查：spawn 1 个 Explore agent 按「反向证伪/矛盾条款/该回退机制」扫（重点=最近一周的改动面）；主控复核后 High 当场修、Med 择机、Low 登记观察 | L1 |
| `减负` | 瘦身轮：spawn 1 个 Explore agent 按「死内容/冗余副本/注入面可指针化」扫；消重≠改写（语义不变的压缩改写不在本方向——单文件压缩主控直改），废弃物理删须零活跃引用实证，删前逐项列清单确认 | L1 |
| `联审` | 部门交叉审查：效果验证线+I/O 合规线只读对账，落点三分（结果直落 PENDING）；**执行完必须跑 `weekly-eval.py --joint-review` 重置锚** | L2 |
| `all` | 顺次跑 正向→逆向→减负（各 1 个并行 Explore）→ 汇总去重 → 统一分档消化；三方向全 High 时升档为多 Explore 并行（本仓无战役机制）。L2 轮 High 项同 evolution-discipline L3 注记规则（≥2 独立候选+落选落盘+单 commit hash 回退锚） | L2 |
| `画像` | 输入习惯画像试跑入口（session-search 未包含）：主控直读近期会话 `.build` 数据产出画像建议，观察期不动决策 | L1 |

> 托管措辞路由：托管语义按用户画像自决档执行。

## 硬约束

1. 探索 agent 只传任务不传正文；回传契约 schema 单源=io-protocol §3+抽查原文复核（`io-budgets.subagent_return` 仅参数值键）；探索类发现扩展字段 `{位置, 证据, 建议, 档位/severity}≤8 条`。
2. 所有真行为改动走 ADR/KNOWLEDGE 沉淀（decision-record）；计数锚改动两处同笔（README/KNOWLEDGE）；预算数值改动逐项留痕。
3. 轮末输出一行总账：`消化 N 条（low X/mid Y/high Z）→ 采纳 N1 / 入 PENDING N2 / 驳回 N3`。
4. anti-pattern 否决门（T120，2026-09-28）：候选直做/接线前 grep `~/.claude/.state/evolution-pool/anti-patterns-<当月>.md` 签名关键词，命中即否决该候选→转 PENDING 登记或 decision-improve，不直做；新增反模式按该文件头部行级格式追加（失败证据断言门锚义务不变，evolution-discipline §沉淀前）。
5. 效果回填义务：本轮动作若动了 token-baseline 有 expect 的项，主控对账回填（measured 不能留 null）。
