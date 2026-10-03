---
name: decision-consensus
description: "多角色共识/Delphi 共识/方案裁决，多轮收敛，主控编排 PCF。"
---

# decision-consensus · 多轮迭代 Delphi 共识

> 定位：决策体系「共识」模式。单轮对抗式裁决用 PCF 三件套；多角色、需迭代收敛的分歧用本 skill——在 PCF 单轮内核外加多轮收敛层，不新建 agent。机制/变更审查类对抗归 `devils-panel`（双向边界）。
> 流程：解析分歧 → 多视角并行提案 → 汇总去标识 → 收敛判定 → 裁决残余分歧 → 产出最终共识。

## 运行约定

> 目录与中间产物约定（`{task_dir}`/`{skill_dir}`、`.build/` gitignore）见 `~/.claude/skills/_shared/runtime-conventions.md §1`。

- 产物命名：`consensus.round{R}.proposal.{i}.json` / `consensus.round{R}.summary.json` / `consensus.final.json` / `debates.md`
- 复用现有 agent（不新建）：`pcf-proposer` / `pcf-critic` / `pcf-finalizer`，主控编排多轮

## 术语（本 skill 定调，所有 references 对齐）

| 术语 | 含义 |
|------|------|
| 轮（Round） | 迭代单位，R=1..max_rounds（默认 3） |
| 视角（Role） | 利益相关立场：架构 / 安全 / 性能 / 用户 / 成本（可裁剪） |
| 共识点 / 差异点 | 所有 proposer 一致的要点 / proposer 之间分歧的要点 |
| 收敛（Convergence） | 差异趋稳；判定规则单源=`references/convergence-rules.md` |
| 共识度（convergence_score） | 0-100，共识点数 /（共识点数 + 差异点数）× 100 |
| 残余分歧 | 收敛后仍未消除的差异点，交 critic/finalizer |

## 何时启用

**启用**：用户说「多角色共识 / Delphi 共识 / 方案裁决」，或主控识别到：方案分歧、多角色利益冲突、高风险权衡、架构选型、需 trade-off 决策。

**不启用**：需求模糊、多种解读 → 用 decision-explore；产物完成待验收 → 用 decision-verify；单轮即可裁决的简单二选一 → 直接用 PCF 三件套。

## 用户输入

- 分歧问题描述（必需，含各方立场与争议点）；候选方案空间 / 约束（可选）
- 期望参与视角（可选，默认 5 视角集）；决策时限 / 风险偏好（可选）

## 执行流程

| Step | 动作 | 工具 / 详情 |
|------|------|------------|
| 0 | 解析分歧 + 召回 | 提取争议点 + 选定参与视角（裁剪规则单源=`references/delphi-protocol.md §视角裁剪规则`）；**读 `~/.claude/decisions/KNOWLEDGE.md` 找相关 ADR/postmortem 装配裁决背景**（按 `standards/common/knowledge-protocol.md` 标准词表匹配分歧主题，供各视角 proposal 参考） |
| 1 | 并行提案 | 每视角 spawn 1 个 `pcf-proposer`（并行、互不可见）；主控按转写规则产 `consensus.round{R}.proposal.{i}.json` |
| 2 | 汇总去标识 | 主控合并各 proposal → 提取共识点 + 差异点 → `consensus.round{R}.summary.json`（含 convergence_score） |
| 3 | 收敛判定 | 见 `references/convergence-rules.md`：收敛 → 残余≥2 走 Step4（critic）再 Step5、残余<2 直 Step5；未收敛且 R<max_rounds → R++，summary 反馈各视角回 Step1 |
| 4 | 残余挑战（可选） | 收敛后仍剩 ≥2 残余分歧 → spawn `pcf-critic` 挑战 |
| 5 | 最终裁决 | spawn `pcf-finalizer` → `consensus.final.json`（与 PCF finalizer 输出兼容） |
| 6 | 记录 | 追加 `debates.md`（格式单源 `_shared/pcf-execution-flow.md §辩论 history 持久化`，2026-09-25 自 task-orchestrator 迁入） |
| 7 | 指标采集 | 按 `references/decision-mapping.md §metrics 采集`，写 `{task_dir}/.build/metrics.latest.json`，含 `rounds`/`convergence_score`/`residual_risks_count`/`overturn_rate`（调用留痕由 collect.py 自动落全局轨） |
| 8 | 沉淀 | consensus.final.json 属运行时产物不入 KNOWLEDGE 索引；重大裁决 → 转 `decision-record` 沉淀 ADR（ADR 为唯一索引载体，`pending_adr`→`linked_adr` 链随 record 落地，见 `decision-record/references/adr-protocol.md §跨类型链`） |

## 输出规范

- `consensus.round{R}.proposal.{i}.json`：`{role, proposal, rationale, confidence}`
- `consensus.round{R}.summary.json`：`{round, consensus_points[], divergences[], convergence_score}`
- `consensus.final.json`：`{decision, confidence, reason(≤150字), residual_risks[], pending_adr(可选,跨类型链), linked_adr(可选,record 沉淀后回写)}`
- `.build/metrics.latest.json`：`{rounds, convergence_score, residual_risks_count, overturn_rate}`（留人工复盘比对）；schema 转写规则与编排映射见 `references/decision-mapping.md`

## 降级策略

> 通用失败降级（空输入/用户全拒绝/上游产物缺失/spawn 失败）见 `standards/common/skill-failure-protocol.md`，本节仅列 consensus 特有项。

| 场景 | 处理 |
|------|------|
| 单轮即高度收敛（R=1 差异点=0） | 跳过迭代直 finalizer（细则=convergence-rules.md §单轮收敛特例） |
| R≥max_rounds 仍未收敛 | 强制收敛（细则=convergence-rules.md §强制收敛处理） |
| proposer 输出 schema 异常 | 主控按转写规则兜底取 candidates[0]，`[WARN]` 记录 |
| 视角过少（<3）无法形成有效共识 | 提示用户补充视角，或降级为单轮 PCF |
| 强制收敛 confidence=low 后用户仍拒绝/无响应 | 启用权重投票 fallback（各视角按 confidence 加权、简单多数决）或 escalate_to_user 强制升级——决策不悬空 |

## 产物生命周期

- `consensus.final.json` + `debates.md` 本地保留，不入库（决策沉淀走 ADR）
- `.build/` 中间轮次产物执行后清理（保留 final + debates）；`.build/metrics.latest.json` 留人工复盘比对，不随中间轮次产物一并清理

## 资源

| 文件 | 用途 | 读取 |
|------|------|------|
| `references/delphi-protocol.md` | 多轮迭代协议（角色 / 匿名 / 反馈 / 信息流） | 全量 |
| `references/convergence-rules.md` | 收敛判定（差异度量 / delta / max_rounds / 共识度） | 全量 |
| `references/decision-mapping.md` | 共识→PCF 编排映射 + schema 转写规则 | 全量 |
| `templates/consensus-round.json` | 单轮产物模板 | 按需 |
| `templates/consensus-final.json` | 最终共识模板 | 按需 |

## 反模式

| 禁止 | 正确做法 |
|------|---------|
| 让 proposer 互相可见（破坏匿名） | proposer 间隔离，仅主控汇总去标识 |
| 隐式跳过收敛判定 | 每轮显式计算 convergence_score 并记录 |
