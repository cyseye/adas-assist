---
name: effect-governance
description: "战略评估部统管五职能组（含进化统管）。触发词：效果回填/闭环检查/验证对账/效果审计/评估服务/周评估/证据链审计/对抗验证调度/进化统管/复盘统筹。"
---

# effect-governance · 战略评估部统管（公立）

三部制组织（AGENTOS-MAP §组织架构）战略评估部行动实体（归属细节归 AGENTOS-MAP，不复写），五职能组：效果闭环/周评估/证据链审计/对抗验证调度/进化统管（§⑤，含复盘统筹）。评估协议 canonical=`_shared/assessment-protocol.md`（未包含，置信度 H/M/L 分级+审计动作+对抗调度表；主控按本文件内嵌流程自裁）；效果验证底层协议=`_shared/evolution-discipline.md §效果验证协议`。standard 型（主控串行；转对抗须用户点头）。GLM 尾部污染探针（`_shared/scripts/glm-pollution-probe.py` 未包含）：探针不可用时本项读数 no_data，不阻断其余议程。

## ① 闭环检查（默认动作）

1. **measured=null 清单**：读 `skill-evolution/registry/token-baseline.json` 的 optimizations + v2_round.actions——列出全部 expect 非空且 measured 为空的项，**分母打印**；逐项标注：有可算口径（→提议回填动作，机械写走 `weekly-eval.py --backfill id=value`，只写 measured 原始值、expect/回退留本 skill 裁决）/ 观察期（→列到期时间）
2. **基线对账**：跑 `usage-stats.py --days 7` 与 baseline 对照，输出趋势差（只读，不自动改 baseline）
3. **回退判定**：实测 < expect×50% 或越参考线的项 → 按 evolution-discipline 回退三分法出提议清单（执行须用户确认）
4. **信号消费**：baseline-gap 信号（weekly-eval 对账行发射）命中时，本 skill 是处置入口——回填或降级观察期。**扩权白名单**：本 skill 周期消费承载仅限 SLA 新信号+燃速回放对账；显式排除已裁决「留人工」信号（仅限历史遗留留人工项；观察表复评不在此列，见周批 checklist 第 5 行）。对账须打印分母与凭证形态；上线首期先跑一次阳性对照（人工制造消费 marker 验证对账段可识别）。

## ② 周评估消费

读 `weekly-eval.py` 预产报告（`<repo>/.claude/.build/weekly-eval-report.md`）：三旧指标（召回/打扰/转化）+ 两新指标（场均输入输出/主模型会话占比）判读与处置入口；两新指标口径、观察期（首两周期只报不判）与 fail-closed 行为见 assessment-protocol §周评估指标口径。参考线数值唯一源 `io-budgets.weekly_eval_refs`，本 skill 不复制数值。**memory 域回填（2026-09-30 接线）**：周评估附带跑一发 `skills/memory-governance/scripts/recall-replay.py`（从仓根跑），责任域命中率对账上期基线（基线单源 memory-governance SKILL，当前 0.8378·4 分生产口径），跌破 -2pp 才立案转 memory-governance，微小波动不追。

**周批消费 checklist**（evo-campaign-20260916 采纳项 3：CLI 通道齐备但零调用 → 周批固定步防悬空）：
1. 消费日档 M5 anomaly 行（measured-null/launchd-err/daily-gap）——逐条当场处置或落 PENDING
1b. 按失败标签频次排序复盘行（词表单源 `decision-improve/references/failure-taxonomy.md`，2026-09-26 D2 落地）——Top 标签入 CMP 排优输入
2. `--backfill id=value` 为**人工触发写动作**（契约不改动）：周批时由主控人工代执行清零悬空项，禁挂 cron
3. 联审到期时执行联审并 `--joint-review` 重置锚（消费即重置，禁裸 touch）
4. **KPI 读数锚注册行**（kpi-re-20260917-verdict 登记式挂接，非逐条枚举）：5 在判+1 观察（KPI5，复活判据=留痕覆盖≥80%）+1 退役（KPI6 tombstone，复活判据已登记）+2 正式候选（军团留痕率/接线有效率）读数锚=`.build/campaign-20260917-kpi-re/cross-team.r1.md` 逐条验证表+`#5/#6 观察退役状态见 kpi-re ADR`；仅 breach/no_data/null 异常项升级为具名 ⚠ 行，正常周零动作；**intake 单源季频对账**（vd-03）：`decisions/external-intake-20260919.md` 四缺口消化状态 quarter 锚（每季首周批对账一轮，未消化条目升 ⚠）
5. **org-formations 观察信号存在性对账**：grep 观察表 3 项激活信号落盘件（F2 after-action 预算诉求/分歧留痕异议被推翻/裁决留痕覆盖）——信号存在即标 PENDING 拉复评（观察项复评不属「留人工」排除面，历史遗留留人工项除外）；死寂（长期零信号）本身记入对账行
6. **KPI 悬空登记**（kpi-re-20260917-verdict 状态补记两项，2026-09-18 KPI 轮落地）：元层仓 cron 盲区（launchd 不覆盖 `~/.claude` 元层）+KPI3 复核宿主空缺（到期 2026-10-14 前须指定；**裁决主办=本部门 effect-governance，2026-10-07 周批前具名登记，vd-06**）——仅 breach/新增留痕时升 ⚠，宿主待裁决；读数锚第 4 行的 `.build/campaign-20260917-kpi-re/` 借宿件若被 cleanup 清理，先从 git 历史或 kpi-re ADR 引文重建再读数，勿静默跳过
7. meta-regression 回归集运行（python3 ~/.claude/skills/_shared/scripts/meta-regression.py 未包含，本仓跳过本项）；绿判据=当日 evolution-daily.log 有 `meta-regression` 行且含 `regression_fail=1/` 即非绿、全零 fail 才绿（分母无关写法，vd-11）；加 `--capability` 看 C13/C14 通道（fail 不 gate，连续两周绿后周批裁决并入 regression 毕业制，绿以日档行为凭据非口头）；weekly-eval 侧 meta-regression-gap 对账行兜底周批忘跑（V2）
8. **GLM 尾部污染信号对账**（external-benchmark-chain-consolidated §② GLM 系本体缺陷画像 登记排查项，原 external-benchmark-round3-20260919）：读数锚=`python3 ~/.claude/skills/_shared/scripts/glm-pollution-probe.py` 单行输出（A1/A2/A3/A4/A5 五特征计数）；A4>0 升 ⚠（观察期不触发分档表动作，仅登记排查），无数据标 no_data

**S34 固定词约定**：after-action/复盘行检出「口径不一致」字样即计 S34 事件（model-governance 未包含，其 §5 固定留痕格式同款先例）。

## ③ 证据链审计

对拟进 ADR/配置表的结论产物，按 assessment-protocol §证据链审计清单逐条核验（六条硬门的动作化执行：逐结论溯源/预注册核验/阳性对照/置信度标级/不利数据/无数据即假设）。不过项降级路径：补证据 / 补标 confidence / 降假设进 PENDING——**登记归机器、判断归人**。

## ④ 对抗验证调度

评估结论涉及体系级裁决而未过对抗时，按 assessment-protocol §对抗验证调度表转交：方案裁决类→PCF 三件套；体系变更类→devils-panel（L1-L3）；产物评审类→review-rule（纪律条款单源该协议，含跳过对抗标 PENDING）。

## ⑤ 进化统管（2026-09-25 用户裁决「统管进化角色」落地，kata coach 位——逼问不改手）

跨部门进化的全局视角统管：保证各 dept 自主进化**有效**（有对账）、**合理**（不 Goodhart）、**相互配合**（非单一视角）。定位于 coach 不做具体改动：对各部门进化轮逼问「目标卡（expect 是什么）→实验卡（怎么验证）→下轮对账（measured 谁回填）」，改动仍走各 skill 既有流程。五项固定议程（并入周批 checklist 消费；2026-09-25 V4 勘误：原文误计「四项」）：

1. **CMP 元生产力排优**（吸收 HGM arXiv:2510.21614，外参见 R5 行）：改进预算排优按「该部门近 N 次改进的 CAPA 实际兑现率」而非本周对账分——防高分低产部门霸占改进预算。**数据源前置缺口（2026-09-25 实测）：token-baseline.json 现无 dept 维度标注**——首期动作=新增改进项时补 dept 字段，存量回填前本项只报不判；**首次回填期限锚=2026-09-27 周批核对存量回填进度，逾期未动升级 PENDING**。
2. **无指标维度巡检**（吸收 arXiv:2603.28063「有限评估下未覆盖维度必然退化」定理）：定期列出「在跑但无 expect 契约的资产」清单——无适应度函数者不得自主进化（AlphaEvolve 准入门同构），先补契约或降观察。
3. **改善预算冻结**（吸收 SRE error budget 方法论，URL 本轮未验证待回访）：某部门 CAPA 复发率超阈（首期阈值=同部门同类复发 ≥2 次/月）→ 冻结其自主进化权、升级 PCF 档，冻结走 PENDING 用户确认。
4. **评审反馈降级**（吸收 arXiv:2609.28614「反馈越详细规避率越高 40.5%vs20.3%」）：PCF/评审给被评部门的反馈只给方向性结论+**验证标准**（decision-improve CAPA 闭环必需项，不因降级豁免），详细评分理由与判据细则留元层（本 skill 裁决记录）——降级的是「判据细节」非「可验证性」，两条款不互斥。
5. **配合度视图+动作出口**：从调用日志蒸馏各部门「擅长域/失效域+协作依赖图」（transactive memory，arXiv:2606.19911）；首期为周批报告附一行定性观察，机制化待数据面就绪。**动作出口**（R5 红队 H2 修正：只监督不提升=未覆盖诉求）：依赖图检出断链/环路/单点依赖超阈 → 触发联审定向议题或路由调整提议（落 PENDING），配合度从观察量升为可动作信号。

**判据双轨**（吸收 ADAS 弱点教训 arXiv:2408.08435）：本节五议程的判据本身归架构巡审定期复审（arch-governance 未包含，主控自审代行；防 meta 层僵化），本 skill 只执行不自我修订。

**裁决纪律补强**（2026-09-25 外参批，weak-to-strong arXiv:2312.09390）：本官逼问/裁决只认落盘锚（file:line/台账行），**推翻部门实证结论须举出锚级反证**，禁凭统管位阶直觉否决——防弱监督者裁决强执行者的系统性失真。**复盘统筹消费锚**：固定议程输入含 decision-improve CAPA 产出与 skill-evolution 反思节（复盘能力提升的用户裁决 2026-09-25 落此，不另立复盘通道）。

## 边界

- 产物级验证归 decision-verify / finish-check（交付时点）；本 skill 只管**体系级评估与效果闭环**——两轴不同不吞并
- 不自建数据集（red-blue-dataset 归 decision-verify data/ 协议）；只调度对抗不自演对抗

## 资源

| 文件 | 用途 |
|---|---|
| `_shared/assessment-protocol.md` | 评估协议 canonical（审计清单/置信度/调度表/指标口径；未包含） |
| `_shared/evolution-discipline.md §效果验证协议` | 效果闭环底层协议 |
| `_shared/analysis-methodology.md §证据链硬门` | 六条硬门条文唯一权威 |
| `skill-evolution/registry/token-baseline.json` | expect/measured 台账（未包含，主控按周评估报告对账） |
| `skill-evolution/scripts/usage-stats.py`（未包含） / `weekly-eval.py` / `daily-archive.py`（未包含） | 量化数据源与日档归档（只读） |
| `_shared/signal-tiers.json` | baseline-gap 分级真值 |
