# 用户纠正记录模板（skill 级）

> 实例落位：`.claude/.state/corrections/<skill>.md`（不入库、扫描范围外、含用户原话）。
> 规范见 `.claude/standards/common/knowledge-lifecycle.md §三`；决策见 ADR knowledge-doc-governance-consolidation。
> 维护纪律：仅维护有效内容——merged 验证 ≥2 轮可删（教训已由条款承载）；每 8 轮/30 天清 stale 与超量 merged（仅保留最近 5 条）。
> 写者/转移执行者登记（T127，2026-09-28）：`new` 写者=主控（受 reflex-correction 提醒驱动）手写本表；`new→merged` 转移执行者=主控（条款落地轮当轮转移并加 `@日期`）；机械核=session-review 周扫 `correction-*` 信号——**仅提示注入，不代写不代转移**（T126 PCF 裁决上限）。
> 固化脱敏判据（T127⑤）：固化件（KNOWLEDGE/memory/条款/外传物）只保留「类型+条款摘要+生效位置」，用户原话仅留本地实例，永不外移。
> 半边同覆盖（T127④）：固化到 KNOWLEDGE/memory 时须核 MEMORY.md（或画像）半边是否需同覆盖，防教训单边落一层。

## 记录表

| id | 纠正原文（用户原话） | 类型 | 生效条款位置（+内容摘要） | 验证方式 | 状态 |
|----|---------------------|------|--------------------------|---------|------|
| C01 | （用户原话引用） | behavior | SKILL.md §X 条款摘要 | reflex-check 不再命中 | merged@2026-01-01 |

## 字段说明

- **id**：C 序号递增（C01…）
- **类型枚举**：`behavior` 行为约束 / `process` 流程偏好 / `expression` 表达格式 / `artifact` 产物标准 / `bugfix` 错误修正
- **生效条款位置**：SKILL.md 节/条款 + 内容摘要（**不写版本号**——位置随迭代更新，防断链）
- **验证方式枚举**：reflex-check 不再命中 / 红蓝条目 / grep 抽查 / 用户确认
- **状态机**：`new`（已记录未生效）→ 条款生效转 `merged` → 被新纠正取代/条款回退转 `stale` → 清理轮删除 `purged`
- **merged_at 形态**（T127②）：`merged`/`stale` 一律带固化日期后缀 `@YYYY-MM-DD`（如 `merged@2026-09-28`）=机械可判的清理时点锚；`new` 不带日期。
