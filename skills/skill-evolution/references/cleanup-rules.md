## EVOLUTION.md 压缩规则（防上下文膨胀）

触发条件：`EVOLUTION.md` 超过 **150 行**。  
压缩策略：保留最近 **3 轮**全量记录（改动 / 指标 / 理由 / 风险 / 下轮方向）；更早版本各压缩为单行摘要：

```
- V{N}（{日期}）：{改动标题} → 产物分 {X}（{verdict}）
```

压缩后目标：≤ 100 行。非 CI 环境压缩前列出被压缩的版本号，等用户确认。

> 其他 skill 资产（SKILL.md / references / registry 型文件）的大小阈值与超标处置分级：skill-design.md 本仓未包含，口径以行内登记值为准（references/agents 单文件 ≤400 行、SKILL.md 主件 ≤150 行），机器探测 = session-review.py `skill-file-oversize` 信号；本文件只管 EVOLUTION.md 的压缩细节。

---

## 产物清理

| 类别 | 文件 | 处置 |
|------|------|------|
| **最终产物（保留）** | `{target}/EVOLUTION.md` | 本地保留，不入库（fresh clone 不可见） |
| **最终产物（保留）** | `{target}/benchmark/metrics.json`（baseline 更新） | 永久保留 |
| **中间产物（清理）** | `{data_root}/.build/report.evolution.json` | 结论已沉淀 EVOLUTION.md 后删除 |
| **中间产物（清理）** | 回归验证 worktree（见 `worktree-sop.md`） | 验证完成后删除，产物不归入当前分支 |

## 清理时机

| 结果 | 操作 |
|------|------|
| 进化通过（verdict=提升） | 更新 EVOLUTION.md + baseline → **删** report.evolution.json → **删** worktree |
| 进化未通过（持平/退化） | 不改 EVOLUTION.md / baseline → **删** report.evolution.json → **删** worktree（无需归档） |
| 分析中止（用户放弃） | **删**所有中间产物，不动 EVOLUTION.md 和 baseline |

## 谨慎优化原则

- 每轮只改**有量化收益的具体问题**（metrics 提升 ≥ evolve_delta），不做「顺便优化」
- 清理前列文件清单，非 CI 环境需用户确认
- 宁可不动，不可改坏：稳定优先于完美

---

## decision-skill 中间产物（扩展）

各 decision-* skill 的 `.build/` 产物遵循统一分类。清理脚本 `scripts/cleanup-builds.py` 按此表执行（Stop hook 自动触发，session-review 前清）。

> **脚本同步约束**：改本表的文件模式 → 须同步改 `cleanup-builds.py` 的 `GUARDED_PATTERNS`/`UNGUARDED_PATTERNS`，并跑 `python3 scripts/cleanup-builds.py --dry-run`（造测试产物放某 `.build/` 直接子）验证实际匹配。防文档-脚本 drift——曾发生 phase/round 命名不一致致脚本死代码（phase 模式匹配不到实际 round.{N} 产物，中间产物从不被清理），grep 查不出此 bug（模式合法但匹配空），须造产物跑脚本才暴露。

| 类别 | 文件模式 | 处置 | 理由 |
|------|---------|------|------|
| 本地（不入库）| verify-report.json | 本地保留 | 最终验证结论（决策沉淀走 ADR） |
| 本地（不入库）| consensus.final.json | 本地保留 | 最终共识（决策沉淀走 ADR） |
| 最终（保留）| lifecycle-decision.json | 永久 | lifecycle 裁决 |
| 最终（保留）| report.review.final.json | 永久 | 最终评审 |
| 最终（保留）| review.pcf.final.json | 永久 | PCF 最终裁决 |
| 最终（保留）| loop-summary.md | 永久 | 全链摘要 |
| 最终（保留）| clarified-requirements.md | 永久 | explore 产物 |
| 快照（保留）| metrics.latest.json | 保留至下次运行 | 末次指标（evolve 采集） |
| 中间（清理）| report.review.round.*.json | 结论入 final 后删 | 评审迭代轮次 |
| 中间（清理）| report.fix.round.*.json | 修复后删 | 修复迭代轮次 |
| 中间（清理）| report.red-team*.json（非 final） | 红队后删 | 结论已入 verify-report |
| 中间（清理）| consensus.round*.proposal.*.json | 收敛后删 | 共识提案 |
| 中间（清理）| consensus.round*.summary.json | 收敛后删 | 共识摘要 |
| 中间（清理）| review.pcf.round.*.json | PCF 裁决后删 | 轮次产物（final 保留，命名约定沿用（pcf-execution-flow 未包含）） |
| 中间（清理）| report.evolution.json | 结论入 EVOLUTION.md 后删 | 评估报告 |
| 本地（不入库）| debates.md | 本地保留 | 共识辩论草稿（决策沉淀走 ADR） |

### 命名约定

- 轮次：`report.{type}.round.{N}.json`（review/fix）
- 红队多轮：`report.red-team.round.{N}.json`（每轮一份，round-based 防多轮覆盖）
- 共识：`consensus.round{N}.proposal.{M}.json` + `consensus.round{N}.summary.json`
- PCF：`review.pcf.round.{N}.json`（轮次，（pcf-execution-flow 未包含））+ `review.pcf.final.json`（最终裁决）
- 最终标识：`.final.json` 后缀
- 跨 skill 隔离：多个 skill 共用同一 `task_dir/.build` 时，最终产物建议带 skill 前缀
  （`report.review.final.{skill}.json`），避免固定名同名互覆盖导致历史产物丢失
  （design-table-spec baseline 曾因此被覆盖；评估引擎已退役，但前缀隔离纪律仍适用）。

### 自动清不适用「需用户确认」门槛

上面「谨慎优化原则」的「非 CI 需用户确认」针对的是**改 skill 文件**的进化操作（删 worktree、改 SKILL.md）。decision-skill 的中间产物是可重建的 JSON 快照（结论已入最终产物），由 `cleanup-builds.py`（Stop hook）自动清，门槛低于 skill 改动，无需逐次确认。`--dry-run` 供手动查看清单。

### PRD .build 不在此列

prd-generator 的 `.build` 由自身 `post_update.py` 管理（manifest/map/plan），命名模式不重叠，`cleanup-builds.py` 不触碰。
