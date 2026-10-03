---
title: <一句话复盘标题>
date: YYYY-MM-DD
incident_date: YYYY-MM-DD
severity: 3
category: <复发匹配键，如 deploy-rollback>
status: draft
related_postmortem:   # 可选：仅 ADR 回链此 postmortem 时由 ADR 写入；复发在正文说明历史 slug，不用此字段
---

# <一句话复盘标题>

## OODA 记录

- **Observe(事实)**：<时间线/症状/影响/客观数据，只记事实不归因>
- **Orient(判断)**：严重度 <1-4>；是否复发 <是/否，链回 related_postmortem>；根因法 <5Why/鱼骨>
- **Decide(决策)**：<全量复盘 / 转 consensus 裁决根因 / 退出>

## 五要素

### 1. 症状(Symptom)

<可观测的异常表现>

### 2. 根因(Root Cause)

**技术根因**：<附 5Why 链或鱼骨分支>
**流程根因**：<对事不对人>

<!-- 5Why 示例：
症状 → 为什么1（依据：...）→ 为什么2（依据：...）→ ... → 根因
-->

### 3. 影响(Impact)

<范围/时长/波及面>

### 4. 行动(Action)

指向 `{slug}-capa.md` 的 action_id 列表：A1, A2, ...

### 5. 教训(Lesson)

<可复用认知，非具体 action>
