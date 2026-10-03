# CAPA 协议

> Corrective Action + Preventive Action。纠正修当下，预防防再发。

## 核心原则

- **纠正与预防分离**：纠正修已发生问题，预防防同类再发；不可只做纠正不做预防。
- **per-action 闭环**：每条 action 独立状态跟踪，整体状态=所有 action Verified 才 Closed。
- **可验证**：每 action 必有验证标准（如何确认该 action 完成/有效）。
- **不强行关闭**：资源/人力不足无法闭环时保持 Open + 复盘日期，不强行 Closed。

## 纠正 vs 预防

| 类型 | 目标 | 典型 |
|------|------|------|
| 纠正(Corrective) | 修当前已发生的问题 | 回滚部署/修 bug/补数据/恢复服务 |
| 预防(Preventive) | 防同类问题再发 | 加自动化校验/改流程/加监控告警/补测试用例 |

判定规则：
- 纠正=消除已发生的故障；预防=改变系统/流程使同类不再发生
- 若某 action 既修当下又防再发，按主要目标归类

## CAPA 闭环状态机（per-action）

```
Open ──分配 owner──▶ In-Progress ──完成执行──▶ Closed ──验证通过──▶ Verified
                                          │
                                          └──验证失败──▶ 回 In-Progress
```

| 状态 | 语义 | 转移触发 |
|------|------|---------|
| Open | 已规划未分配 | 分配 owner → In-Progress |
| In-Progress | 执行中 | 执行完成 → Closed |
| Closed | 执行完成待验证 | 验证通过 → Verified；验证失败 → In-Progress |
| Verified | 验证通过，闭环 | 终态 |

> capa.md 整体 status 映射规则（per-action 状态聚合）：
> - **Closed** = 所有 action 均 Verified
> - **Open** = 所有 action 仍 Open（均未开始）
> - **In-Progress** = 其他：已开始推进但非全部 Verified（既非全 Open 也非全 Verified）

## 复发判定

复发 = 同类别问题历史 postmortem 已记录后再现。

匹配规则：
- 匹配键 = postmortem frontmatter 的 `category` 字段
- 新 postmortem 的 `category` 与历史某 postmortem 相同 → 判复发
- 复发时新 postmortem 在正文（Orient 节）说明历史 id，不在 frontmatter 写链（`related_postmortem` 仅用于 ADR→postmortem 回链）
- 复发 postmortem 的 CAPA 必须评估历史 CAPA 为何失效（是未执行/执行无效/预防措施本身错）
- **匹配失败处理**：精确 category 匹配失败 → 先按关键词/症状模糊匹配历史 postmortem → 命中判复发（confidence=medium）→ 仍无命中 → `[WARN] 无法判定复发` + AskUserQuestion 让用户裁定（新问题 / 复发），不静默判新问题

## 验证标准写法

每 action 的 verification 字段须可观测、可判定：

- 纠正类：明确"如何确认该问题已消除"（如"重跑 X 测试通过"/"监控 Y 指标恢复"）
- 预防类：明确"如何确认同类不再发生"（如"CI 加校验 Z，提交触发"/"流程节点 N 必审"）

禁止模糊验证（如"加强关注"/"注意"），必须有可检查的条件。

## 代码层 CAPA 执行边界

代码层 CAPA 边界单源=`decision-improve/SKILL.md §不启用清单`；一句话：improve 规划"该修什么、为什么"，代码层"怎么改"由主控按 dev-implement 流程执行或手工修复。
