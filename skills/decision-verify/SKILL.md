---
name: decision-verify
description: "验证/Red-Blue 验证/质量门/验收：红队+蓝队+Checklist 串行迭代，code/design/prd/generic 三档；小改动不上全量。"
---

# Skill: decision-verify · Red/Blue + Checklist 验证

> effort 缺省：quick=low / standard=medium（全局缺省）/ full=high（model-governance 未包含，原指针 §5` 触发条件式升档。

> 调度说明：本 skill 的 agents/*.md 不被平台注册，禁止按名 spawn。「委托 X」= 主控 Read agents/X.md 后按其定义自演，或以其全文作 prompt spawn general-purpose。（约定见 `_shared/runtime-conventions.md §4`）

对任意产物（code/design/prd/generic）做红蓝队迭代验证：红队(review-rule)主动找缺陷，蓝队(exec-review-fixer-blue)修复，**主控串行管迭代评分/一票否决/PCF**（按 review-gate-protocol.md）。

**架构职责**：主控管对象判定+迭代编排+评分+收尾汇总；红队/蓝队/pcf-* 为叶子 agent（主控直接 spawn，非嵌套）。详细规则下沉 references/。每轮归维/评分/判定属机械算术，**调 `gate-assist.py verify-judge`**（stdin 喂 findings+thresholds，双词表 profile，判定优先级表内建）执行，主控只消费 verdict 决定下一步——禁逐轮手工算分（ADR adr/data/token-effect-balance-v2）。

## 1. 运行约定
1. `{skill_dir}` = `~/.claude/skills/decision-verify`
2. `{target_dir}` = 待验证产物目录（用户传入）
3. `{work_dir}` = `{target_dir}`（产出根目录；主控拼 `{work_dir}/.build/` 写产物）
4. 文件传递：agent 间通过 `.build/*` 路径交付；prompt 仅传路径，不内联正文。
5. **终态判定原则**（外参吸收 2026-09-18，Anthropic evals「outcome 看环境终态而非模型自述」）：通过与否以落盘产物/命令输出/文件终态为准——被验证方（或蓝队/修复者）的自述"已修复/已通过"不构成通过证据，须 Read 产物或重跑命令核验终态后才可计 fixed_count。

## 2. 触发条件
**启用**：用户说"验证 / Red-Blue 验证 / 质量门 / 验收" + 待验证产物路径。
**不启用**：生成 PRD/详设 → 项目仓流程 | 共识裁决 → decision-consensus | 需求探索 → `decision-explore`。

## 3. 用户输入
| 参数 | 必选 | 说明 |
|------|------|------|
| target_dir / target_files | 是 | 待验证产物路径 |
| object_type | 否 | code/design/prd/generic；缺省自动判定（见 verify-mapping.md） |
| tier | 否 | quick/standard/full；缺省按「验证档位」推断（见 §5），显式指定覆盖推断；上游 handoff 可传入 |

## 4. 输入与资源
| 资源 | 路径 | 读取者 |
|------|------|--------|
| 红队 checklist | `references/checklist-dimensions.md` | review-rule |
| 红蓝协议 | `references/red-blue-protocol.md` | review-rule(rules) / 主控 |
| 评分协议 | `references/review-gate-protocol.md` | 主控 |
| 对象映射 | `references/verify-mapping.md` | 主控 |
| 蓝队 fixer | `agents/exec-review-fixer-blue.md` | 主控调度 |
| 红队 reviewer | `~/.claude/agents/review-rule.md` | 主控调度 |

> **不委托 review-gate agent**（嵌套 background spawn 断裂实证已登记 memory `review-gate-nested-bg-limit`）：主控直接 spawn 叶子 agent，通知链不断；评分/判定协议沿用 review-gate-protocol.md（agent 不复用，protocol 复用）。

## 5. 执行流程

### Phase 0：对象判定
按 `verify-mapping.md` 判定 object_type（用户显式 > 自动按扩展名/目录名 > generic+[INFO]）。据此选 checklist 特化项与评分权重。

**召回**：**上游有 clarified-requirements.md 时：先读其 frontmatter `recall_refs` 直读命中条目，命中不足再全索引扫描**（转交指针化，ADR adr/data/token-effect-balance-v2）；否则读 `~/.claude/decisions/KNOWLEDGE.md` 找相关 postmortem（按 `standards/common/knowledge-protocol.md` 标准词表匹配 target 主题），供 §9 复发判定参考——补 verify 现仅塞 handoff 转发不查历史的缺口。

**数据集召回**：object_type=design 时读 `{skill_dir}/data/red-blue-dataset.jsonl`（存在时），按 `task_type` + `task_chain.final_output_path` 匹配当前验证目标、筛 `status=active` 条目，命中进 Phase 1 `baseline_dataset` 参数（红队回归基线；schema 与防误判纪律见 `references/dataset-protocol.md`）。

**验证档位**（对象判定后立即定档；重武器按需点火——多轮对抗取优仅 full，对齐 `_shared/evolution-discipline.md §智能分档总则`，不为小改动上最重模式）：

| 档 | 适用 | 数据集基线 |
|----|------|-----------|
| quick 快验 | 单文件产物 / 上游 handoff 标重验 / 提交前快验 | 跳过 |
| standard 标验（缺省） | 常规产物验收 | 按既有条件 |
| full 全验 | 重大交付 / 跨多任务验收 / 体系级改动 / 用户说「深度/全量验证」 | 必跑 |

> 档位轮次/评分参数单源=`review-gate-protocol.md` §5；quick 简化判定特化见下。

- **档位推断**（用户未显式指定 tier）：单文件产物、提交前快验或上游 handoff 标快验/重验 → quick；常规验收（缺省）→ standard；用户说「深度/全量验证」或重大交付、跨多任务 → full；显式指定覆盖推断
- **各档共享硬约束**：must-fix 一票否决（安全性 P0 / 反幻觉检出）全档生效；round-based 命名与 Phase 3 清理规则不变；数据集回写全档生效
- **quick 简化判定（quick 全部特化在此单源）**：跳过评分（报告省略分数字段，仅 status/must_fix_count/must_fix_items/top_issues）、判定不走七步评分只用 must_fix==0 且 P0==0 → pass；否则蓝队修 1 次+复验 1 轮，fixed_count==0 或复验仍不过 → escalate_to_user（无 PCF 分支，争议直接 escalate_to_user）
- 档位由主控按产物规模直判，不套 devils-panel 判据——该判据是变更影响面轴（自进化域），验证域是产物规模轴，两轴不同，总则不改写既有判据

### Phase 1：组装调用参数
- reviewer_args = "target_files={tf} checklist={skill_dir}/references/checklist-dimensions.md rules={skill_dir}/references/red-blue-protocol.md output={work_dir}/.build/report.red-team.round.{round}.json baseline_dataset={Phase 0 命中条目路径列表}"（`{round}` 占位，Phase 2 每轮 spawn 时按当前轮次替换——round-based 命名防多轮覆盖；`baseline_dataset` 为数据集召回的回归基线，无命中时省略该参数，红队按 `references/red-blue-protocol.md §数据集回归基线` 处理）
- fixer_spec = {skill_dir}/agents/exec-review-fixer-blue.md
- fixer_args = "target_dir={td} object_type={ot}"

### Phase 2：主控串行迭代（按 review-gate-protocol.md）
初始化：Read `{skill_dir}/references/review-gate-protocol.md` 提取评分维度/权重/公式/阈值/PCF，按「验证档位」表取 max_rounds/评分制开关/PCF 触发集；`round=0, prev_score=null, score_history=[]`。

loop（max_rounds=按档位，取值见上方「验证档位」单源注 = review-gate-protocol.md §5）：
1. `round += 1`；spawn review-rule（subagent_type=review-rule，传 reviewer_args，output 中 `{round}` 替换为当前轮次）→ `{work_dir}/.build/report.red-team.round.{round}.json`；**同步等待 spawn 完成再 Read**（确保 report 落盘，防时序致读取空/丢失）。
2. 按 protocol §2-§4 评分：issue 归 4 维、must-fix 标记（§3）、维度分/总分公式（§4 单源，权重按 verify-mapping.md object_type）。
3. Write `{work_dir}/.build/report.review.round.{round}.json`（schema §7）。
4. 判定（七步优先级与阈值全表=protocol §5 单源：must-fix 一票否决→维度底线→总分→CRITICAL→plateau→修复停滞→超轮次）：CRITICAL 仅 full（standard 记 score_history 进蓝队循环不即时触发）；quick 档判定见「验证档位」节 quick 简化判定单源。
5. FIXABLE→委托蓝队 exec-review-fixer-blue（不被平台注册，主控 Read `agents/exec-review-fixer-blue.md` 后按其定义自演，或以其全文作 prompt spawn general-purpose；按 fixer_spec 规范，传 work_dir/round_report=`{work_dir}/.build/report.review.round.{round}.json`/round_number/fixer_args）→`{work_dir}/.build/report.fix.round.{round}.json`；fixed_count==0→plateau→PCF（quick 档行为见 quick 简化判定单源）；否则更新 prev_score、score_history，回 1。
6. PCF→（仅 standard/full）串行 spawn pcf-proposer→pcf-critic→pcf-finalizer（文件驱动，context 写 `{work_dir}/.build/review.pcf.context.json`）→按决策执行：`fix_targeted`（spawn fixer 限 top-3 must-fix/P0 后跑最终轮）/`accept_with_flags`（须无 must_fix）/`escalate_to_user`。

收敛（PASS / accept_with_flags / escalate_to_user）→ Phase 3。

### Phase 3：收尾汇总
Read `report.review.final.json`（主控按 §8 schema 写）+ 红/蓝队报告，按 `templates/verify-report.json` schema 汇总成 `{work_dir}/verify-report.json`（关键计数/产物分均在此；**不另写 `{work_dir}/.build/metrics.latest.json`**——dogfood 时 `work_dir`=被验证 skill 目录，写它会与该 skill 自身产物混淆）。verify-report 属运行时产物**不入 KNOWLEDGE 索引**；知识沉淀走 handoff：must_fix>0 → `decision-improve`（postmortem/capa 条目入索引），PASS 但有重大裁决 → `decision-record`（ADR 条目入索引）。**数据集回写**（有召回条目时）：PASS → 刷新命中条目 `last_verified`，检出回归 → 置 `verification.regression_detected=true`（协议 `references/dataset-protocol.md` §4）。

## 6. 输出规范
```
{target_dir}/
  verify-report.json                                   # L0 验证报告（永久）
  .build/report.red-team.round.{N}.json                # 红队 issue（round-based，防多轮覆盖）
  .build/report.fix.round.{N}.json                     # 蓝队修复
  .build/report.review.round.{N}.json + .final.json    # 主控迭代评分
```

## 7. 异常处理

> 通用失败降级（空输入/用户全拒绝/上游产物缺失/spawn 失败）见 `standards/common/skill-failure-protocol.md`，本节仅列 verify 特有项。
| 场景 | 处理 |
|------|------|
| target 缺失 | 硬失败 |
| object_type 无法判定 | 默认 generic + [INFO] |
| review-rule/fixer spawn 失败 | 重试 1 次→仍失败 hard fail |
| pcf agent spawn 失败 | 重试 1 次→仍失败 escalate_to_user |
| 反幻觉来源缺失 | fixer 标 skipped_no_source + [WARN]，不静默（触发 must-fix 一票否决） |

## 8. 产物生命周期与清理

**清理时机**：仅在 Phase 3 收尾（收敛判定后）执行一次。Phase 2 迭代轮次中**绝不清理**——red-team/review.round 报告须完整留存到收尾，防收敛轨迹中途丢失。

**分级清理**：

| 收敛状态 | 处理 |
|---------|------|
| PASS（默认） | 删 `.build/report.red-team.round.*.json` / `report.review.round.*.json` / `report.fix.round.*.json` / `review.pcf.*.json`；**保留** `verify-report.json`（L0 永久）+ `report.review.final.json`（终态留痕） |
| fail / escalate_to_user | 保留 `.build/` 全部用于调试 |
| `KEEP_INTERMEDIATES=1` | 跳过清理，全保留 |

> red-team report 采用 round-based 命名（`report.red-team.round.{N}.json`），多轮迭代不互相覆盖——修复原固定名 `report.red-team.json` 每轮覆盖致历史丢失的根因。收敛轨迹（score_history / dimensions）已归档进 `report.review.final.json` + `verify-report.json`，终审后可安全清理过程 round 文件。

## 9. 转交边界（闭环下游）

verify-report.json 落地后的转交映射单源 = `references/verify-mapping.md` §6（信号→skill 表 + handoff 字段写法 + 仅提议不自动跑的克制约定），本节不再重复列表。

## 反模式
| 禁止 | 正确做法 |
|------|---------|
| 红队直接修复 | 红只找不修，修复由蓝队 |
| 蓝队主动找新问题 | 蓝只修不找 |
| issue 内联到 fixer prompt | 仅传 report 路径 |
| 主控无限迭代 | 轮次上限按 review-gate-protocol.md §5 档位表（单源），plateau 走 PCF |
| 小改动也跑全量多轮 | 按验证档位取强度：多轮对抗取优仅 full（对齐 `_shared/evolution-discipline.md §智能分档总则`） |
| 委托 review-gate（嵌套 background 断裂） | 主控直接 spawn 叶子 agent |

## 引用
| 文件 | 用途 | 读取者 |
|------|------|--------|
| `references/verify-mapping.md` | 对象判定+checklist选择+权重+编排映射 | 主控 |
| `references/checklist-dimensions.md` | 4维通用+对象特化检查项 | review-rule |
| `references/red-blue-protocol.md` | 红蓝职责+攻击维度+隔离+数据集回归基线 | review-rule/主控 |
| `references/dataset-protocol.md` | 数据集条目 schema/采集/注入/生命周期 | 主控 |
| `data/red-blue-dataset.jsonl` | 红蓝回归基线数据集（JSONL） | 主控召回/设计 skill 追加 |
| `references/review-gate-protocol.md` | 评分+阈值+PCF | 主控 |
| `agents/exec-review-fixer-blue.md` | 蓝队泛化修复 | 主控 |
| `templates/verify-report.json` | 验证报告 schema | 主控 |
