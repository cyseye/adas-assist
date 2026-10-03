---
name: decision-improve
description: "任务/项目 Postmortem+CAPA/OODA 复盘/持续改进：失败/延期/复发根因+CAPA 闭环，主 agent 交互式（不 spawn），分歧转 consensus。"
---

# decision-improve · Postmortem + CAPA 持续改进

> 定位：决策体系「持续改进」模式——决策对齐组（decision-*）的按需复盘组件，独立可用、不依赖编排触发，与其他 decision skill 平级协作（分歧转 consensus、重大决策转 record）。对象是项目任务（非 skill 资产）。
> 流程：触发识别 → 收集事实 → 判断分级 → 根因分析 → Postmortem 五要素 → CAPA 规划 → 沉淀闭环 → 指标采集。

## 运行约定

> 目录与中间产物约定（`{task_dir}`、`.build/` gitignore）见 `~/.claude/skills/_shared/runtime-conventions.md §1`。

- `{postmortem_dir}` = `~/.claude/decisions/postmortems/`（复盘文档存放目录）；不 spawn subagent，主 agent 交互式执行，根因分歧大时主控对抗自审裁决
- 命名：`{slug}.md`（语义 kebab 全局唯一，禁数字前缀）；CAPA 文档 `{slug}-capa.md` 同 slug 前缀链回

## 术语（本 skill 定调，所有 references 对齐）

| 术语 | 含义 |
|------|------|
| OODA | Observe-Orient-Decide-Act，复盘前端决策环（检测信号→判断分级→是否复盘→执行） |
| Postmortem 五要素 | 症状(Symptom)/根因(Root Cause)/影响(Impact)/行动(Action)/教训(Lesson) |
| 根因(Root Cause) | 技术根因 + 流程根因（对事不对人，不追责个人） |
| 纠正措施(Corrective) / 预防措施(Preventive) | 修当前已发生的问题 / 防同类问题再发（系统/流程层） |
| 复发(Recurrence) | 同类别问题历史 postmortem 已记录后再现 |
| CAPA 闭环 | per-action：Open→In-Progress→Closed→Verified；整体状态映射单源=`references/capa-protocol.md §CAPA 闭环状态机（per-action）` |

## 何时启用

**启用**：用户说「复盘 / postmortem / CAPA / 根因分析 / 持续改进」，或主 agent 识别到：任务失败/延期/缺陷复发/重大 incident/反复返工；复盘触发=上列人工/识别通道。

**不启用**：
- skill 资产进化反思（对象是 skill，非项目任务）→ `skill-evolution`；架构决策沉淀（非失败复盘）→ `decision-record`；产物质量验收（非事后复盘）→ `decision-verify`
- 单个 bug 的代码修复 → 当前无专项 skill，CAPA 代码 action 由主控按 dev-implement 流程执行或手工修复（本 skill 只做项目级根因+CAPA 规划）；需求模糊需澄清 → 主控直接问
- 方案分歧多角色裁决 → decision-consensus

## 用户输入

- 复盘触发事件（必需）：一句话点明发生了什么；时间线/已知事实（可选，缺则 Observe 步提问收集）；严重度/影响范围（可选，缺则 Orient 步判定）；是否允许走 consensus 裁决根因（可选）

## 执行流程

| Step | 动作 | 工具 / 详情 |
|------|------|------------|
| 0 | 触发识别（OODA-Observe 起点） | 识别复盘信号；判定是否值得复盘（严重度≥阈值，见 `references/postmortem-protocol.md §值得复盘的判定`）；无价值 `[INFO]` 退出 |
| 1 | OODA-Observe 收集事实 | 时间线/症状/影响/客观数据；**只记事实不归因**；AskUserQuestion ≤4 问/批；归因阶段标签取词表单源 `references/failure-taxonomy.md`（2026-09-26 D2 落地，禁自造同义标签） |
| 2 | OODA-Orient 判断 | 严重度分级(1-4)；查同类别历史 postmortem 判定是否复发（`references/capa-protocol.md §复发判定`）；**上游有 clarified-requirements.md 时：先读其 frontmatter `recall_refs` 直读命中条目，命中不足再全索引扫描**（转交指针化，ADR adr/data/token-effect-balance-v2）；否则**读 `~/.claude/decisions/KNOWLEDGE.md` 找相关 ADR/postmortem 装配根因背景**（按 `standards/common/knowledge-protocol.md` 标准词表匹配主题 tag；复发匹配规则单源=`references/capa-protocol.md §复发判定`，category 合法值=signal-tiers.json `capa_categories` 枚举）；选根因法（简单→5Why，复杂多因素→鱼骨） |
| 3 | OODA-Decide 决策 | 是否全量 postmortem；根因分歧大→主控对抗自审裁决根因；无复盘价值 `[INFO]` 退出 |
| 4 | 根因分析 | 5Why 或鱼骨（人/机/料/法/环/测），规则单源=`references/postmortem-protocol.md §根因分析法`；产出技术根因 + 流程根因 |
| 5 | Postmortem 五要素 | 按 `templates/postmortem.md` 写 `{postmortem_dir}/{slug}.md`：症状/根因/影响/行动/教训 |
| 6 | CAPA 规划 | 按 `templates/capa.md` 写 `{postmortem_dir}/{slug}-capa.md`：纠正 + 预防；每 action 必含 owner+due+验证标准 |
| 7 | 沉淀 + 闭环 | 按 `standards/common/knowledge-protocol.md` 索引 schema（summary 守 `standards/common/knowledge-protocol.md` summary 字段 bigram 约定）**更新 `~/.claude/decisions/KNOWLEDGE.md`**：postmortem/capa 索引条目（type=postmortem|capa）+ 建 `related_verify`/`related_adr` 跨类型链（`decision-record/references/adr-protocol.md §跨类型链`）；CAPA 行动闭环前 capa.md 整体状态保持 Open（沉淀落点：postmortem/capa 正文留本域，进平台 memory 层走 `memory-governance` 通道）；**若 CAPA 含纠正类 action（type=纠正）→ capa.md 标 `requires_reverify=true`，提议重跑 `decision-verify` 确认根因消除（闭合 verify→improve→re-verify）** |
| 8 | 指标采集 | 按 `references/improve-mapping.md §metrics 采集`，写 `{task_dir}/.build/metrics.latest.json`（postmortem_quality/action_count/capa_closed_count/action_completion_rate/recurrence_rate/recurrence_category）（调用留痕由 collect.py 自动落全局轨） |

## 输出规范

产物 `{slug}.md` 必含【Postmortem 五要素】（定义见 §术语；写法见 `references/postmortem-protocol.md`），产物顺序：① 症状 ② 根因（附 5Why/鱼骨链）③ 影响 ④ 行动（指向 capa.md action_id）⑤ 教训。

frontmatter：`id` / `title` / `date` / `incident_date` / `severity`(1-4) / `category`(复发匹配键) / `status` / `related_postmortem`(复发时链回历史 id) / `related_verify`(可选，跨类型链) / `related_adr`(可选，跨类型链)；跨类型链字段见 `decision-record/references/adr-protocol.md §跨类型链`。
`{slug}-capa.md` actions 表：`action_id` / `type`(纠正|预防) / `description` / `owner` / `due` / `status`(Open|In-Progress|Closed|Verified) / `verification`。

## 降级策略

> 通用失败降级（空输入/用户全拒绝/上游产物缺失/spawn 失败）见 `standards/common/skill-failure-protocol.md`，本节仅列 improve 特有项。

| 场景 | 处理 |
|------|------|
| 事实不足无法定根因 | 根因标 `[待补充]` + `[WARN]`，不杜撰 |
| 根因分歧大 | 主控多方案对抗自审裁决，不内建 |
| CAPA 无法闭环（资源/人力） | 标 `[Open]` + owner + 复盘日期，不强行关闭；资源恢复后必须重新启动闭环，不可长期搁置 |
| 非失败 / 无复盘价值 | 建议不启动，`[INFO]` 说明理由 |
| 编号冲突（并发） | 取较大序号 + 1 重试 |

## 产物生命周期

- `postmortem.md` + `capa.md` 落 `decisions/postmortems/`，分层入 git（decisions-tiered-versioning：复盘知识资产入库；PENDING 信号池本地）
- postmortem status：初始 `draft`（Step 5 写入）；Step 7 沉淀时五要素齐全且经确认 → `accepted`；已 `accepted` 正文不可变，新认知另起 postmortem 并在 `related_postmortem` 链回
- capa 整体 status：映射规则单源=`references/capa-protocol.md §CAPA 闭环状态机（per-action）`
- `.build/` 草稿执行后清理（metrics.latest.json 留人工复盘比对，无自动消费方）

## 资源

| 文件 | 用途 | 读取 |
|------|------|------|
| `references/postmortem-protocol.md` | OODA 四阶段 + 五要素 + 根因法 + 严重度分级 + 值得复盘判定 | 全量 |
| `references/capa-protocol.md` | 纠正 vs 预防 + CAPA 闭环状态机 + 复发判定 + 验证标准写法 | 全量 |
| `references/improve-mapping.md` | 与其他 skill 边界 + 产物字段映射 + metrics 采集 + 沉淀与复发闭环 | 全量 |
| `templates/postmortem.md` | 复盘文档模板 | 按需 |
| `templates/capa.md` | CAPA 文档模板 | 按需 |

## 反模式

| 禁止 | 正确做法 |
|------|---------|
| 杜撰根因（5Why 无依据） | 规则单源=`postmortem-protocol.md §根因分析法 5Why` |
| 只写纠正不写预防 | 纠正修当下，预防防再发，两者都要 |
| 责备个人 | 对事不对人，根因分技术根因+流程根因 |
| CAPA 无 owner / due | 每 action 必含 owner+due+验证标准 |
| 复盘变总结会无根因 | 必须有根因分析，不只是流水账 |
| 把 postmortem 写成 PRD | 只记复盘+CAPA，不展开实现 |
| metrics 隐式采集（不写 Step 8） | Step 8 显式写 metrics.latest.json |
