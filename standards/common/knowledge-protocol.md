# 决策知识召回与索引协议

> 统一各 decision-* skill 对 `~/.claude/decisions/KNOWLEDGE.md` 的「召回（读）」与「沉淀（写）」，
> 替代此前各 skill Step0 各自手写的 tag 匹配逻辑。本文件定字段级契约；闭环机制已兑现于 decision-* 知识钩子与反射层。

## 一、召回协议（消费端 · 各 skill Step0）

召回 = 读 KNOWLEDGE.md，按主题域装配相关历史产物作当前任务背景。

### 标准主题 tag 词表（= KNOWLEDGE 节轴，领域驱动）

| tag | 覆盖范围 | 典型产物 |
|---|---|---|
| meta/机制 | 元层运转机制与架构（反射/hook/闭环/并发/监督/检索/路由/进化链） | adr + decision |
| meta/治理 | 边界规则资产（入库/分类/文档/skill 资产/宪法/信号分级/收尾门/克制登记） | adr + decision |
| meta/方法论 | 流程判据与分档（分析方法/影响面/公共层抽取/智能分档/收敛边界） | adr + decision |
| meta/复盘 | adas-assist 工程教训（postmortem/capa 横切节） | postmortem + capa |
| data/模型 | 表设计/ER/数据结构 | adr + postmortem |
| data/加工 | ETL/tech-spec/数据流水线 | adr |
| data/展示 | 前端还原/figma/可视化 | adr |
| meta/外参 | 外参/调研沉底件索引行（原文本地不入库；R8 召回面义务承载节，2026-09-27） | reference |

> data 各节实现三层统一召回（knowledge-doc-governance-consolidation 定版）：skill 本地 `decisions/` 与 `project-docs/` 产物落点不变，精选跨会话召回价值条目索引至此；纯项目实现细节（表结构/阈值/特定流程）仍不进本索引。`data/服务` 0 条不开节，≥2 再开（零空节）；lifecycle/requirement 等流程型条目按主题归最近 meta 节。
> 归位细则：复盘节仅收 meta 域 postmortem/capa，data 域复盘按链路归节；分档/分级判据归方法论，交付/收尾门资产归治理（流程内嵌确认环节归方法论）；跨域体系整合决策归 meta，data 节收数据链路域 skill 的本地决策（含该域 skill 基建）。

新增 tag：仅当现有 tag 无法覆盖且预计 ≥2 条产物落入，才开新节，避免碎片化（不为假设域预填）。

### 召回规则

1. 从当前任务提取关键词（需求 / 决策主题）
2. 命中上表 tag 的节（同义 / 包含匹配，非全词）
3. 装配命中节内全部条目作背景，取其「摘要」字段
4. 无命中 → 不强召回，产物背景节记 `[no-recall]`

召回片段格式（写入各 skill 产物的「背景 / 召回」节）：

```
[recall] tag:{匹配tag} ← {条目标题}({类型})：{摘要}
```

## 二、索引更新协议（生产端 · 各 skill 沉淀步）

沉淀 = 写一条索引到 KNOWLEDGE.md 对应 tag 节。

### 条目 schema

```
- [{title}]({path}) | {type} | {summary} | 链: {cross_link}
```

| 字段 | 约束 |
|---|---|
| title | 简短可读，≤20 字，含关键结论 |
| path | 相对 `~/.claude/decisions/` 或仓库根；跨仓单源资产（双仓权威分界：共享 skill `decisions/`、`postmortems/` 在本仓）允许 adas-assist 绝对路径指针，禁复制副本 |
| type | 枚举：adr / lifecycle / postmortem / capa / requirement / decision / reference（外参/调研沉底件的索引行专用，原文在本地不入库域，2026-09-27 沉淀治理轮登记）/ tombstone（冷藏项：判死理由+复活条件入摘要，产物清理后指针可指向存活载体；2026-09-16 战略日历轮登记）；新类型须先在此登记再使用，避免散落 |
| summary | 一句话 ≤30 字（阈值单源=knowledge-lifecycle.md 压缩原则），写结论而非描述；单一主题一行（原子化回写软门，2026-09-25 对标批：禁多主题打包行，写入前先 grep 同主题既有行防重复——先搜后写）；**bigram 约定（全出口适用，2026-09-26 自 knowledge-precipitation-protocol 并入）：须含 ≥2 个领域实词——中文 bigram（如「分库分表」「骨架优先」）或 ≥3 字符英文 token（如 `worktree`），禁全泛词（问题/处理/优化/机制等停用词）。依据：knowledge-recall 按实词交集计分（每命中 2 分，≥2 分才召回），全泛词 summary 沉淀即失效 |
| cross_link | `字段:目标ID`（协议定义的跨类型链），多目标用 `;` 分隔（`pending_adr:0003;0004`）；无则 `-`；主题软关联靠 tag 分节，不进此字段；**supersede 双向锚**（2026-09-25 起）：条目被取代时旧行不删，cross_link 追加 `superseded_by:{新产物slug}`，与新 ADR frontmatter `supersedes` 构成双向可溯边（ADR-M12 双向一致在索引层的镜像，消「删行即失锚」违证据链硬门），历史行触碰时惰性补齐不批量回写；登记日≠裁决生效日时 summary 前缀 `effective:YYYY-MM-DD`（bi-temporal 语义，回填类条目适用） |

### 沉淀规则

- 一条产物对应一条索引；运行时产物（verify-report / consensus.final）与经验汇总快照不产索引条目
- type 必须用上表枚举值，禁止自创
- 跨类型链只在协议定义时写（如 lifecycle→adr 用 `pending_adr`），禁止临时软关联
- 沉淀端：record(adr) / improve(postmortem/capa) / lifecycle / explore(requirement)，末步按本 schema 写
- **外参件召回面义务（2026-09-27 根因 R8）**：`decisions/external/` 外参沉底件结论蒸馏入 ADR/KNOWLEDGE 后，必须在 KNOWLEDGE 落 ≥1 条索引行（结论行即可，path 指外参件）——外参件无索引行=零召回=白调研；写侧不补即复发 R8
- **ADR 机械校验义务（同轮 R1-R5）**：ADR 落盘前跑 `scripts/adr-mdcheck.py`（四不变量：status 枚举/supersedes 闭环/命名判据/frontmatter 必备键），ERROR 归零才收口；发号用 `--next-id T` 取号禁自取

## 三、迁移

各 decision-* skill 的 Step0 / 沉淀步已改为引用本协议，替代各自手写规则（迁移完成，历史进度文件已随机制废弃清理）。

## 四、职责边界（沉淀前置判据）

> decision 族沉淀物（postmortem/adr 等）本就是抽象决策，与 design 族"防项目设计实现索引混入"场景不同；但职责边界对全族通用，沉淀前须过此判据。

- `~/.claude/decisions/KNOWLEDGE.md` = 决策产物唯一索引（ADR/postmortem/capa + 领域七节召回），主动检索；决策知识资产分层入 git（knowledge-doc-governance-consolidation：活跃 ADR + 索引入库，postmortems/experience/PENDING 仅本地）；harness skill 业务决策 → 对应 skill `decisions/` 子目录（精选条目经 data/* 节索引可达）
- `.claude/memory/`（项目级）与用户级 memory = 项目结论/场景约定 + 个人行为约束（详见下「三层 memory 契约」）
- 项目设计实现（表结构/分区策略/阈值/矩阵/特定流程等项目特定细节）→ 项目 REF/TECH 文档 + git，**不进 KNOWLEDGE.md**

> **路由登记义务（2026-09-13 实证）**：新增知识资产（skill/协议/ADR 域）落位时同步自查 README 是否需要补路由行——「新资产只长 skill 不长路由」会产生路由黑洞（历史实证：memory-governance 曾两图零登记）。

**沉淀前置判据**：候选条目能否脱离具体项目独立成立（跨项目可复用）？
- 能（通用选型判据/决策原则/方法论）→ 沉淀
- 否（指向 `project-docs/` 章节的项目实现索引，含项目特定标识符如表编号 T2/需求 ID RTQ-C1/项目表名）→ 归项目文档 + git，不沉淀

> design 族专属沉淀协议（_shared/knowledge-precipitation-protocol.md）已于 2026-09-26 删除：其服务对象 design 三族 skill 已退役，summary bigram 约定已并入上方 summary 字段行，沉淀前置判据由本节承载。

## 五、三层 memory 契约（memory-layer-governance）

| 层 | 位置 | 职责 |
|---|---|---|
| 平台 memory | `~/.claude/projects/<slug>/memory/` | 项目作用域教训结论层（结论+Why+How to apply，平台原生格式，不在 git） |
| 跨机偏好 | `~/.claude/memory/USER-PREFERENCES.md` | 跨机用户偏好层（不动） |
| 项目业务约定 | 项目 `.claude/memory/*.md` | 项目结论/场景约定（教训型笔记，入项目 git） |

桥接规则：
- memory 条目承载 ADR 结论时必须留 ADR 路径指针；ADR=决策论证层（Why+决策），memory=结论应用层（结论+How），KNOWLEDGE 索引=发现锚点层
- ADR 原文佚失时，memory 即事实载体（须标注承接关系）
- 平台 memory 召回锚点 = MEMORY.md 索引行 title+hook+frontmatter `trigger:` 拼接——治理压缩时承接条目钩子必须补入被并条目关键词（v3 承接锚点别名制：节名=原条目名+「承接原条目：…」前缀）
- 平台 memory 结构形态 v3 定版：3 件按 `type` 三分类（user 画像/feedback 授权/project 基建事实），新增条目先问能否并入既有件——单源 `adr/meta/knowledge-management-v3-memory-tiering-20260930`
- 重复分流五裁决（纯重复压指针/细节回灌 ADR 勘误/正文佚升格为事实载体/无重叠保留/同类按 type 合一）与回放验证口径（域分流（recall-replay.py，memory-governance/scripts/）：`domain_split`，责任域命中率=真实召回质量）：`adr/meta/memory-layer-governance.md` + v3 ADR；治理执行走 memory-governance skill
