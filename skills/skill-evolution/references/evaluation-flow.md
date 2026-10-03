# 进化执行流程

> 评估引擎（metrics/evolve 链）已退役（2026-09-05）；效果判据 = 全局调用日志（`registry/invocations.jsonl`）+ 周评估三指标。本文件为现状流程；历史 metrics SOP 见 git 历史。

## 执行流程

```
[触发] 用户要求 OR 明确退化（周评估/用户反馈信号）OR 共性问题≥2次
   ↓
[rules 健康检查] python3 skill-evolution/scripts/rules_audit.py {target}
   → high 问题 → 先修 skill 设计文件，再评产物；low 问题记录，不阻断
   ↓
[门控] 真实共性≥2次 + 改进指向明确收益 + 风险等级≤中 → 进入根因前置
       否则 → 不进化，记理由（默认拒绝；判据见 `_shared/evolution-discipline.md`）
   ↓
[根因+影响面前置] 见 `_shared/evolution-discipline.md §根因与影响面前置`（分档 L1/L2/L3）
   ↓
[PCF 辩论] pcf-proposer → pcf-critic → pcf-finalizer（见下方 PCF 步骤说明）
   ↓
[执行] 按 PCF finalizer 裁决改 skill 纪律/规则/模板（worktree 隔离，见 worktree-sop.md）
   ↓
[记录] 更新 EVOLUTION.md → 清理中间产物（见 cleanup-rules.md）；重大版本转 decision-record 沉淀 ADR
```

**执行者**：主 agent（触发判断 + 门控裁决 + PCF 协调 + EVOLUTION.md 写入）。各 skill 维护自己的 EVOLUTION.md。

## 根因与影响面前置（本 skill 域增量）

四步协议 canonical 见 `_shared/evolution-discipline.md §根因与影响面前置`。本 skill 域增量：

- 根因方法论引用 decision-improve（简单→5Why，复杂→鱼骨）
- L2 根因链内联传 PCF；L3 写 `{target}/.build/rootcause-impact.md`
- 退化 P0（系统性/复发）升 devils-panel 对抗快审（`devils-panel/references/integration-mapping.md 接入点2`）
- 确认门即 evolution-discipline §骨架优先 5 的骨架轮——确认的是改动结构（改哪些文件哪些条款），通过后 worktree 执行即填充轮，不另设门控

## PCF 辩论步骤（根因+影响面确认后）

主 agent 传给 pcf-proposer 的内容（精简内联，不走文件）：

- 根因链 + 影响面清单（**必读**；提案不回应根因即 fail）
- 具体改动提案（改哪个规则/模板/纪律，一段话描述）
- 效果信号摘要（调用日志趋势 / 周评估指标 / 用户反馈）
- 风险评级（低/中/高，来自 `_shared/evolution-discipline.md §风险评级`）

> 影响面清单同时作为 pcf-critic 的检查面（改动波及点是否全覆盖）。输入超长（完整内容 > 100 行）时先写入 `.build/gate-input.md`，传路径给 proposer。

产物：每轮产出 `.build/review.pcf.round.{N}.json`（proposer/critic/finalizer 结论），门控通过后清理。

## 回归验证 SOP（改 skill 后必做，覆盖回归 / 判定 / 留痕三环）

1. **回归重跑**：在 worktree（见 `worktree-sop.md`）用固定测试集从头跑一次目标 skill，产出新效果数据。
2. **效果判定**：主控对比改动前后产物质量与效果信号（调用日志趋势 / 用户反馈）：
   - 提升 → 达取优门槛，EVOLUTION.md 更新当前最优版本标注
   - 下降 → **明确退化**，记 EVOLUTION.md「残留风险」，**回退 skill 改动**
   - 持平 → 无实质变化，默认不动（不记 EVOLUTION）
3. **判定留痕**：结论（提升/下降/持平 + 证据）写入 EVOLUTION.md 本轮条目，防后续轮误判。
