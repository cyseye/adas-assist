---
name: decision-record
description: "决策沉淀/ADR/架构决策记录：记为可追溯 ADR，主 agent 交互式执行（不 spawn），可选 consensus；不做裁决只做沉淀。"
---

# decision-record · ADR 决策沉淀

识别决策点 → 背景澄清 → 备选梳理 → 决策陈述 → 后果评估 → 命名写 ADR → 状态机维护。

> 定位：决策体系「决策沉淀」模式。与 consensus / lifecycle / verify 互补：它们产生决策，本 skill 固化决策。决策须先有结论，再沉淀。

## 运行约定

- `{adr_dir}` = `~/.claude/decisions/adr/{域}/`（双域：`meta/` 元层工程——adas-assist 机制/文档治理/方法论，无法归类归此；`data/` 数据业务共性决策，首份落此写 frontmatter `domain: data`（dual-domain-taxonomy）；**落点路由**：harness skill 业务决策 → 对应 skill `decisions/`（本地保留、不进本索引、不扫治理信号），业务项目技术选型 → `project-docs/`）
- `{task_dir}` = 当前任务工作目录（默认 cwd），中间产物走 `{task_dir}/.build/`
- 不 spawn subagent，主 agent 交互式执行
- 命名：`{语义slug}.md`（目录即业务域），slug 全局唯一、禁数字编号（规范见 `standards/common/doc-naming.md`）

## 何时启用

**启用**：用户说「记录决策 / 沉淀 ADR / 写架构决策记录」，或走 decision-consensus 共识裁决，或主 agent 识别到值得沉淀的架构决策（见 `references/adr-protocol.md §何为值得沉淀的决策`）。

**不启用**：
- 需求模糊需澄清 → decision-explore；方案分歧 → decision-consensus
- 产物质量验收 → `decision-verify`；skill 增删判断 → decision-lifecycle

## 用户输入

- 决策主题（必需）：一句话点明决策对象
- 决策结论（可选）：已形成的 chosen 方案；缺则主控先澄清再陈述
- 背景与约束、备选方案（可选）：前者=用户已知的问题/约束/驱动因素，缺则主控按 Context 要素提问；备选缺则主控梳理

## 执行流程

| Step | 动作 | 工具 / 详情 |
|------|------|------------|
| 0 | 识别决策点 + 召回 | 用户指定 / 主控从上下文提取 / 主控裁决转交（consensus/lifecycle/devils-panel）（`adversary-report.json` verdict=reject 且用户强行推进 → 记「风险已知接受」ADR，compromise → 记有条件通过，见 `devils-panel/references/integration-mapping.md 接入点4`）；判定「值得沉淀」（`adr-protocol.md §何为值得沉淀的决策`）；**上游有 clarified-requirements.md 时：先读 frontmatter `recall_refs` 直读命中条目，命中不足再全索引扫描**（转交指针化，ADR adr/data/token-effect-balance-v2）；否则**读 `~/.claude/decisions/KNOWLEDGE.md` 装配 Context**（按 `standards/common/knowledge-protocol.md` 词表匹配决策主题，补 Step 1 背景）；**去重**：召回发现高度相似已有 ADR（同主题+同方向）→ 不自动建新，提示三选：① Supersede（决策变更，旧 ADR 标 Superseded）② 跳过（完全重复，仅记 linked_adr）③ 合并（新视角补进旧 ADR Consequences） |
| 1 | 背景澄清 | 按 `references/adr-protocol.md §五要素` 的 Context 要素提问（问题 / 约束 / 驱动因素），AskUserQuestion ≤4 问/批；复用 socratic 思想 |
| 2 | 备选梳理 | 用户已给→直接；缺→主控列 2-3 备选 + 权衡，或主控自做正反两臂分析形成结论 |
| 3 | 决策陈述 | 明确 chosen + 关键理由（与驱动因素对应，2-4 条）+ rejected 理由 |
| 4 | 后果评估 | 正向 / 负向 / 中性三类影响 |
| 5 | 编号 + 写 ADR | 按 `templates/adr.md` 写 `{adr_dir}/{语义slug}.md`（归域规则见运行约定）；更新 `~/.claude/decisions/KNOWLEDGE.md` 单源索引（写前 re-read 防并发丢条，见 `adr-protocol.md §并发修改`）；**自检**：按 `references/adr-checklist.md` 核对命名/frontmatter/KNOWLEDGE 同步。**本 skill 是全部决策留痕的唯一收口**（含投委会表决⑥、探索战役 P7、效果回退判定）：其他环节只提议不写 ADR |
| 6 | 状态机 + 跨类型链 | Supersede 双向记录（规则=`adr-protocol.md §状态机`）；源自 consensus → frontmatter 写 `related_consensus` 且 consensus.final.json 回写 `linked_adr`（`adr-protocol.md §跨类型链`）；**自检**：`pending_adr→linked_adr` 回写完成、`related_consensus` 指向真实 final.json、Supersedes 双向一致 |
| 7 | 收尾 + 沉淀 | 写 `metrics.latest.json`（调用留痕由 collect.py 自动落全局轨）；按 `standards/common/knowledge-protocol.md` schema **更新 `~/.claude/decisions/KNOWLEDGE.md` 索引**（新条目 type=adr，含跨类型关联字段） |

## 输出规范

产物 `{语义slug}.md` 必含五要素（写法见 `references/adr-writing-guide.md`）：① Status ② Context ③ Decision ④ Consequences ⑤ Alternatives（重大决策必填）。

frontmatter：`title` / `status` / `date` / `supersedes`（可选）/ `superseded_by`（可选）/ `related_consensus` / `related_postmortem`（可选，跨类型链，见 `references/adr-protocol.md §跨类型链`）。

## 降级策略

> 通用失败降级（空输入/用户全拒绝/上游产物缺失/spawn 失败）见 `standards/common/skill-failure-protocol.md`，本节仅列 record 特有项。

| 场景 | 处理 |
|------|------|
| 决策尚无结论 | 不强行沉淀；主控自做正反两臂分析形成结论 |
| 背景信息不足且用户无法补充 | Context 标「待补充」+ `[WARN]`，不杜撰约束 |
| 不值得沉淀（实现细节 / 可轻松回退） | 建议不建 ADR，`[INFO]` 说明理由 |
| 命名撞名（并发） | 换更精确语义 slug 重试（≤3 次） |
| 旧 ADR 缺失无法 Supersede | `[WARN]` 记录，不阻断新 ADR 建立 |

## 产物生命周期

- ADR 文档（`{adr_dir}/*.md`）+ KNOWLEDGE 索引为交付物，分层入 git（decisions-tiered-versioning：活跃域入库；PENDING 运行时本地；废弃 ADR 零活跃引用后物理删除靠 git 历史）
- 已 Accepted 的 ADR 正文不可变；新认知另起 ADR 并 Supersede（skill decisions/ 属本地进化沉淀，无 git 历史，重大变更直接改写）；`.build/` 中间提问草稿执行后清理

## ADR 库治理

**触发条件**（任一）：①本次沉淀新增/大改 ≥2 份 ADR ②活跃区（meta/data 双域）>24 份或单域 >18 份（阈值定版见 adr/meta/dual-domain-taxonomy）——主控**主动提议**治理，用户确认后执行；session-review `adr-governance-overdue` 信号自动兜底提醒（库超限时）。

**治理动作**（三板斧，非全量重写）：
1. **压缩**：单份 >40 行压回 ≤40——只留决策语义（Status/Context 2-3 行/Decision 要点/Consequences 正负各 1-2 行/Alternatives 各 1 行），实现细节归 skill 条款不留在 ADR
2. **废弃**：Superseded 且零活跃引用（grep skills/KNOWLEDGE/CLAUDE.md）→ **物理删除**（历史靠 git，decisions-tiered-versioning，无 archive 堆叠），同步删 KNOWLEDGE 条目；亦适用于 Accepted 零引用且裁决已由规范/结构承载的一次性重构 ADR
3. **分组复核**：活跃域按 meta/data 双域归属（细分主题走 KNOWLEDGE tag），新 ADR 归对域；harness 业务决策不进中央库（落对应 skill decisions/）

守不可变惯例：压缩不改决策语义、不改语义名、不断 supersedes 链——git 历史保全量。

## 记忆沉淀尾步（战役 20260917 采纳 #3：memory 沉淀者归口）

ADR 收口后判定：未达 ADR 线但跨项目通用或有复召回价值的教训 → 写平台 memory 散文件 + MEMORY.md 索引行（格式对齐 memory-governance 约定 Step1，含计数锚回填）；判据不达则不留。本步使 memory 链条「沉淀→召回→治理→淘汰」闭环，写路径唯一归口在此，其余组件只读。

## 资源

| 文件 | 用途 | 读取 |
|------|------|------|
| `references/adr-protocol.md` | 五要素 + 状态机 + 命名规则 + 与其他 skill 边界 + 沉淀判定 | 全量 |
| `references/adr-writing-guide.md` | Context/Decision/Consequences/Alternatives 写法 + 反模式 | 全量 |
| `references/adr-checklist.md` | ADR 产物质检清单（frontmatter/五要素/命名/状态机/索引/链） | verify adr 对象 / 生产自检 |
| `templates/adr.md` | ADR 文档模板 | 按需 |

## 反模式

| 禁止 | 正确做法 |
|------|---------|
| 决策无结论就沉淀 | 先有结论（consensus / PCF / 用户）再 record |
| 改已 Accepted 的正文 | 新认知另起 ADR 并 Supersede |
| Context 写成方案 / Consequences 只写正面 | Context 只写背景与约束；正/负/中性三类都要 |
| 把 ADR 写成 PRD / 设计文档 | 只记决策 + 理由，不展开实现 |
| 用数字编号命名 | 语义 slug 命名（规范见 standards/common/doc-naming.md） |
