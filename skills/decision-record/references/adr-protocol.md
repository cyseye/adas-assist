# ADR 协议

> Architecture Decision Record（架构决策记录）。把重要决策记录为可追溯、可演进的结构化文档。采用轻量级 ADR（lightweight ADR）：一个决策一份文档，语义 slug 命名（规范见 standards/common/doc-naming.md），状态机驱动生命周期。

## 核心原则

- **决策可追溯**：记原因，不只记结果。后人能理解「当时为什么这么决定」。
- **一决策一文档**：不把多个无关决策塞进一份 ADR。
- **不可变正文**：已 Accepted 的 ADR 正文不回头改；新认知另起 ADR 并 Supersede 旧者。
- **沉淀而非裁决**：本 skill 不下决策结论，只记录；结论由 consensus / PCF / 用户给出。

## 五要素（每份 ADR 必含）

| 要素 | 作用 | 必填 |
|------|------|------|
| **Status** | 当前状态（见状态机） | 是 |
| **Context** | 背景：要解决什么问题、约束、驱动因素、当时的事实 | 是 |
| **Decision** | 采纳了什么决策 + 为什么选它 | 是 |
| **Consequences** | 后果：正向 / 负向 / 中性影响 | 是 |
| **Alternatives** | 考虑过但未采用的备选 + 拒绝理由 | 强烈建议（重大决策必填） |

> **decided-by 机读格式**：frontmatter `decided-by: <署名>` 单字段单人一行（禁自由文本塞多人），供继承指针计数（org-formations 未包含，规则照旧）机械 grep；战役 ADR 另必含归建清单占位段（`{skill_dir}/templates/adr.md`）。

## 状态机

```
Proposed ──采纳──▶ Accepted
   │                  │
   │                  ├──废弃──▶ Deprecated
   │                  └──被取代──▶ Superseded by <slug>
   └──不采纳──▶ Deprecated（或直接不建立）
```

| 状态 | 语义 | 转移触发 |
|------|------|----------|
| Proposed | 已提议待定 | 新建 ADR 默认状态；用户/主控确认后 → Accepted |
| Accepted | 已采纳生效 | Proposed 经确认；被新 ADR 取代 → Superseded |
| Superseded | 被更新 ADR 取代 | 新 ADR 显式声明 `Supersedes <slug>` |
| Deprecated | 不再适用 / 废弃 | 决策失效但无直接替代 |

> 状态转移须双向记录：新 ADR 写 `Supersedes <slug>`，旧 ADR 的 Status 改 `Superseded by <slug>`。
> **局部取代**（仅取代某 Decision，非整份）：新 ADR 声明 `Supersedes <slug> Decision K`，旧 ADR 保持 Accepted，**frontmatter `superseded_by` 留空**，取代关系只在**新 ADR 文内+旧 ADR 文末追加勘误行**承载（禁原地改写正文、禁填 superseded_by——规约 adr/meta/adr-immutable-errata-convention，2026-09-16 起）。

## 命名规则

- 格式 `{语义slug}.md`——目录即业务域，文件名语义 kebab **全局唯一、禁数字编号**（规范详见 `standards/common/doc-naming.md`）
- 新建时 grep 查重 slug；撞名换更精确语义词重试（≤3 次）。不引入文件锁——ADR 创建低频、主控串行为主，重试足以覆盖跨会话偶发并发（适用域限定：入库知识文件，git 仲裁兜底见下节；gitignored 运行时状态文件由 [shared-state-concurrency](../../../decisions/adr/meta/shared-state-concurrency.md) 的 flock+原子写机制管理）

## 并发修改

> 承接「不引入文件锁」原则（**仅限入库知识文件**——adr 知识域/KNOWLEDGE/postmortems）：ADR 操作低频、主控串行为主，跨会话偶发并发不靠锁，靠「重试 + git 仲裁 + verify 检测网」三层兜底。运行时状态文件（PENDING/reflex 状态/jsonl）被 hook 高频自动写且本地不入库，走 shared-state-concurrency ADR 的锁+原子写机制，本原则不适用于它们。

text 文件读-改-写在无锁下无法真正原子。各类修改并发的处理边界：

| 场景 | 事前 | 仲裁 | 事后兜底 |
|------|------|------|---------|
| KNOWLEDGE 索引更新 | 写前 re-read 检测目标条目是否已存在，避免重复追加/丢条 | git 提交仲裁（后提交者 merge conflict） | session-review `adr-consistency`（孤儿/缺条目双向对账） |
| 同一 ADR 内容改 | 无（低频） | git 仲裁 | verify `ADR-M01~M08` |
| Supersede 并发 | `superseded_by` 单值——一个 ADR 同时只能被一个新 ADR 取代 | 并发两个 Supersede 同一旧 ADR → 不自动合并，git 冲突/人工裁决 | verify `ADR-M12`（双向一致） |

原则：

- **不预防到底，但能发现+修复**：并发导致的不一致由 verify（adr 对象）与 session-review 一致性扫描事后揪出，主控按 `adr-checklist.md` 修复
- **git 是最终真相**：入库知识文件的跨会话并发终极冲突 = git merge conflict，adas-assist 不重造版本控制；PENDING 等运行时文件全量快照语义（最新磁盘真值胜出）
- **KNOWLEDGE 更新 re-read**：record 更新 KNOWLEDGE 时写前重读，目标条目已存在则跳过、检测到新条目则 re-base 自己的追加

## 与其他 decision skill 的边界

> 边界单源 = `decision-record/SKILL.md §不启用清单`（explore/consensus/verify/lifecycle 各自归位）。一句话：consensus / lifecycle / verify 负责「产生决策」，record 负责「固化决策」——决策须先有结论，再沉淀；record 本身不做裁决。

## 跨类型链

产物间跨类型关联（ADR↔consensus↔postmortem↔verify），弥补现仅有同类型链（Supersede / `related_postmortem`）的缺口。KNOWLEDGE.md 的「关联」字段是这些链的统一检索视图。

| 源产物 | 目标 | 字段（frontmatter 可选） | 写入时机 |
|---|---|---|---|
| ADR | 源 consensus | `related_consensus` | consensus 转交 record 沉淀时 |
| ADR | 触发它的 postmortem | `related_postmortem` | postmortem 揭示决策缺陷时回链 |
| ADR | 源 lifecycle | `related_lifecycle` | lifecycle 裁决转 record 沉淀时回链 |
| consensus | 待沉淀的 ADR | `pending_adr` → 沉淀后转 `linked_adr` | consensus 产 final.json 时标 pending，record 沉淀后回写 linked |
| postmortem | 触发它的 verify-report | `related_verify` | improve Step 7 落地时写 |
| postmortem | 相关 ADR | `related_adr` | postmortem 揭示决策缺陷 / CAPA 指向 ADR 时 |
| capa | 源 postmortem | `postmortem_id` | capa 建立时写 |
| lifecycle | 待沉淀的 ADR | `pending_adr` → 沉淀后转 `linked_adr` | lifecycle 建议落地后转 record 时标 pending，record 沉淀后回写 |

双向：上游产物也回写下游引用（如 consensus.final.json 加 `linked_adr`）。所有字段可选，不破坏现有模板契约（向后兼容）。KNOWLEDGE.md 的「链」字段**只放本表定义的协议跨类型链**（格式 `字段:目标ID`，无则 `-`）；topical 主题关联靠 tag 分节召回，不进「链」字段——避免协议链与软关联混淆。

## 何为「值得沉淀的决策」

满足任一即建议建 ADR：
- 架构层面（技术选型 / 分层 / 数据模型 / 跨服务契约）
- 难以撤销或撤销成本高
- 有多个合理备选且权衡非平凡
- 团队需对齐口径、避免重复讨论

不建 ADR：实现细节、可轻松回退的局部选择、纯执行性决定。
