# 自修改纪律（公共 canonical）

> 所有"自修改型"工作（改 skill / 规则 / 配置 / 自进化）的共同纪律。[USER-PREFERENCES.md](../../memory/USER-PREFERENCES.md)「自修改克制」为精炼总览（CLAUDE.md 2026-09-26 重写后总览迁此，T114-F4 断链修复），本文件为完整门控；含任务级智能分档总则与根因影响面前置。skill-evolution 接入条件见其 `references/gate-rules.md §1`，不在此重复。

## 五条原则

1. **不为假设建机制**：≥2 次真实共性重现才动手；单次偶发 / 主观无共识 / 源问题不动
2. **提议 vs 执行分离**：信号可自动产建议清单，但改文件须用户确认；禁自动改不禁自动提议
3. **默认不动**：自修改是例外不是常态；稳定优先于完美；不满足门槛即拒并记理由
4. **效果导向 / 不为设计而设计**：机制存在须可验证效果；瘦身保留真拦截缺陷的环节，去掉形式完整但无实际价值的环节
5. **指标不强跑**：baseline 待真实使用自然回填，不为拿单个数值强跑完整流程

## 智能分档总则（宪法 #5「多级判断」落地路由）

> 任务 / 改动执行前先定档。两轴：**执行模式**（轻量直改 / 骨架先行 / 完整流程）× **验证强度**（自审+复验 / 单轮审查 / 多轮对抗取优）。本总则只做「任务→机制」路由，不改写既有判据的档位定义与命名（各领域仍为权威——信号消化三档真值=`signal-tiers.json`，改名 JSON+文档两处同改）。

| 档 | 判定（缺省打分器=主控按影响范围×可逆性±数据支持自评；分歧走 devils-panel） | 执行模式 | 验证强度 |
|----|----|----|----|
| L1 轻量 | 单点改动 / 影响单文件 / 可回滚 / 风险评级低 | 轻量直改 | 主控自审 + 精确 grep 复验 |
| L2 中等 | 单 skill 规则 / 协议局部修改 / 范围可控 | 骨架先行（§骨架优先） | 单轮审查（主控红队自审 单轮快审）+ 根因影响面轻量（见下节） |
| L3 重大 | 跨 skill 协议 / 核心纪律 / 不可逆 / 体系架构调整 | 完整流程 | 多轮对抗取优：主控多轮正反两臂对抗 / 沙盘推衍（`_shared/analysis-methodology.md §沙盘推衍`，每视角必走 ≥1 真实历史场景）。注记（2026-09-27）：L3 候选须 ≥2 独立方案（PCF 承载），**落选候选落 PENDING 或 ADR Alternatives 节存档可对比**（非 git 比喻）；体系档 High 改动单 commit 提交+ADR 记 hash 作回退锚；择优判据=轮首预登记指标（前置②同款，延伸到 /evolve 轮） |

- **多轮验证取优仅 L3**：L2 单轮、L1 自审——不为小改动上最重模式，也不为省事给大改动降档
- **资产管理场景映射行**（2026-09-27 版本发布纪律批，ADR version-release-discipline；码引用带「进化分档」前缀，doc-naming 只留指针）：措辞类=L1 直改｜索引行/路由行=L1 同笔两处｜目录拆分/文件迁移=L2（断链扫描+MAP/README 同步）｜常规定版（快照+tag，机械）=L2｜带行为变更集的定版=L3（完整流程+效果基线对照行）
- 既有档位机制（主控收尾检查梯度 / 信号消化三档 / 纠偏三档 / §风险评级）按各自场景使用，本表只提供任务入口选档路由

## 根因与影响面前置（L2+ 改动必走，L1 豁免）

> 自进化改动动手前四步：**析根因 → 摸影响面 → 确认 → 按根因推进**。根因方法论引用 decision-improve（简单→5Why 缺依据标[假设]；复杂→鱼骨六维），仅引用不转交（skill 进化归本纪律管辖）。

1. **根因归因**：信号 / 退化数据先回答「为什么发生」，再回答「改哪里」；表面症状不得直接成为改动方案
2. **影响面全量排查**：被改条款 / 信号类型 / 函数名的全仓引用点（`_shared` 引用矩阵 / session-start.py 硬编码集合 / hooks「两处同改」项）精确 grep，可下放 sonnet agent 但回传须含**命令原文+命中清单**（可复验）；语义影响面判断归主控，调研结论须交叉验证
3. **确认门**：根因链 + 影响点清单 AskUserQuestion 确认（按根因改 / 扩大影响面一并处理 / 中止）后推进；每处改动可追溯至根因
4. **L1 豁免**：一句话根因 + 影响点枚举，随既有门控一并确认，不单独提问

> 项目代码域（业务代码/公共资产改动）的同构协议见 `_shared/impact-exploration.md`，两域各为 canonical，互不吞并。

## 骨架优先（任务与自进化执行准则）

> 覆盖日常开发任务与自进化轮次（含智能化自我进化）。CLAUDE.md「骨架优先」为精炼总览，本节为完整版。

1. **不过度设计，实用优先**：重点骨架（核心流程/节点）先实现，细节后续补
2. **任务编排**：罗列任务清单 → 拆解 → 规划 → 并行执行探索 → 关注重点 → 交付
3. **干扰即清（三分法）**：细节干扰（零使用机制/形式化环节/历史归档误判为活性依赖）先清理——真零依赖→删；扩展能力→降级保留；真问题但高风险→登记不动。**清理决策须主控精确 grep 复核**（探索 agent 的行数与依赖面会失真）
4. **自进化轮次同守**：每轮 = 真实信号 → 分析 → 改进 → 验证；数据驱动（reflex-hooks.jsonl / invocations 真实运行数据，不造数据）；机制建后无效果即回退
   - **评估快照门**：skill/协议行为面改动前后各跑一次 recall selftest 快照并附对照（meta-regression 壳未包含，跑 knowledge-recall --selftest）——outcome-based grading 外参（anthropic evals），改前无快照=改动无效留痕。豁免：L1 纯注释/文档措辞级改动（零行为面、零规则增删、零锚点变动）免快照，判定理由随提交留痕（2026-09-25 finish-check Reviewer A 建议，托管采纳）
5. **两轮交付**（多节点产物 / 机制改动适用；单点小改不强制）：骨架轮产结构（验收=节点可走通、门控可判）→ 确认后进填充轮，细节由真实使用信号驱动

> 术语注：本节「骨架」专指交付节奏；skill 执行形态一律表述为「主 agent 交互式执行」（全仓消歧见 `decisions/adr/meta/smart-grading-tiering-consolidation.md`）

## 触发条件（仅以下情况才「提议」，非每次执行）

- 用户明确要求「评估 / 进化 / 优化」
- 主 agent 发现**明确退化**（metrics 较上次降 ≥ |regress_delta|，或新增 P0 级问题）
- 多产物累积**共性真实问题**（≥2 次重现）

> 触发的是「提议」，「执行」仍须用户确认（原则 2）。

## 「不动」清单

| # | 场景 | 理由 |
|---|------|------|
| 1 | 机械指标已 100% 时，不为 AI 项强行优化 | 部分问题可能是输入固有，无法靠 skill 消除 |
| 2 | metrics 已达 threshold，禁止「为优化而优化」 | 除非解决特定 P0 |
| 3 | metrics 远超 threshold，无实质优化空间 | 稳定优先 |
| 4 | 输入固有的模糊/矛盾，标记「源问题」 | 不纳入进化目标 |
| 5 | 单次偶发问题（非 ≥2 次重现）不动 | 样本不足（原则 1） |
| 6 | AI 项评估不确定性高（主观、无共识）不动 | 无共识不优化 |
| 7 | 改动风险 > 收益（动核心纪律/协议，收益未达门槛）不动 | 风险可控优先（评级见下） |

## 风险评级（第 7 条量化依据）

| 等级 | 判定 | 处置 |
|------|------|------|
| 低 | 仅改 worker 纪律 / 模板补充，不动审查协议与评分公式 | 允许，正常走门控 |
| 中 | 改审查规则 / 子检查项，可能影响 metrics 基线 | 需回归验证 metrics 不降 |
| 高 | 动核心纪律 / 评分公式 / 门控阈值，影响所有产物 | 默认不动，除非收益达量化门槛 |

## 信号消化分级（PENDING 积压自动消化授权）

> 用户授权「低风险自动做、高风险才问」；中风险档=待办型信号不每次会话问，开局仅汇报、挂周评估批量确认一次。判定规则：low/mid 集合机器真值=`signal-tiers.json`（仅列 low/mid；未列类型=高档——发射面限 session-review，session-start 自产信号见各行标注；读取失败回退空集=全按高档），下表为人类可读对照；**新增信号类型须 JSON 与下表两处同改**。

### 进化周期三档（cadence，数值单源 `io-budgets.evolution_cadence`，两处同改禁令）

| 档 | 周期 | 内容 | 产物/消费 |
|---|------|------|----------|
| 日档（小） | 每日 22:35 weekly-eval launchd 串联第二程（daily-archive.py）承载（2026-09-26 勘误：原「03 点独立 cron」不存在，周期任务唯一读口=AGENTOS-MAP §七），零模型 | 心跳扫描：PENDING 计数+超线+联审到期；机械归档项（轮转核查/断链 grep/.state 清理提示）无条件执行。模型小任务不进日档：模型项挂周批 low 档；「半夜整理归档」以纯脚本形态承载（2026-09-27），模型窗立项须先 decision-record 翻案本行+≥2 次真实积压证据 | `.build/evolution-daily.log` 一行/日，仅落盘零注入 |
| 周档（大） | 每周日锚 | 周评估三指标+战略对账+批次统筹消化（low 自动/mid 批量确认；High 一律落 PENDING 待用户确认，禁自动改）。**进化批待办**（2026-09-27）：超线信号>0 时 weekly-eval.py 在报告追加「进化批待办」行（带周期锚日期），执行者=下次会话主控消费周报时按托管语义跑 `/evolve all`（L2）；去重走 `evolution-batch.marker`（消费即重置，joint-review.marker 同构），防重复跑；与后台分析段分工=分析段诊断、/evolve all 消化动作，同一信号不双消费 | weekly-eval-report.md；主控消化后 touch marker |
| 决策档 | 14 天窗口 | 高风险信号攒批一次 AskUser（批次门一次 multiSelect） | 三入口（2026-09-27 增补第三）：session-start 指针 + 用户指令 + `/evolve 决策` 手动拉起（同一 multiSelect 门，不建第二确认面；ADR evolution-cadence-tiers 追加节登记） |
| 外参节律 | 周批（last-external-action marker 到期判定，「本周期」=自 marker 日期起算） | `/evolve 状态` 资讯扫描为唯一轻量通道；到期未执行时零模型脚本仅在周报加「外参扫描待办」行，扫描由下次会话主控执行（low 档机械入 PENDING，过外参准入（协议本仓未包含，主控按证据链硬门自审））；条目攒 ≥5 条或命中深探触发词升 §9.2 深探 | marker+PENDING 外参条目；深探产物按准入落库 |

部门联审双轨：用户触发词「部门联审/交叉审查」即跑 + `joint_review_window_days`（14 天）到期自动兜底；**任何一次执行后 `weekly-eval.py --joint-review` 重置锚**，与周批 marker 分离。

### 部门执行流程映射（条款→周期宿主→验收）

> 每条核心条款钉周期宿主与验收（ADR 锚 organization-evolution-consolidated「无宿主条款不得入协议」）；**新增部门条款必须同笔在本表登记行**。

| 部门 | 核心条款 | 周期宿主（自动触发点） | 产物 | 验收信号 |
|---|---|---|---|---|
| 模型治理部 | §5 档位×effort 映射+调用点登记；self_evolution_round 预算 | 周评估「消耗审计对照」行 | 超线 ⚠ 行 | spawn 总量/审计类占比入报告 |
| 运行治理部 IO 组 | io-budgets 数值单源+唯一写者 | 联审固定议程（I/O 合规线）+ io-protocol 文字零数值纪律 | 联审落点三分记录 | 双写漂移=0（grep 抽查） |
| 战略评估部 | 基线先行+measured 回填义务 | 周评估 baseline-gap 行 | ⚠ 行→effect-governance 处置 | measured=null 清零 |
| 知识进化部 | knowledge-protocol schema+候选池出口 | 周评估 evolution-pool 行+resolved 事件 | 待验证计数行 | pending_validation 清零或裁决 |
| 进化引擎 | 三档 cadence+批次统筹 | daily log（日）/周日锚（周）/决策批 14 天 | evolution-daily.log+周报 | 日档心跳连续；⚠ 处置见下 |
| 全部门（复盘线） | 失败/翻案/误判/战役收尾须产复盘，frontmatter severity+category 必填（category=capa-protocol 匹配键） | ①session-review verify 非 pass ③联审复盘议程 | `postmortems/*-retrospective.md`（仅本地）+EVOLUTION/ADR 指针 | 失败事件 schema 复盘覆盖率；同款误判不复发 |
| 全部门 | **⚠ 处置义务**：周报每条 ⚠ 须「当场处置」或「落 PENDING 挂档」，禁只读不落；**消费 SLA**：周期信号须具名消费者（默认=effect-governance）+消费时限 2 周期+连续 2 周期零消费→升联审议程+信号冻结注销 | 周评估注入 | PENDING 条目或当场修复 | 同款 ⚠ 不复发（复发≥2 次→联审）；SLA 对账：零消费信号数=0 |
| 进化引擎（画像试点） | 输入习惯画像探针：周批主控直读近 2 天输入（session-search 未包含）→≤3 行画像+机械映射（高频方向=本轮首选方向；新约束命中 PENDING=升档）；观察期 2 周期只出画像不动决策；**不写 expect**（判据=主控逐轮记「画像采纳=是/否+实际选向」入 daily log），试点 2 周期无效即撤（2026-09-27 立，ADR evolution-cadence-tiers 追加节） | 周档（/evolve all 前置步；单独触发=`/evolve 画像`） | 画像 ≤3 行+daily log 采纳行 | 采纳率读数（只报不判至观察期满） |
| 进化引擎（外参线） | 外参节律见三档表「外参节律」行（本行不复制）；自审路由单源=commands/evolve.md `自审` 行 | 周批 last-external-action marker 到期判定 | PENDING 外参条目+审计产物 | 外参条目消费率；审计产物计数非零（周评估 MC2 S①） |

| 信号 | 级别 | 消化方式 |
|------|------|---------|
| baseline-gap（产物分回填 baseline） | 低 | 主控自动消化，仅汇报结果 |
| stale-eval（skill-evolution 评估） | 低 | 同上（只读） |
| dead-skill（lifecycle 只读核验） | 低 | 同上（判采集漏报/真死，不删） |
| cold-skill（低频 1-4 次无进化无验证） | 低 | 同上（只读分析，处置另行确认） |
| hot-skill（高频 ≥30 次从未进化） | 低 | 同上 |
| adr-progression-review（ADR 30 天无变更，层级累进复核） | 低 | 同上（汇报：晋升 L3/维持/归档三选；动作另行确认） |
| adr-consistency（frontmatter/索引/死链漂移） | 低 | 同上（机械回填；改语义→升级）；KNOWLEDGE 缺条目子类=提案用户确认才改，主控不自动回填 |
| map-count-drift（地图计数 vs 目录实测漂移） | 低 | 同上（机械回填仅汇报；口径二义升级人工；计数锚=目录 `find|wc`） |
| tracked-junk / untracked-report（垃圾已版本记录/报告未 ignore） | 低 | 同上（只读建议 rm --cached/补 ignore；执行另行确认） |
| calibration-tier-quality（主控收尾档位分布；real-run=免检路径分布单列） | 低 | 同上（只报分布+疑点；升降档留用户裁决；样本 verdicts ≥5） |
| calibration-recall-quality（召回率/打扰度越参考线才产） | 低 | 同上（校准召回词/阈值另行确认；样本各 hook ≥10 行） |
| weekly-eval-due（marker 缺失或早于周日锚；session-start 注入） | 低 | 读预产出报告结论（禁实时 jq；后台分析段消化时复核勿盲采）+批量确认+抽样复核，只读汇报；完成后 touch weekly-eval.marker |
| adr-governance-overdue（ADR 库超限：全局 >24 / 单域 >18） | 中 | 开局仅汇报挂周评估；周评估批量确认；已处理随下次扫描消除 |
| skill-file-oversize（skill references/agents 单文件超 400 行；SKILL.md 主文件另有 ≤150 行阈值；skill-design.md 本仓未包含，阈值以本行登记值为口径） | 中 | 同上（拆分/瘦身评估可判不动；处置经用户确认，挂周评估消化） |
| strategy-review-due（阈值单源=_shared/signal-tiers.json `strategy_review`〔双源同改〕；weekly-eval 发射，分母随行打印） | 中 | 同上（超线转 decision-lifecycle：压缩/归档/分组复核，蓝图 §四默认拒绝） |
| experience-summary-due（经验汇总到期） | 中 | 同上（不紧急待办） |
| calibration-skill-triggers（高频触发词未在 description / 高频失败） | 中 | 同上（改 description 须用户确认；样本调用 ≥10 次、词频 ≥3 次） |
| skill-changed-unsynced（基准=EVOLUTION/skill-local ADR/元层 adr 取最新，见 session-review.py `_skill_sync_floor`） | 高 | AskUserQuestion 确认后补 EVOLUTION 或转 decision-record（行为真值=session-start.py） |
| dataset-orphan / dataset-stale（红蓝数据集条目失联/基线超期） | 高 | AskUserQuestion 确认后才动（删条目/重跑 verify） |
| verify 非 pass / must_fix>0 | 高 | AskUserQuestion 确认后才动（修业务代码） |
| evolution verdict 非持平 | 高 | 同上（下游涉改 skill） |

升级规则：低风险消化过程中若需改 skill 逻辑 / 删文件 / 修业务代码 → 立即升级为高风险，先问再做。

### 纠偏三档（螺旋闭环纠偏判定）

reflex-check 检查3 按客观信号量化三档，与上表分级同构：

- **轻**（同类纠正 1 次）：Skill 不变，仅计数留痕（不触发演化动作，防过度优化）
- **中**（同类 2 次）：进入观察——提醒沉淀建议+PENDING 积压+狼来了抑制；同类 ≥3 次达重档
- **重**（同类 3 次或显式拒绝）：提炼 Lesson 当场沉淀（条款级→EVOLUTION.md / 机制级→decision-record ADR），Evolution Record 自动落盘 `.state/evolution-pool/`（仅落盘不入库）。**沉淀准入门（2026-09-27 启示②立项，外参锚=记忆自投毒定理级反例 deepexplore-possibility-20260927）**：沉淀前必须核「触发源是否用户原话」——reflex-check 词表匹配会把主控引用的被审资产原文/执行体技术文本误判为用户纠偏（L42/L55 两例实证），非用户原话触发源禁沉淀，改记 negative 观察行。**失败证据断言门（2026-09-28 T100 吸收 2607.13083 Phantom）**：机制级沉淀/改进提案须附真实失败证据锚（file:line、实存事件 id 或日志行）——无锚=假设性提案禁升格，防「为假设建机制」旁路。
- **教训沉淀前三步冲突裁决**（Mem0 成对裁决+Zep 失效不删外参吸收，2026-09-25）：沉淀前 ① grep evolution-pool 相似旧条目（关键词交集 ≥2）；② 成对裁决 ADD（无冲突）/ SUPERSEDE（旧条目尾加标记 `(superseded by <新条目主题> <日期>)`，knowledge-recall 按行级 `superseded` 关键词过滤，物理删禁止）/ NOOP（重复则 DOWNVOTE 计数 +1 不新增行）；③ 新条目行首元信息带 valid_from 日期——裁决只标记不删除（标记过滤现生效于知识索引源；lessons 行级源待接线，见 recall-regression.json `_cr_note`；本行 2026-09-27 环节轮去重：原 :152/:153 逐字节双写已删一处）

## .build 归口契约与持久资产白名单（campaign-20260916 归口件，2026-09-16；2026-09-27 T114 升 ## 独立节）

> **契约一句话**：`.build`=可再生临时区，**契约资产不得以 .build 为唯一落盘地**；白名单+清理台账使「蒸发」变「可观测事件」（ADR 锚=campaign-20260916 归口件）。

**持久资产白名单**：单源=cleanup-builds.py `REPO_BUILD_WHITELIST`（机械单源；2026-09-27 T114 收敛——原 prose 复制清单与代码常量已实测漂移，本节不再复制清单，新增资产改代码常量一处即可）；双宿主登记（写者+读者）义务不变。历史登记背景：进化批/reflex-pending/外参节律各 marker（周期锚，写者=daily-archive.py/weekly-eval.py/主控）｜日档/周报/pending-history/reflex 运行数据｜`locks/`。

**清理台账**：`~/.claude/.build/cleanup-ledger.jsonl` append-only，行格式 `{date,target,reason,actor}`——任何脚本删除动作追加一行（cleanup-builds.py 已内置）；读者=session-review `asset-vanished` 扫描（白名单资产消失或 mtime 回跳→PENDING 一行）。

## 周评估（反射层效果，数据源 `.claude/.build/reflex-hooks.jsonl`）

> 原则 4「效果导向」的落地动作：反射层按周用真实数据评估，不达标按切片回滚，不为拿数值强跑。
>
> **触发**：cron 每日跑 `skill-evolution/scripts/weekly-eval.py`（周日锚到期才重算；指标计算零模型；超线 ⚠ 才触发后台分析段）产出 `.claude/.build/weekly-eval-report.md`；session-start 到期注入报告结论。节流频率裁决单源=model-governance §3.7；用户豁免=`weekly-eval.py --force`（旁路 marker 且不 touch）。主控**禁实时 jq 计算**，只读结论做下方处置；完成后 touch marker 复位。指标口径变更须 weekly-eval.py 与下表两处同改。手工测试 session_id 必须 `test-` 前缀（混入分母会使召回率/打扰度全部失真）。

| 指标 | 口径 | 参考线 |
|---|---|---|
| 召回率 | knowledge-recall 的 match / 总行数（排除 test- session） | 参考线数值单源 io-budgets.weekly_eval_refs |
| block 打扰度 | reflex-correction 的 block-heavy / (block-heavy+light)（2026-09-27 T117 口径迁移：reflex-check 实流仅产 exempt-skip，判定事件挂 reflex-correction 名下；exempt-skip 与 reflex-output 不进分母） | 同上单源 |
| 澄清转化 | 窗口内 reflex-clarify resolved 事件 / block 次数（reflex-check 检测澄清+窗口内 ADR 沉淀落 resolved） | 同上单源 |

主控处置清单（零样本指标不判定，报告已印分母）：
- **异常指标**：按切片排查 + 抽样复核（抽 3 个 match 会话 transcript 判召回采纳——采纳无自动记录，transcript 即证据）
- **候选池消化**：`.state/evolution-pool/evolution-records.jsonl` 过滤 `evolution_action.status == "pending_validation"`（嵌套路径非顶层），逐条闭环 / 升级（转 skill-evolution）/ 作废（置 rejected_no_signal）即改同路径 status；候选池是待消化队列非归档；`data_routing=DPO` 终点未建不预建
- **中风险待办批量确认**：PENDING 中档信号按 skill 分组 multiSelect ≤4/批（现在处理/继续挂/标记已处理）；已处理的随后续扫描自然消除

## 效果验证协议（战略评估部底层条款，canonical）

> 适用：一切带 expect 的优化/治理改动。机器可执行四条；回填走周评估节拍。

1. **基线先行**：改动落地前在 token-baseline.json 登记 expect+**可算度量口径**——测不出口径的不许写 expect（写「观察期」并记理由）。
2. **回填义务**：落地后 1 个周评估周期内把实测写回 measured 字段（verify-report / finish-verdicts 固定字段或 baseline JSON）；到期未回填由 weekly-eval 对账行发射 baseline-gap（生产者=weekly-eval 对账步骤）。机械回填走 `weekly-eval.py --backfill id=value`——只写 measured 原始值，expect/回退判定留人工。
3. **回退触发**：实测 < expect×50%，或效果指标越参考线，或瘦身后 must-fix 拦截记录下降 → 适用回退三分法并留 EVOLUTION/ADR 一行。
4. **留痕归一**：里程碑验证结论一行入 EVOLUTION.md/ADR（正文留 target_dir），供 skill-changed-unsynced 对账。

审计入口：effect-governance：measured=null 清单 / 基线对账 / 回退判定，分母打印。审计入口，另立口径；expect/measured/回退字段定义以本节为唯一权威（P0-5 引用口径统一）。

## 量化门槛（须同时满足才执行）

- **真实共性**：问题 ≥2 次重现（非偶发）
- **量化收益**：metrics 提升 ≥ evolve_delta（各 skill 自定义，如产物分 ≥3 / 覆盖率 ≥5%）
- **风险可控**：不动核心纪律 / 不引入新 must-fix 问题
- **默认拒绝**：不满足 → 不执行，记理由

## 效果导向验证（原则 4 落地）

瘦身 / 精简 / 去机制后，须验证「效果不降」：

- 保留的环节仍能 catch 它该 catch 的缺陷（对比瘦身前后 must-fix 拦截记录）
- 若某环节去掉后缺陷漏过（效果不保），按原则 4 **回退该环节**——不为精简而精简
- 验证方式：worktree 隔离跑真实场景 + 对比产物质量分 / 拦截记录，记入对应 EVOLUTION.md

## 文档卫生（沉淀落位契约）

主文档（SKILL.md / standards / 工作 references）只承载**规则本体**，过程性内容按类型归拢：

| 内容 | 归宿 | 主文档写法 |
|------|------|-----------|
| 版本记录 / 进化叙事 / 轮次数字 | 对应 skill `EVOLUTION.md` | 禁留（「N 轮实证」类表述不入主文档） |
| 教训现象与根因细节 | pitfalls 类知识条目 / ADR | 一句规则 + 「详见 #N」指针 |
| 机制/写法规范 | 单一权威源文件（如 responsive-rules） | 其他文件引用，禁双写 |
| 日期戳 | 仅 EVOLUTION / ADR frontmatter | 知识条目标题不带日期 |
| 归档 | ADR 废弃 → `archive/`（Deprecated + 索引登记） | 活跃区只留生效决策 |

- 收尾检查按本表核对：主文档出现过程叙事即 P2 清理项
- 判据：删掉这段后规则是否仍可执行——可执行则删（叙事），不可执行则留（规则）

## 归档索引（2026-09-25 压缩战役）

- 资产迁移与全局区盘点为独立批次，批内资产留原地｜原叙事见 git 历史 2026-09-16 附近（campaign-20260916 归口件批次注记）
- 周评估触发「已异步化」沿革本仓未包含，按现行协议执行

## PENDING 登记-消化对账试点（2026-09-26 R3 定稿，pcf-critic 8 漏洞修订版；试点期 2 周评估窗，回滚=本节 git revert+快照 .state/pending-snapshot-20260926-r3.md）

> 基线读数：消化率 25%（7d 新增 10/消化 2.5，R2 B 臂实测）。试点目标：消化率 ≥50%（**分母=信号总量**（session-review 扫描数），非登记数——防压分母 Goodhart）；评估并入 weekly-eval 对账表加一列，不另起炉灶。

1. **登记 SKU（D1'）**：人工登记 T 行须含「消费判据=可 grep 的 done 状态词+具名**已存在**读点位文件」；通道指向不存在读点位=登记不合格。session-review.py 脚本自产行豁免（程序化生成模板化判据，两套合格标准，防自指信号洪水）。
2. **登记配额（D2'）**：单轮 登记 ≤2 条，超限并复合行——复合行只存 PENDING 行 id 指针（单源，cleanup-builds ledger 双写误读先例）。
3. **轮首抽检（D3'）**：task-driver 轮首挂载增义务「抽上轮 T 号 1 条核判定性+顺手打 done/not-done 标记」（≤30s）；**本义务 2 周日落**（防轮首成本堆积）。
4. **封闭动作集（D5，Linear triage 吸收）**：每条 T 号终态四选一=采纳修掉/去重合并（注明并入 id）/拒绝留痕（一句理由，**计入消化分母**）/搁浅待条件（触发条件即消费判据，条件触发自动浮回）；来源锚 anthropic engineering/linear.app/docs/triage（全文级深读 R3 A 臂）。
5. **消化自愈（D6，观察不试点）**：消化失败案例回写修正归 PENDING T46 门（零实证不建机制，Anthropic 工具自愈同构）。
