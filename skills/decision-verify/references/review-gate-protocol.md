# Review Gate Protocol — 验证门控协议

decision-verify 的迭代验证评分标准、循环规则、PCF 触发条件（特有维度 / 数据源 / must-fix / Schema）。通用机制（评分公式 / 判定逻辑 / PCF 决策空间 / 嵌套 spawn 约束）（review-gate-skeleton 未包含，判定逻辑以本文件特化值为准），主控顶层串行 spawn reviewer/fixer 执行评审，**禁止 background 委托 review-gate**（review-gate agent 仅作协议来源）。

> **正确性与安全性优先**：正确性（40%）与安全性（30%）合计 70% 权重，是本协议最高优先维度。修复排序中正确性 P0 与安全性 P0 并列最高（仅次于必须修复项）。

---

## §1 评分维度

| 维度 | 权重 | 核心关注 |
|------|------|---------|
| 正确性 | 0.40 | 逻辑/状态/数据是否符合预期，无死状态/未定义引用/异常未处理 |
| 安全性 | 0.30 | 认证/授权/注入/越权，信任边界处校验 |
| 规范性 | 0.20 | 命名/格式/引用/结构约定 |
| 完整性 | 0.10 | 覆盖度/清单/场景齐全，无遗漏 |

> code 对象安全性权重提至 0.35，其余维度权重相应调整，见 `verify-mapping.md` 权重表。

---

## §2 数据源映射

decision-verify 的红队为单一 reviewer：review-rule。review-rule 按 `checklist-dimensions.md` 逐项校验 `target_files`，产出 issue（含 check_id / severity:P0|P1 / dimension / location / message）。

review-gate 从 review-rule 的 report 归档：

| 步骤 | 操作 |
|------|------|
| 1 | Read `report.red-team.round.{N}.json`（reviewer agent 输出，{N}=当前轮次） |
| 2 | 按 issue 的 `dimension` 字段归入 4 维（正确性/安全性/规范性/完整性） |
| 3 | severity 已是 P0/P1（review-rule 按 checklist-dimensions 的 severity 映射完成） |
| 4 | 按本协议 §3 标记必须修复项 |
| 5 | 按 §4 公式计算各维度分与加权总分 |

---

## §3 必须修复项（must-fix）

必须修复项独立于评分，存在即不通过（一票否决），不可通过 `accept_with_flags` 豁免。

| 必须修复项 | 标记条件 |
|-----------|---------|
| 安全性 P0（注入/越权/认证缺失） | issue 的 dimension=安全性 且 severity=P0 |
| 反幻觉检出 | exec-review-fixer-blue 报 skipped_no_source（产物有但来源无） |

**规则**：
- 判定优先级（must-fix → 维度底线 → 总分 → PCF）与超轮次 PCF 受限（不可 `accept_with_flags`）骨架未包含，判定逻辑以本文件特化值为准 §判定逻辑 / §PCF 决策空间
- 计入 `report.review.round.{N}.json` 的 `must_fix_count`
- 同时计入所属维度 P0 扣分（不额外扣，但触发一票否决）

---

## §4 评分公式

### 维度分
```
维度分 = max(0, 100 - P0数 × 25 - P1数 × 8)
```
- P0 每个扣 25，P1 每个扣 8，下限 0
- P0/P1 词表为骨架登记的合法特化（骨架未包含，判定逻辑以本文件特化值为准 §合法特化登记），不迁三级词表

### 总分（默认权重）
```
总分 = 正确性分 × 0.40 + 安全性分 × 0.30 + 规范性分 × 0.20 + 完整性分 × 0.10
```
> code 对象用 `verify-mapping.md` 的调整权重（安全性 0.35）。

### 示例
| 维度 | P0 | P1 | 维度分 | 加权 |
|------|----|----|--------|------|
| 正确性 | 1 | 2 | 59 | 59×0.40=23.6 |
| 安全性 | 0 | 1 | 92 | 92×0.30=27.6 |
| 规范性 | 0 | 1 | 92 | 92×0.20=18.4 |
| 完整性 | 0 | 0 | 100 | 100×0.10=10.0 |
| **总分** | | | | **79.6** |

---

## §5 阈值定义

| 参数 | 值 | 说明 |
|------|------|------|
| 通过阈值 | 90 | 总分 ≥ 90 → PASS |
| 临界阈值 | 60 | 首轮 < 60 → CRITICAL，触发 PCF |
| 维度底线 | 80 | 任一维度分 < 80 → FIXABLE（不论总分） |
| 收敛阈值 | 5 | 相邻轮次分差 < 5 → plateau |
| 最大轮次 | 5 | 达 5 轮未通过 → PCF |

**档位特化**（上表为 full 档值；**档位参数在此单源**，decision-verify SKILL.md「验证档位」节只留指针不复写。standard/full 判定逻辑不变；**quick 为骨架轻量评审门在 verify 域的实例**——无评分 pass/fail、蓝队修 1 次+复验 1 轮、不上 PCF 改 escalate_to_user，形态见骨架（未包含）§轻量评审门`）：

| 档 | 最大轮次 | 评分制 | PCF 触发 |
|----|---------|--------|---------|
| quick | 2 | 无评分：pass/fail + must-fix/P0 清单 | 不触发，争议直接 escalate_to_user |
| standard | 3 | 全量表值 | plateau / 修复停滞 / 超轮次（CRITICAL 仅记 score_history 不即时触发） |
| full | 5 | 全量表值+数据集基线必跑 | 全触发（CRITICAL / plateau / 修复停滞 / 超轮次） |

### 判定逻辑

骨架七步判定骨架未包含，判定逻辑以本文件特化值为准 §判定逻辑（must-fix 一票否决 → 维度底线 → 总分 → PCF 升级 → FIXABLE 循环，任何层级不过不被下层掩盖），阈值用本文件 §5 表特化值。本协议新增一条特化：**修复停滞**——round≥2 且本轮 fixed_count==0 → PCF（fixer 能修的已修，防维度底线死循环；fixed_count 源自 report.fix.round.{N}.json）。

---

## §6 PCF 场景

### 触发
| 触发 | 条件 |
|------|------|
| CRITICAL（仅 full；standard 记 score_history 不即时触发） | round==1 且 score<60（0-100 PCF 触发器，非升 main 门——升 main 门见 model-governance.md §1a） |
| plateau / 超轮次 | 骨架未包含，判定逻辑以本文件特化值为准 §判定逻辑（阈值用 §5 档位特化值） |
| 修复停滞 | FIXABLE 态下 fixer 连续轮次 skipped 集合无变化（能修的已修，剩余为不修/无法修，如用户决定接受的规范性 P1）——否则卡在维度底线无止境循环 |

### Proposer 候选
| 候选 | 动作 | 适用 |
|------|------|------|
| fix_targeted | 修复 top-3 P0 后跑最终轮 | 剩余 P0 ≤ 3 |
| accept_with_flags | 接受当前质量，标未解决 | 剩余为可接受取舍**且无 must_fix**；或修复停滞（剩余为不修/无法修的 P1，fixer fixed_count=0） |
| escalate_to_user | 中止，向用户输出明细 | 多维度严重缺陷 |

### Critic 焦点
- 各维度分数趋势、剩余 P0 可修复性、修复引入新问题风险

### Finalizer 范围
骨架未包含，判定逻辑以本文件特化值为准 §Finalizer 约束。

---

## §7 轮次报告 Schema
```json
{
  "round": 1,
  "total_score": 79.6,
  "status": "fixable",
  "must_fix_count": 1,
  "must_fix_items": [{"type":"安全性P0","source":"report.red-team.round.{N}.json","location":"..."}],
  "dimensions": {
    "正确性": {"weight":0.40,"score":59,"p0":1,"p1":2,"floor_check":"fail"},
    "安全性": {"weight":0.30,"score":92,"p0":0,"p1":1},
    "规范性": {"weight":0.20,"score":92,"p0":0,"p1":1},
    "完整性": {"weight":0.10,"score":100,"p0":0,"p1":0}
  },
  "top_issues": [],
  "source_reports": ["report.red-team.round.{N}.json"]
}
```

## §8 最终报告 Schema
```json
{
  "status": "pass|pass_with_flags|fail",
  "final_score": 92.0,
  "rounds_used": 3,
  "must_fix_count": 0,
  "dimensions": {
    "正确性": {"score":90,"p0":0,"p1":1,"floor_check":"pass"},
    "安全性": {"score":95,"p0":0,"p1":1},
    "规范性": {"score":92,"p0":0,"p1":1},
    "完整性": {"score":100,"p0":0,"p1":0}
  },
  "score_history": [79.6, 88.0, 92.0],
  "pcf_triggered": false,
  "pcf_decision": null,
  "unresolved_issues": [{"type":"", "source":"", "location":"", "reason":"<非空，接受理由；空即按未处置返回 FIXABLE>"}]
}
```
- status=pass: must_fix_count==0 且总分≥90 且各维度≥80
- status=pass_with_flags: PCF accept_with_flags 后通过；**unresolved_issues 每条强制带非空 `reason` 字段**（空处置视同未处置，记 must_fix），且 round 间 severity 降级（P0→P1）留痕视同未处置一并计入
- status=fail: PCF escalate_to_user 或策略失败
