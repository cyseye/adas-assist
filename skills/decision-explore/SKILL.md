---
name: decision-explore
description: "需求探索/Socratic 探索/澄清需求，收敛 artifact；主 agent 交互式不 spawn。"
---

# decision-explore · Socratic 需求探索

识别模糊点 → 五维度提问 → 显式假设陈述 → 产出澄清后的需求 artifact。

> 定位：决策体系「探索」模式。需求已明确 → 直接执行；需求模糊 → 先用本 skill 收敛。

## 运行约定

> 目录与中间产物约定（`{task_dir}`、`.build/` gitignore）见 `~/.claude/skills/_shared/runtime-conventions.md §1`。本 skill 不 spawn subagent，主 agent 交互式执行。

## 何时启用

**启用**：用户说「需求探索 / Socratic 探索 / 澄清需求」，或主 agent 识别到：需求模糊、多种解读、边界不清、「帮我想」类开放式请求。

**不启用**：
- 需求已明确、可直接执行 → 走对应实现 skill
- 方案分歧需多角色裁决 → 用 decision-consensus
- 产物待验收 → 用 decision-verify

## 用户输入

- 模糊需求描述（必需）
- 相关上下文/约束、受众与优先级（可选）

## 执行流程

| Step | 动作 | 工具 / 详情 |
|------|------|------------|
| 0 | 识别模糊点 + 召回 | 通读需求，标注歧义/缺口/多解读处；**读 `~/.claude/decisions/KNOWLEDGE.md` 装配背景**（按 `standards/common/knowledge-protocol.md` 词表匹配需求关键词，供 Step 1-2 参考） |
| 1 | 生成澄清问题 | 按 `references/socratic-dimensions.md` 五维度（目标 / 边界 / 假设 / 约束 / 验收）出题 |
| 2 | 提问 | AskUserQuestion（≤4 问/批）；用户答 → 更新认知；未答 → 转假设 |
| 3 | 收敛判定 | 见 `~/.claude/skills/_shared/socratic-inquiry.md` 收敛信号；未收敛 → 回 Step 1 补问 |
| 4 | 假设陈述 | 未澄清项按 `references/assumption-protocol.md` 六要素显式记录 |
| 5 | 产出 | 按 `templates/clarified-requirements.md` 写 `{task_dir}/.build/clarified-requirements.md` |
| 6 | 指标采集 | 主控算 completeness_score / dimension_coverage 写 `{task_dir}/.build/metrics.latest.json`（见下节） |
| 7 | skill 自检 + 转交 | lifecycle 信号单源 = `decision-lifecycle/references/lifecycle-signals.md`（`references/skill-lifecycle.md` 已是指针壳）：「需要新 skill / 拆分 / 合并」→ 转 `decision-lifecycle`；**多角色争议 / 方案分歧（本步直判，不走 skill-lifecycle.md）→ 标 handoff 转 `decision-consensus`**（handoff={rationale:分歧点, context:clarified-requirements.md 路径}，consensus 以澄清产物作分歧上下文，不重复探索） |
| 8 | 沉淀 | 重大决策点 / 需求结论 → 按 `standards/common/knowledge-protocol.md` schema 更新 `~/.claude/decisions/KNOWLEDGE.md`（type=requirement，tag 按词表主题归属，关联相关 ADR）；一般性需求不强制。无论是否沉淀，重大澄清收敛后**必须沉淀 ADR/KNOWLEDGE 条目**（reflex-check 以「窗口内有沉淀」判定 resolved 终态事件，weekly-eval 澄清转化率分子依赖它；澄清后零沉淀=该次澄清计为未转化——一次性问答类豁免）**产物 frontmatter 落 `recall_refs: [{path, why}]`**（Step 0 命中的 KNOWLEDGE/ADR 指针）——下游 finish-check/verify/improve/record Step 0 按指针直读，替代全索引重扫（转交指针化，ADR adr/data/token-effect-balance-v2） |

## 输出规范

产物 `clarified-requirements.md` 必含七节：⓪ 背景/召回（Step 0 召回片段，格式见 knowledge-protocol.md，无命中留 `[no-recall]`）① 目标（问题+成功定义）② 边界（包含/不包含）③ 假设（六要素表）④ 约束（技术/时间/资源/兼容）⑤ 验收标准（可观测）⑥ 待确认项。

## 指标采集（Step 6）

主控执行末尾写入 `{task_dir}/.build/metrics.latest.json`（留人工复盘比对；evolve 评估链已退役）：

```json
{"completeness_score": "<六节非空占位完成率，0-1>", "dimension_coverage": "<五维度获明确答案占比，0-1>"}
```

- `completeness_score`：六节（目标/边界/假设/约束/验收/待确认）非空占位占比
- `dimension_coverage`：五维度（目标/边界/假设/约束/验收）获明确答案占比

## 降级策略

> 通用失败降级（空输入/用户全拒绝/上游产物缺失/spawn 失败）见 `standards/common/skill-failure-protocol.md`，本节仅列 explore 特有项。

| 场景 | 处理 |
|------|------|
| 用户无法回答关键问题 | 转显式假设 + 标「待确认」（触发场景细则=`assumption-protocol.md §何时把不确定项转假设`） |
| 需求极度模糊无法提问 | 先出「最关键的 1 个问题」破冰 |
| 提问超过 3 批仍未收敛 | 停止提问，剩余不确定项全转假设，`[INFO]` 记录 |

## 产物生命周期

- `clarified-requirements.md` 为交付物，提交 git；`.build/` 中间提问草稿执行后清理（保留交付物）

## 资源

| 文件 | 用途 | 读取 |
|------|------|------|
| `references/socratic-dimensions.md` | 五维度提问清单 | 全量 |
| `~/.claude/skills/_shared/socratic-inquiry.md` | 苏格拉底问法公共纪律（收敛信号/提问纪律/自问分派；未包含，收敛信号见本件 Step 3） | 全量 |
| `references/assumption-protocol.md` | 假设陈述六要素 | 全量 |
| `references/skill-lifecycle.md` | 指针壳，单源=decision-lifecycle/references/lifecycle-signals.md | 按需 |
| `templates/clarified-requirements.md` | 产物模板 | 按需 |

## 反模式

| 禁止 | 正确做法 |
|------|---------|
| 隐式假设（默认但不写下来） | 全部按六要素显式记录 |
| 一次性问 >4 个问题 | 分批，每批 ≤4 |
| 把模糊需求直接交给实现 skill | 先探索收敛，再实现 |
| 提问复述用户已说的内容 | 只问歧义和缺口 |
| 命中收敛信号仍继续提问 | 命中即停，剩余转假设 |
