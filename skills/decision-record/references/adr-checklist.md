# ADR 产物质检清单

> ADR 文档的逐项校验清单，供 decision-verify（adr 对象）红队校验 + decision-record 生产自检。

## 与其他文档的关系

- `adr-protocol.md`：约束定义（原理、状态机、编号规则、跨类型链协议）
- `adr-writing-guide.md`：写法指引（五要素写法、反模式、长度粒度）
- 本文件：可勾选执行版，机械项为主，供 review-rule 红队判定

---

## 1. frontmatter 检查

### 规范性（dimension: 规范性）

#### 机械项
- [ADR-M01] frontmatter 必含 title/status/date 三字段 | severity: P0 | 类型: 机械 | dimension: 规范性
- [ADR-M02] status 取值 ∈ {Proposed/Accepted/Deprecated/Superseded by <slug>}，无非法值 | severity: P0 | 类型: 机械 | dimension: 规范性
- [ADR-M03] frontmatter 无 id 字段（文件名即唯一标识） | severity: P0 | 类型: 机械 | dimension: 规范性
- [ADR-M04] 可选链字段存在时值合法（related_consensus/related_postmortem/related_lifecycle/supersedes/superseded_by） | severity: P1 | 类型: 机械 | dimension: 规范性
- [ADR-M05] Superseded by <slug> 格式正确（by 后有空格 + 目标 ADR 语义名） | severity: P1 | 类型: 机械 | dimension: 规范性

---

## 2. 五要素章节检查

### 完整性（dimension: 完整性）

#### 机械项
- [ADR-M06] 五要素章节齐全：Status/Context/Decision/Consequences/Alternatives 五个二级标题存在 | severity: P0 | 类型: 机械 | dimension: 完整性
- [ADR-M07] Status 章节内容与 frontmatter status 一致 | severity: P0 | 类型: 机械 | dimension: 完整性
- [ADR-M08] Context/Decision/Consequences 三章节非空（≥1 行正文） | severity: P0 | 类型: 机械 | dimension: 完整性

#### AI项
- [ADR-A01] Context 章节只写背景与约束，未写成方案描述 | severity: P1 | 类型: AI | dimension: 完整性
- [ADR-A02] Decision 章节含明确 chosen 陈述（非"考虑各方面后决定"类含糊表述） | severity: P0 | 类型: AI | dimension: 完整性
- [ADR-A03] Decision 章节附 2-4 条关键理由，与 Context 驱动因素对应 | severity: P0 | 类型: AI | dimension: 完整性
- [ADR-A04] Consequences 章节含正向/负向/中性三类影响（非只写正面） | severity: P0 | 类型: AI | dimension: 完整性
- [ADR-A05] Alternatives 章节（若存在）列 2-3 个备选 + 每个附拒绝理由 | severity: P1 | 类型: AI | dimension: 完整性
- [ADR-A06] Alternatives 章节（重大决策）非空 | severity: P0 | 类型: AI | dimension: 完整性
- [ADR-A07] ADR 正文长度在 30-80 行范围（非超长混入实现细节，非太短<10 行） | severity: P1 | 类型: AI | dimension: 完整性

---

## 3. 编号一致性检查

### 规范性（dimension: 规范性）

#### 机械项
- [ADR-M09] 文件名符合语义 kebab 格式（无数字编号前缀，见 doc-naming） | severity: P0 | 类型: 机械 | dimension: 规范性
- [ADR-M10] slug 全局唯一（meta/data 双域+skill 本地 decisions+project-docs grep 查重无撞名） | severity: P0 | 类型: 机械 | dimension: 规范性
- [ADR-M11] 文件名不含数字前缀（去数字重构后防复发） | severity: P1 | 类型: 机械 | dimension: 规范性

---

## 4. 状态机一致性检查

### 规范性（dimension: 规范性）

#### 机械项
- [ADR-M12] Supersedes 双向存在：新 ADR 声明 supersedes，旧 ADR Status 声明 Superseded by <slug>（局部取代例外：旧 ADR 保持 Accepted + 正文备注，见 adr-protocol §状态机） | severity: P0 | 类型: 机械 | dimension: 规范性
- [ADR-M13] 无单向悬挂：有 Superseded by 声明时，对应新 ADR 存在且声明 supersedes | severity: P0 | 类型: 机械 | dimension: 规范性
- [ADR-M14] Supersedes 链无循环（A→B→A 类循环依赖） | severity: P0 | 类型: 机械 | dimension: 规范性

---

## 5. 索引一致性检查

### 规范性（dimension: 规范性）

#### 机械项
- [ADR-M15] KNOWLEDGE.md adr 行与实际 ADR 文件一一对应（无孤儿：文件存在索引无；无幽灵：索引有文件无，双向对账） | severity: P0 | 类型: 机械 | dimension: 规范性
- [ADR-M16] 新条目行格式对齐 `- [标题](adr/{域}/{slug}.md) | adr | 摘要 | 链` 且落对 tag 节 | severity: P1 | 类型: 机械 | dimension: 规范性
- [ADR-M17] 废弃动作同步：物理删除 ADR 须同步删 KNOWLEDGE 条目（历史靠 git，无 archive 层） | severity: P0 | 类型: 机械 | dimension: 规范性
- [ADR-M18] KNOWLEDGE 尾注计数注释与目录实测一致（meta/data 两数） | severity: P1 | 类型: 机械 | dimension: 规范性

---

## 6. 跨类型链闭环检查

### 完整性（dimension: 完整性）

#### 机械项
- [ADR-M19] related_consensus 字段指向真实存在的 final.json（路径有效，文件存在） | severity: P0 | 类型: 机械 | dimension: 完整性
- [ADR-M20] related_postmortem 字段指向真实存在的 postmortem 文件 | severity: P1 | 类型: 机械 | dimension: 完整性
- [ADR-M21] pending_adr 在 consensus 中存在对应 linked_adr 回写（双向链闭环） | severity: P1 | 类型: 机械 | dimension: 完整性
- [ADR-M22] related_lifecycle 字段指向真实存在的 lifecycle-decision.json（路径有效，文件存在） | severity: P1 | 类型: 机械 | dimension: 完整性

---

## 检查项统计

- 机械项：22 项（ADR-M01 ~ ADR-M22）
- AI 项：7 项（ADR-A01 ~ ADR-A07）
- 总计：29 项

## 按维度分组

- **规范性**：ADR-M01~M05（frontmatter）、ADR-M09~M11（命名）、ADR-M12~M14（状态机）、ADR-M15~M18（索引）= 15 项
- **完整性**：ADR-M06~M08（五要素机械）、ADR-A01~A07（五要素 AI）、ADR-M19~M22（跨类型链）= 14 项
- **正确性**：0 项（ADR 场景基本不适用，链指向真实存在归入完整性）
- **安全性**：0 项（ADR 文档不涉及运行时安全）