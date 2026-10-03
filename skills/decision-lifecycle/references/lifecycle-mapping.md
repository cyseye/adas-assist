# 生命周期映射

> 信号 → 门槛 → 风险 → PCF → 决策 的编排映射，以及与 explore / skill-evolution 的转交边界。

## 编排链路

执行链路单源=SKILL.md 执行流程表（Step 0-8；Step8 建议动作等用户确认、不自动执行的克制单源也在该表）。

## 与 decision-explore 的转交

| explore 侧 | lifecycle 侧 |
|-----------|--------------|
| Step7 轻量识别信号（同类 prompt≥3 / 触发冲突等） | 正式归类 + 门槛 + 风险 + PCF |
| 仅提示「建议转 decision-lifecycle」 | 下结论 + 产出 lifecycle-decision.json |
| 不下增删结论，不写决策产物 | 唯一的增删决策出口 |

> explore 是信号「探头」，lifecycle 是增删「裁决庭」。explore 不再自己下增删结论，避免双份维护与口径不一。

## 与 decision-consensus / decision-verify 的区别

| skill | 处理对象 | 与 lifecycle 关系 |
|-------|----------|-------------------|
| consensus | 方案分歧的多角色裁决 | lifecycle 的 PCF 内部已含多角色辩论，不外部调用 consensus |
| verify | 产物质量验收 | verify 不触发增删；若 verify 反复暴露某 skill 结构问题，可作为 lifecycle 的信号来源之一 |
| record | 决策沉淀为 ADR | lifecycle 重大增删结论可转 record 沉淀 ADR（决策可追溯） |

## 产物字段映射（lifecycle-decision.json）

| schema 字段 | 来源 Step | 取值约束 |
|-------------|-----------|----------|
| `signal.type` | Step1 | `new` / `split` / `merge` / `none` |
| `signal.evidence` | Step0-1 | 具体观察记录（≥1 条） |
| `gate.threshold_met` | Step2 | bool |
| `gate.reason` | Step2-3 | 门槛校验 / 不动清单命中说明 |
| `gate.risk` | Step4 | `low` / `mid` / `high` |
| `pcf.triggered` | Step6 | risk=低时 false，否则 true |
| `pcf.decision` | Step6 | `approve` / `reject` / `escalate` / null |
| `verdict` | Step5-6 | `建议新增` / `建议拆分` / `建议合并` / `不动` |
| `action` | Step8 | 仅建议文案，等用户确认 |
| `residual_risks` | Step6-7 | finalizer 残余风险或迁移成本 |

## metrics 采集（人工复盘留痕）

主控 Step7 写 `{task_dir}/.build/metrics.latest.json`：

```json
{
  "decision_quality": "<0-1: 过程合规性——信号证据+门槛+风险+verdict+PCF 字段均非空的完整性>",
  "restraint_rate": "<0-1: 判定为「不动」的比例，越高越克制>",
  "user_adoption_rate": "<0-1: 用户确认采纳的建议动作占「给出建议」总数的比例；sample≥10 才可靠，<50% 触发人工审查>",
  "escalation_rate": "<0-1: PCF finalizer confidence=low 而 escalate_to_user 的比例，越高说明决策不确定性越大>"
}
```

> lifecycle 为低频决策 skill，执行对象每次不同、无固定测试集——参考 skill-evolution 门控，metrics 仅做趋势记录，baseline 留 null 待真实使用回填，不强跑回归。
