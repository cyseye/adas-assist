---
name: devils-panel
description: "魔鬼天团——三方对抗自我监督（分级触发）：正方论证/反方挑战/裁判裁决，多轮攻守互换。"
---

# Skill: devils-panel · 魔鬼天团自我监督

三方对抗式自我监督：正方（支持者）论证变更必要性 → 反方（挑战者）挑风险 → 裁判（裁决者）评估争议提出折中 → 最终裁决。**按复杂度分级触发**——轻量变更主控自审，中等单轮快审，重大才完整多轮攻守互换。对抗对象为方案文档本身；重大方案另配「沙盘推衍」实证强化（`_shared/analysis-methodology.md §沙盘推衍`），互补不互替。

## 运行约定

1. `{skill_dir}` = `~/.claude/skills/devils-panel`；`{target_dir}` = 被审查对象目录；`{work_dir}` = `{target_dir}/.build/`
2. 文件传递：prompt 仅传路径不内联正文
3. 角色用通用 `subagent_type="claude"` + `references/adversary-roles-protocol.md` 模板构造 prompt（无专用 agent 文件）

## 触发条件（按复杂度分级）

> 与体系宪法 #5「智能分档」对齐。打分器（`assess_complexity`）被 `_shared/evolution-discipline.md §智能分档总则` 引用为通用缺省路由基——改判据须同步总则映射，防双源漂移。

| 维度 | 加分 |
|------|------|
| 影响范围 | 跨 skill +2 / 核心协议 +2 / 单 skill +1 |
| 可逆性 | 不可逆（无回滚方案）+2 / 回滚复杂 +1 |
| 数据支持 | 无真实信号 +1 / 假设驱动 +1 |

L1（≤1 分）=不触发主控自审；L2（≤3）=单轮快审；L3（>3）=完整对抗。判定标准、执行方式与缺省打分器伪代码详见 `references/integration-mapping.md §复杂度分级`、`§执行流程 Phase 0`。

**接入点**：四个接入点（decision-lifecycle Step6 / skill-evolution 根因前置 / session-start 周评估 L1 主控自审 / decision-record Step0 转交源）的默认级别与升级条件见 `references/integration-mapping.md §接入点总览`（唯一权威表）。

**不启用**：日常代码改动 / 文档措辞修订 / 配置参数微调（有明确回滚）/ 用户直接调用（应通过接入点）/ 方案分歧多角色收敛裁决 → `decision-consensus`（本 skill 管机制/变更审查类对抗，PCF 单轮快裁归其内核）。

## 用户输入（接入点传入）

| 参数 | 必选 | 说明 |
|------|------|------|
| target | 是 | 审查对象路径（skill/protocol/rule） |
| change_type | 是 | 变更类型（skill_add/skill_delete/skill_split/evolution_regression/system_health_scan） |
| evolution_history | 否 | 历史变更轨迹（EVOLUTION.md） |
| regression_details / scan_scope | 否 | 退化详情（skill-evolution 场景）/ 扫描范围（session-start 场景） |

## 执行骨架（canonical=详版伪代码 `references/integration-mapping.md §执行流程`，两处同改）

Phase 清单：0 召回+定档 → Round 1 正方→反方 → Round 2（仅 L3）替代方案→辩护 → Round 3 裁决 → 收尾——逐 Phase 动作单源见彼件，本处不重复。

**verdict 映射**：`reject`→BLOCK（返回接入点）；`compromise`→CONDITION（附条件）；`approve`→PASS。

**互斥检出（org-formations U8）**：收尾写报告前，对同工件存在性 grep `pcf.finalizer.md`（PCF 终裁面）；两面 verdict 方向相反（reject/BLOCK vs approve/PASS）→ AskUserQuestion 用户被动仲裁，结果回写边界。

## 输出规范

- `{target_dir}/adversary-report.json` — 最终报告（永久，ADR 证据）
- `{target_dir}/.build/`：`protagonist/antagonist.round{1,2}.json`、`referee.round3.json`、`adversary-summary.json` — 中间产物，执行后清理

## 异常处理

| 场景 | 处理 |
|------|------|
| target 缺失 | 硬失败 |
| spawn 失败 | 重试 1 次 → 仍失败 hard fail |
| protagonist / antagonist 输出异常 | 标 INFO：正方论证不足反方默认胜；反方无挑战正方默认胜 |
| referee 输出异常 | 标 ERROR：裁决失败，升级 AskUserQuestion |

## 转交边界

| verdict | 转交 skill | 触发理由 |
|---------|-----------|---------|
| reject / compromise | decision-record | reject=记录"风险已知接受" ADR（若用户强行推进）；compromise=记录有条件通过 |
| approve | 无 | 直接执行 |

## 反模式

| 禁止 | 正确做法 |
|------|---------|
| 正反方互相可见（破坏对抗） | 仅限上一轮输出可见（R1 反方见正方，R2 正方见反方） |
| 裁判参与早期轮次 / 跳过 Round 1 直接裁决 | 裁判仅 Round 3 介入；至少跑 Round 1，有争议才 Round 2 |
| 内联 prompt 传完整文件 | 仅传路径，subagent 自行 Read |

## 资源

| 文件 | 用途 |
|------|------|
| `references/adversary-roles-protocol.md` | 角色协议 + prompt 模板 |
| `references/integration-mapping.md` | 接入点映射 + 调用逻辑 + 复杂度分级 + 执行流详版伪代码（canonical） |
| `templates/adversary-report.json` / `adversary-summary.json` | 报告/追踪 schema |
| `decision-consensus/references/convergence-rules.md` | deadlock 检测（随仓复用） |
| `standards/common/knowledge-protocol.md` | 知识索引协议 |
