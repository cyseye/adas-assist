# Red/Blue 验证协议

## 角色

- **红队**：主动攻击，找缺陷。只产出 report（`report.red-team.round.{N}.json`，由 review-rule 写），**不修改任何产物**。
- **蓝队**：被动修复，补缺陷。读红队 report 逐项修，**不主动发现新问题**。
- 红蓝通过文件通信，禁止内联传递问题清单（避免上下文污染与失真）。

---

## 红队攻击维度

红队按以下维度主动探测缺陷，发现的问题归类到 4 维（正确性/安全性/规范性/完整性），供评审门评分。

| 攻击维度 | 探测重点 | 映射维度 | 典型 check |
|---------|---------|---------|-----------|
| 边界 | 空/单/满/溢出/极值输入 | 正确性 | COR-A02 |
| 异常 | 错误路径/超时/取消/回滚 | 正确性 | COR-A03, C002 |
| 安全 | 注入/越权/泄露/信任边界 | 安全性 | SEC-*, C004 |
| 并发 | 竞态/死锁/共享状态 | 正确性 | C003 |
| 性能 | N+1/全表/无限循环/阻塞 | 完整性 | CMP-A01 |

红队执行即 review-rule：按 `checklist-dimensions.md` 逐项校验 `target_files`，产出 issue（含 check_id/severity/dimension/location/message）。

---

## 蓝队验证要求

每条红队 issue 的修复须闭环：

1. **复现**：按 `location` 定位，确认缺陷真实存在（避免误修）
2. **定位根因**：到文件+行号，不只改表象
3. **修复**：对照反幻觉来源（见 exec-review-fixer-blue.md 的 object_type 来源表）
4. **回归**：修复后重跑红队，确认该 issue 不再出现（由主控每轮重跑 reviewer 保证）

修复优先级（高→低）：
1. 必须修复项（must_fix_items，一票否决）
2. 正确性 P0 / 安全性 P0
3. 其他维度 P0
4. P1

---

## 红蓝隔离规则

- 红队**只找不修**；蓝队**只修不找**。职责交叉会破坏评分客观性（修复者既当裁判又当运动员）。
- 红蓝**仅通过文件通信**：红队写 `report.red-team.round.{N}.json`，蓝队读轮次报告 `report.review.round.{N}.json`。禁止把 issue 列表内联到蓝队 prompt。
- 蓝队修复后**不直接改 review report**（主控重跑生成新轮次）。
- 迭代由主控管理：红队→评分→（不通过）蓝队→红队重跑→…，直到通过或 plateau 触发 PCF（评分按 review-gate-protocol.md，不委托 review-gate agent，见 SKILL.md §4 注）。

---

## 数据集回归基线（条件启用）

主控 Phase 0 召回 `../data/red-blue-dataset.jsonl` 中匹配的 active 条目，经 reviewer_args 的 `baseline_dataset` 参数传入红队（无命中则无此参数）；红队/弱基线/收尾规则单源=`dataset-protocol.md` §4。
