# 收敛判定规则

> decision-consensus 的收敛判定，借鉴 review-gate 的 plateau 检测（连续两轮分差 < 阈值即收敛）。术语对齐 SKILL.md。

## 差异度量

### 要点提取

主控汇总每轮 N 个 proposal 后，按「要点」粒度对比：

1. 从各 proposal 提取**可比较要点**（如「用 Redis」「需持久化」「运维成本高」）
2. 对每个要点判定：
   - **共识点**：所有 proposer 对该要点立场一致（支持 / 反对一致）
   - **差异点**：proposer 之间立场分歧（至少一方不同）

要点是收敛的最小单位——一个 proposal 拆解为若干要点，要点级对比形成共识 / 差异集。

## 共识度公式

```
convergence_score = round( 共识点数 / (共识点数 + 差异点数) × 100 )
```

- 0 = 完全分歧（无共识点）
- 100 = 完全一致（无差异点）
- 写入 consensus.round{R}.summary.json 的 convergence_score

## 收敛条件（借鉴 review-gate plateau）

review-gate plateau：`round>=2 and (total_score - prev_score) < 5`。本 skill 借鉴：

| 条件 | 判定 |
|------|------|
| R >= 2 且 (本轮 convergence_score - 上轮) < convergence_delta(=5) | **收敛**（差异趋稳，继续迭代收益递减） |
| R >= 2 且 差异点数 <=2 且 较上轮差异点数减少 | **实质收敛**（差异已细节化，分差虽 >=delta 但继续迭代边际收益低于成本） |
| R >= max_rounds(=3) | **强制收敛**（达迭代上限） |
| 否则（R < max 且分差 >= delta 且不满足实质收敛） | 继续，R++ 回提案 |

### 为何用「分差 < delta」而非「分差 <= 0」

分差小但非零也算收敛——差异在收窄但极慢，继续迭代边际收益低于成本。delta=5 是经验值，复杂分歧可调高到 8-10（在 summary 中记录调整理由）。

### 为何补「实质收敛」

分差 < delta 检测「趋稳」，但快速收敛场景分差仍大而差异已细节化，仅靠分差会过度迭代——实质收敛以「差异点数≤2 且较上轮减少」兜底，触发后同样走 critic/finalizer。前提：要点提取粒度跨轮一致（summary 显式标注总要点数；波动>30% 粒度不可比，降级只按分差判定）。

## 强制收敛处理

R≥max_rounds 仍未自然收敛时：

1. 标记本次为强制收敛
2. 残余分歧全部移交：残余 ≥2 → pcf-critic 挑战；然后统一交 pcf-finalizer
3. consensus.final.json 的 confidence 标 `low`，reason 注明「强制收敛，残余分歧未完全消除」
4. debates.md 记录 `outcome: forced_convergence`

## 判定决策表

| R | convergence_score | prev_score | 判定 | 动作 |
|---|------------------|------------|------|------|
| 1 | 任意 | —（无上轮） | 继续 | R=2，注入 summary1 反馈 |
| 1 | 100 | — | 收敛（差异点=0） | 单轮收敛，跳 critic 直 finalizer |
| 3 | 任意 | 任意 | 强制收敛 | → critic / finalizer，confidence=low |

> 自然收敛（分差<delta）与实质收敛同时满足时记自然收敛，实质收敛为兜底（动作一致，均→critic/finalizer）。

### 单轮收敛特例

R=1 即 convergence_score=100（差异点=0）：各方首提案即完全一致，跳过迭代与 critic，直接 finalizer 裁决（对应 SKILL.md 降级策略「单轮即高度收敛」）。

## 与 review-gate 的差异

本 skill 借鉴其 plateau 思想但对象不同：review-gate 评产物质量分（delta=5、max 5 轮、停滞后触发 PCF 辩论），consensus 评共识度（delta=5、max 3 轮、停滞后强制收敛 + 残余交 finalizer）。

## 关联

- 多轮编排与反馈格式：见 delphi-protocol.md
- schema 转写与编排映射：见 decision-mapping.md
