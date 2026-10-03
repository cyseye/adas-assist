---
postmortem_id: <slug>
status: Open
requires_reverify: false  # CAPA 含纠正类 action(type=纠正)时改 true → 触发 decision-verify 复验(见 SKILL Step7)
---

# CAPA · <复盘标题>

## CAPA Actions

| action_id | type | description | owner | due | status | verification |
|-----------|------|-------------|-------|-----|--------|--------------|
| A1 | 纠正 | <修当下已发生问题> | <owner> | YYYY-MM-DD | Open | <可观测验证条件> |
| A2 | 预防 | <防同类再发> | <owner> | YYYY-MM-DD | Open | <可观测验证条件> |

## 闭环跟踪

- 整体状态：<映射规则见 references/capa-protocol.md §CAPA 闭环状态机>
- 复发检查日期：<YYYY-MM-DD>
- 同类别历史 postmortem：<slug 或 无>
- 历史 CAPA 失效评估（复发时必填）：<为何历史预防措施未生效>
