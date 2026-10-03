# 高价值概念注册表（concept-registry，2026-09-25 C1-C4 四路深探收口）

> 受控词表：只收**能落成设计规则**的科学概念，每条=操作化定义≤50字+本仓消费点+一手锚。
> 收录门：定义可操作+映射点具体+锚 verified；弱映射淘汰先例=Cromwell 法则（C2 自裁）。
> 消费点三处：①检索 query 构造（alt 术语入 query 提价值密度）②判级/聚合规则（量尺纪律）③台账分类词汇。

## 知识组织（C1）

| 概念 | 操作化定义 | 本仓消费点 | 锚 |
|---|---|---|---|
| SKOS 三层标签 | pref 唯一显名/alt 收同义缩写/hidden 只进索引不展示，三层互斥 | KNOWLEDGE 行与 query 构造的别名槽规则；未来 lint 硬校验 | w3.org/TR/skos-primer §2.2 |
| 分面分类法 | 互斥穷尽正交轴组合代替枚举树，任意轴切片 | 索引膨胀时的轴化改造判据（域×类型×状态）；轴需先裁互斥 | en.wikipedia.org/wiki/Faceted_classification |
| 形式概念分析 FCA | 对象×属性矩阵经 Galois 闭包成概念格，孤儿标签=不可召回 | 索引质量审计的机械判据（PENDING 宿主） | FCA, Wille 1981 |
| Cranfield 实验 | recall/precision 权衡+「系统细节影响大于方法论」的 A/B 判卷原貌 | 本仓所有召回 A/B 的方法论背书 | Cleverdon 1962 |

## 推理与判级（C2）

| 概念 | 操作化定义 | 本仓消费点 | 锚 |
|---|---|---|---|
| Pearl 因果之梯 | 关联/干预/反事实三层不可互推，高层 claim 须高层证据 | conclusion-matrix 降档列：「导致」类 claim 证据仅相关观察→禁高置信 | arXiv:2503.11870, 2405.07373 |
| 信号检测论 SDT | 辨别力 d′ 与判断标准 c 独立；动阈值换配比不换能力 | 召回实验强制记 2×2 四格，先问 d′ 还是 c（L25 判卷分离同构） | arXiv:2603.14893 |
| Stevens 测量层次 | nominal 计数/ordinal 比序/interval 才可算术平均 | 判级字段标量尺：GRADE/verified=ordinal 禁均值禁百分比差；F1=nominal 合法 | arXiv:2101.02668, 2212.11735 |
| Toulmin 论证模型 | claim/data/warrant/qualifier/rebuttal 五件套 | conclusion-matrix 列设计的学术原型（提名已收锚 1708.01425） | arXiv:1708.01425 |

## 数据与信息（C3）

| 概念 | 操作化定义 | 本仓消费点 | 锚 |
|---|---|---|---|
| DIKW 批判 | 层级间无一致转换判据；「升层」不构成论证——data≠信息的量变 | 禁「原始数据→结论→教训」管道话术自证，教训须独立论证 | Frrické 2009, DOI 10.1177/0165551508094050 |
| PROV 三角色 | Entity+Activity(时序)+Agent(负责者)+derivation 链 | findings 台账记账模式：finding/检索过程/session 三角色可机械核验 | W3C PROV-DM REC 2013 |
| PMI vs TF-IDF | TF 量频次 PMI 量独立性偏离；纯 TF 把高频平庸词当强关联 | 召回扩展/相似聚合先归一 PMI 再排序+频次地板 | Church & Hanks 1990, ACL J90-1003 |
| FAIR 原则 | Findable/Accessible/Interoperable/Reusable 判据 F1-F15 | findings 台账可发现性/可复用性自检清单 | go-fair.org |

## LLM 知识体系（C4）

| 概念 | 操作化定义 | 本仓消费点 | 锚 |
|---|---|---|---|
| 连锁失误 ripple | 点改单条事实≠多跳邻域同步更新 | 资产变更必须回扫引用方（ADR/KNOWLEDGE 交叉引用登记影响域） | arXiv:2307.12976, 2202.05262, 2210.07229 |
| faithfulness/factuality | 违反给定上下文 vs 违反可验证世界知识，二者可 trade-off | 拒纳台账分类词汇两栏分立禁混用 | arXiv:2311.05232, 2404.00216 |
| 校准/ECE | 置信与正确率对齐度；RLHF 系统性过自信，推理预算升高加剧 | 模型自报置信禁作唯一判据；分档独立理论依据 | arXiv:2410.09724, 2606.11211 |
| 涌现度量伪影 | 「能力涌现」可能是离散不可分指标的测量假象 | 能力声明先查度量口径 | arXiv:2304.15004（ID 勘误：非 15076） |
| 外置世界模型 | LLM 隐式关系建模分布外崩溃，须外置显式结构 | 知识关系不依赖模型隐式记忆，靠仓内显式链接 | arXiv:2406.03689, 2409.12278 |

## 全局消歧：L 码与第三档命名（2026-09-26 F16+F18 落地，五套量尺一次收口）

> L 码为**域内局部编码**，跨域不同义；引用时必须带域名（如「security L2」而非裸「L2」）。全局消歧唯一落点=本节，新增 L 量尺须先在此登记。

| 域 | 量尺 | 方向 | 单源 |
|---|---|---|---|
| 安全分级（数据出网面） | L0 公开 / L1 蒸馏 / L2 仅本地（最高） | L2 顶 | standards/security-protocol.md |
| 知识生命周期 | L0 临时 / L1 短期 / L2 中期 / L3 长期（最高） | L3 顶 | standards/common/knowledge-lifecycle.md |
| skill 资产层 | L0 交付层/参考层（最高价值产物）/ L1 源层 / L2 构建层 | L0 顶 | standards/skill-design.md（未包含） |
| 智能分档（处置强度） | L1 轻量 / L2 中等 / L3 重大 | L3 顶 | skills/_shared/evolution-discipline.md |
| 任务档位→effort | quick/L1 → standard/L2 → full/L3 → 跨模块/L4 | L4 顶 | standards/model-governance.md §5（未包含） |

**full/deep 消歧**：`full` =通用第三档名（execution-tiers/assessment-protocol/model-governance 均未包含）；`deep` = 主控收尾检查与 flow-prd-design 的**用户面特化命名**（触发路由表未包含），语义同 full 档，属登记特化非漂移——两 skill 文档内用 deep，协议件内用 full，禁混写。

## 使用纪律

1. query 增强只加 **alt 术语**（缩写/同义/中英），禁堆泛词——PMI 规则：低频精确词>高频平庸词。
2. 判级聚合走量尺纪律：ordinal 字段只报众数/中位+序比较。
3. 新概念入表走收录门三件套，弱映射即淘汰（先例在案）；待复试提名挂 PENDING（Codd 范式/Campbell 效度/溯因 IBE/schema matching）。
4. 本文为概念单源；消费方（knowledge-protocol 及各调研/探索 skill）只引不复制。
