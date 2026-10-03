# finish-check 评审门协议

> 复用 `_shared/review-gate-skeleton.md`（骨架未包含，判定逻辑以本文件特化值为准）：编排契约（主控串行 spawn 禁 background）+ 严重性分级 + 评分公式 + 判定优先级 + PCF 决策空间与 Finalizer 约束；档位/reviewer 结构/PCF 触发分级见 SKILL.md「梯度选择」。本文件只定义 finish-check 特有项：判定语义 + must-fix + issue→severity 映射 + 判级纪律 + 维度权重/阈值。

## 判定语义（quick/standard，无加权评分）

- `must_fix==0` → `pass`（有未修 MAJOR/MINOR → `pass_with_flags`）；`must_fix>0` → `fixable`
- status 取 pass / pass_with_flags / fixable 三值（无 critical——CRITICAL 为 full 专用状态值）
- B0 例外各档生效：须人工确认才 BLOCKER，非无条件
- **finish-check 无 fixer agent**，不适用 skeleton 判定优先级第 7 步（spawn fixer→下一轮）：FIXABLE 的处理统一在终报告（轻修复清单 / P1 单独裁决 / handoff）；full 多轮 = reviewer 按上轮 findings 重审复评，非自动修复

## must-fix 列表（一票否决 = BLOCKER；B0 例外见上）

| 维度 | issue | 理由 |
|------|-------|------|
| B1 | 跨任务功能交叉未公共抽取 | 重复实现债，交付前必修 |
| A1 | 冗余/废文/死代码（结构性，非单点） | 交付带废文污染检索 |
| B4 | 跨功能逻辑未闭环（断链/死路径） | 交付即缺陷 |
| A3 | 实现未满足用户明确要求 | 不满足需求=未完成 |
| B0 | git 未提交/未 push 但用户预期已提交 | 漏提交混入（须人工确认，不自动 BLOCKER） |

## issue→severity 映射（非 must-fix）

| 维度 | issue | severity |
|------|-------|----------|
| A2 | 表达层次混乱/逻辑不严谨 | MAJOR |
| A2 | 语言不精炼/啰嗦 | MINOR |
| A4 | 过度设计（为假设建机制） | MAJOR |
| A4 | 未按 project rules（命名/格式） | MINOR |
| B2 | 需串联未串联（非断链，优化级） | MAJOR |
| B3 | 跨任务上下文轻微不一致 | MINOR |

## severity 判级纪律（reviewer 校准，实证沉淀）

**词汇统一**：BLOCKER（=must-fix=P1 单独裁决）/ MAJOR（=P2 可入修复清单）/ MINOR（=P3 可选）。汇报用 P 系词汇，reviewer 回传用三级词，禁用 critical 等未定义词（CRITICAL 作 full 总分阈值状态值除外）。

1. **MAJOR 及以上仅限三类实证**（须引用可复现证据：文件+行号+原文片段）：断链（引用目标不存在）/ 需求未满足（用户明确要求落空）/ 口径矛盾（同一概念两处语义冲突）。
2. **表述方式差异但语义一致 → 最高 MINOR**（如「保留 32 天」vs「清理 >32 天分区」）。reviewer 自认「语义一致」的项禁止标 MAJOR+。
3. **reviewer 自评 informational / 保持现状的 finding 不计入 severity 统计与 must-fix 判定**，只作备注。
4. **主控复核**：MAJOR+ 未经主控逐项交叉验证不得进终报告——复核含降级/驳回记录与理由（防 reviewer 误判被下游放大，memory `review-fix-chain-false-positive`）。

## 维度权重与阈值（仅 full 适用）

**权重**：清单 A（产物质量）A1/A2/A3/A4 各 25%；清单 B（提交一致性）B0 10% / B1 30% / B2 20% / B3 20% / B4 20%；两清单同跑各占 50% 归一。

**评分域（仅此 9 维）**：A1-A4 + B0-B4（B0 为主控自查产出，含权重）；A5 为条件维度（对象含前端页面时转交 `audit-page-quality`）、B5 定级 P2 走轻修复清单，均不入评分。full 的 reviewer = **2 个合并 reviewer**（A 组覆盖 A1-A4、B 组覆盖 B1-B5；一次输入多维复用，先例 review-figma 四维合一——曾为每维 1 reviewer 共 9 spawn，2026-09-12 token 治理轮合并，评分仍按 9 维逐维计，B0 主控自查不 spawn、A5 转交）。

**阈值**：总分 ≥ 90 → PASS；任一维度 < 80 → FIXABLE；round 1 总分 < 60 → CRITICAL → PCF；两轮分差 < 5 → plateau → PCF；max_rounds = 3（收尾检查非深度迭代，3 轮够）。

## PCF 触发条件（详版，分级见 SKILL.md 梯度表 PCF 列）

1. CRITICAL（round 1 总分 < 60）—— 仅 full（quick/standard 无评分不适用）
2. plateau（两轮分差 < 5）—— 仅 full（轻量档单轮不适用）
3. 超轮（round ≥ 3）—— 仅 full（轻量档单轮不适用）
4. **reviewer 争议**：同一项多 reviewer 结论冲突（finish-check 独有——reviewer 间分歧时 PCF 裁决，非评审停滞）—— standard + full

决策空间与 Finalizer 约束复用 skeleton（特化仅一处：`fix_targeted` 的 handoff 约束 = improve/fix）。

## 产物命名

- 检查报告：`{work_dir}/.build/report.finish-check.round.{N}.json` + 终审 `{work_dir}/.build/finish-check-report.json`（上游编排按此路径读取）
- PCF：`{work_dir}/.build/finish.pcf.{context,proposer,critic,finalizer}.json`
- 装配上下文：`{work_dir}/.build/finish-context.json`
- 产物生命周期（inline 零文件 / file 汇报后清理 / 验证标记落 `.claude/.state/`）见 SKILL.md 运行约定
