---
name: skill-evolution
description: "skill 进化框架：健康检查→语义验证→PCF 改进→反思；效果数据走调用日志+周评估。"

---

# skill-evolution · 结构化 skill 进化框架

规则体检 → 语义验证 → PCF 改进 → 记录 → 反思。

> **验证换面纪律（2026-09-27 启示①立项，外参锚 arXiv 2609.24972：无正则自改进同面增益在 OOD 面收缩/消失）**：进化效果验证须含 ≥1 个换面复测（换输入分布/换执行体/换判据任一），同面复测不构成效果证据——skill 行为级回归沿用此规（回归=近邻面，换面=远邻面，两者齐备才判「已修复」）。

> **评估引擎已退役，见 `references/evaluation-flow.md` §头**（2026-09-05 起；效果数据走全局调用日志+周评估，主链收缩为规则体检/语义验证/PCF 改进/反思）。
> **接入 scope**：目标 skill 需有可验证产物与测试集；执行编排型（dev-implement / figma-to-code 等）不接入，用「人工反馈 + memory」代替。

## 运行约定

- `{skill_dir}` = `~/.claude/skills/skill-evolution`
- `{target}` = 待评估/进化的目标 skill 目录

## 触发

**启用**：用户说「评估/进化/反思 skill」+ 指定目标 skill
**不启用**：执行目标 skill 本身（如生成 PRD）→ 走各自 skill

## 执行流程

| Step | 动作 | 工具 / 详情 |
|------|------|------------|
| 1 | **rules 健康检查（门控）** | rules_audit.py 本仓未包含——主控按 `references/authoring-checklist.md` 对 {target} 人工体检：high 问题 → 修完复检至无 high 才进 Step 2；low 记录不阻断 |
| 1b（建议）| **skill 文档语义验证**（首次接入 / 重大文档改动后）| 主控串行 spawn review-rule（checklist=`{target}/references/*-checklist.md`，无专属 checklist 时以 `references/authoring-checklist.md` 为通用审查依据，output=`{target}/.build/report.red-team.round.N.json`）→ exec-json-fixer；产出 `{target}/verify-report.json`；must_fix>0 先修再进 Step 2 |
| 2 | 效果数据观察（先运行目标 skill） | 全局调用日志 + 周评估指标 |
| 3 | 评估 | 主控读调用统计与周评估指标做效果判定 |
| 4 | 门控（默认不动） | 见 `references/gate-rules.md §2-§4` |
| 4.5（go 后）| 根因+影响面前置（方案准备步骤，非新门控） | 单源=`references/evaluation-flow.md §根因与影响面前置`（canonical 在 `_shared/evolution-discipline.md §根因与影响面前置`，本行只留指针） |
| 5（go）| PCF → worktree 改 skill → 回归 → EVOLUTION.md → 重大版本沉淀 ADR → 清理 | 见 `references/evaluation-flow.md` + `references/worktree-sop.md` + `references/cleanup-rules.md`；PCF 输入须含根因链+影响面清单（提案不回应根因即 fail）；重大版本变更转 `decision-record` 沉淀为 ADR（type=adr，复用既有决策沉淀机制），让 decision-* Step0 召回命中进化决策；小改动留 EVOLUTION.md 不强制回流（避免 KNOWLEDGE 碎片化） |
| 6（定期）| 反思 | 见 `references/reflection-guide.md`；结果记本目录反思日志（文件未建档前由执行轮按需创建） |

## 资源

| 文件 | 用途 | 读取 |
|------|------|------|
| `references/gate-rules.md` | 接入条件 / 触发门控 / 不动清单 / 量化门槛 | 全量 |
| `references/evaluation-flow.md` | 进化执行流程 + 回归验证 SOP | 全量 |
| `references/cleanup-rules.md` | 产物分类与清理时机 | 全量 |
| `references/worktree-sop.md` | Worktree 隔离 SOP | 全量 |
| `references/reflection-guide.md` | 反思维度与步骤 | 全量 |
| `scripts/rules_audit.py` / `scripts/worktree-evolve.sh` | 本仓未包含（结构体检走 Step 1 人工口径；worktree 隔离按 `references/worktree-sop.md` 手工执行） | — |
| `templates/` | EVOLUTION 模板 | 按需 |

## 反模式

| 禁止 | 正确做法 |
|------|---------|
| 多轮干预后自动改 skill | 主 agent 提议，等用户确认后才启动 |
| 回归验证在当前工作区跑 | 必须 worktree 隔离（见 `references/worktree-sop.md`） |
| 进化完不清理中间产物 | 见 `references/cleanup-rules.md` 清理时机 |
| 每轮顺便优化 | 只改有量化收益的具体问题 |
