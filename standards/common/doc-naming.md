# 文档命名与管理规范

> 跨类型文档（ADR / postmortem / capa / lifecycle / TECH / REF / standards / skill 文档）命名与生命周期管理的单一权威。各 skill 协议（adr-protocol 等）引用本文件，不复制条款。
> 确立载体：ADR doc-naming-refactor（2026-08-19，用户裁决：去数字、业务领域组织、同类分组；该 ADR 已废弃删除，裁决由本文件承载，原件见 git 历史）。

## 一、命名规范

| 规则 | 说明 |
|------|------|
| 语义 kebab，**禁数字编号** | 文件名 = 业务语义的小写连字符 slug（`skill-evolution-spiral-loop.md`）；不使用 NNNN 序号前缀——编号无语义且引入单调递增/不复用等治理负担 |
| 目录即业务域 | 分类靠目录承载（ADR 库 meta/data 双域 + postmortems/；skill 本地 `decisions/` 子目录（本地不进版本控制）与 `project-docs/common/` 同规）；文件名不再重复目录词（`decisions/fixer-public-agent.md` 而非 `decisions/design-fixer-*.md`）——域词属专名（agentos-loop）或主题核心词（删后语义泛化）时保留 |
| slug 全局唯一 | 新建时 grep 查重；撞名换更精确语义词重试（≤3 次） |
| 文件名即唯一标识 | frontmatter 不设 id 字段；互链/引用（supersedes/superseded_by/related_*/postmortem_id/正文引用）一律用 slug |
| 单一最终版 | 禁文件名版本后缀（.vN）——版本走 frontmatter，项目文档历史靠 git（[knowledge-doc-governance-consolidation](../../decisions/adr/meta/knowledge-doc-governance-consolidation.md)） |

## 二、文档管理三则

| 动作 | 规则 |
|------|------|
| **重构**（压缩/精简） | 压缩不改决策语义、不改语义名、不断 supersedes 链——git 历史保全量；细节下沉 skill 条款不留在决策文档 |
| **合并** | 并入方正文/备注记录被并文档的 slug 与合并原因；被并方删除（git 历史可溯）；不保留空壳文件占位 |
| **取代** | 完整取代：新 ADR 写 `Supersedes <slug>` + 旧 ADR 改 `Superseded by <slug>` 双向；局部取代（仅某 Decision）：旧 ADR 保持 Accepted + 正文备注。被取代且零活跃引用 → 物理删除（历史靠 git，无 archive 堆叠层） |

## 三、生命周期与治理（引用既有机制，不重复）

- 四层分层（L3 长期 / L2 中期 / L1 短期 / L0 临时）与流动规则：`knowledge-lifecycle.md`
- ADR 库治理三板斧（压缩/废弃删除/分组复核）与阈值：decision-record SKILL.md「ADR 库治理」
- 自动信号：session-review 的 adr-governance-overdue / adr-progression-review / adr-consistency（frontmatter/索引/死链一致性）+ repo-hygiene（版本管理边界三分类检测）

## 四、跨域量尺码消歧（L 码全局对表，2026-09-26 立）

> 五套 L 码各域自治、同名不同义且方向相反（L2 在安全域最高、在知识域仅中期）——引用 L 码时**必须带域名前缀**（如「安全 L2」「知识 L3」），裸 L 码视为未消歧表述。本表为唯一全局对账处，新域量尺码立码时同批登记。

| 域 | 码尺 | 单源 |
|---|---|---|
| 安全域 | L0 公开 / L1 蒸馏 / L2 仅本地（L2 最高、禁出网） | security-protocol.md |
| 知识域 | L0 临时 / L1 短期 / L2 中期 / L3 长期（L3 最高） | knowledge-lifecycle.md |
| skill 资产域 | L0 交付层/参考层（最高价值）/ L1 源层 / L2 构建层 | skill-design.md |
| 进化分档域 | L1 轻量 / L2 中等 / L3 重大 | evolution-discipline.md |
| 任务档位域 | L1 quick / L2 standard / L3-L4 full/跨模块 | model-governance.md §5（未包含） |

- 第三档命名：通用语境=`full`；`deep` 仅为主控收尾检查与 flow-prd-design 的**用户面特化命名**（同义登记在案，非漂移——二者对外档位名不改，对内语义即 full 档）。
