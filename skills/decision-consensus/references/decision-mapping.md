# 共识→PCF 编排映射

> decision-consensus 复用 PCF 三件套（pcf-proposer / pcf-critic / pcf-finalizer），本文件定义「如何编排」与「schema 如何转写」。**不修改 PCF**（符合「不新建 / 不改 agent」原则），主控做转写。术语对齐 SKILL.md。

## 编排映射

### 每轮 proposer 数

默认 5 个 pcf-proposer（视角集与裁剪规则单源=`delphi-protocol.md §视角裁剪规则`）；**并行 spawn**（一条消息多 Agent 调用，foreground），各 proposer 互不可见。

### 视角→proposer 赋值

spawn pcf-proposer 时，prompt 注入：

```
【分歧上下文】{问题描述 + 各方立场}
【你的视角】{视角名}（架构 / 安全 / 性能 / 用户 / 成本）
【你的关注点】{该视角关注点，见 delphi-protocol.md}
【上轮反馈】{R>1 时注入，见 delphi-protocol.md 反馈格式}
【任务】从{视角名}视角，针对分歧提出 1-2 个候选方案，
        输出 {candidates:[{id, action, pros, cons}]}
```

### critic 触发条件

- **收敛后**残余分歧 ≥ 2 → spawn pcf-critic 挑战残余分歧
- 残余 < 2 → 跳过 critic，直交 finalizer
- critic 输入：收敛后的残余分歧 + 各方立场；输出 `{issues:[{candidate, severity, issue, location}]}`

### finalizer 触发条件

- **总触发**（收敛后必跑）→ spawn pcf-finalizer
- 输入：所有轮 summary + critic 的 issues（若有）
- 输出：`{decision, confidence, reason, residual_risks[]}` → 直接写为 consensus.final.json

## ★schema 转写规则（核心）

### 张力

consensus 期望的 proposal schema：`{role, proposal, rationale, confidence}`
pcf-proposer 实际输出：`{candidates:[{id, action, pros, cons}]}`

结构不同。**不修改 PCF**，主控做转写。

### 转写规则（取 candidates[0]）

```
role       = spawn 时赋予的视角名（架构 / 安全 / 性能 / 用户 / 成本）
proposal   = candidates[0].action
rationale  = "优点：" + candidates[0].pros + "；缺点：" + candidates[0].cons
confidence = "medium"（pcf-proposer 无置信度字段，默认；
              多轮趋同可主控上调为 "high"，强制收敛标 "low"）
```

### 完整转写示例

**输入**（某视角 pcf-proposer 输出）：
```json
{
  "candidates": [
    {
      "id": "A",
      "action": "采用 Redis，支持分布式与持久化",
      "pros": "高性能、支持集群、数据可持久化",
      "cons": "增加运维成本、需额外资源"
    }
  ]
}
```

**输出**（主控转写为 consensus.round{R}.proposal.{i}.json）：
```json
{
  "role": "架构",
  "proposal": "采用 Redis，支持分布式与持久化",
  "rationale": "优点：高性能、支持集群、数据可持久化；缺点：增加运维成本、需额外资源",
  "confidence": "medium"
}
```

### 为何取 candidates[0]

pcf-proposer 设计为提 1-2 个候选（A/B）。Delphi 每视角应给**本视角的立场方案**（非多候选对比）。取 candidates[0] 作为该视角主立场；若 proposer 给了 2 个候选，candidates[1] 默认忽略（保持转写简单；主控也可按质量择优，但默认取 [0]）。

## 产物 schema 对齐

proposal 字段逐项转写规则见上文 §转写规则（取 candidates[0]）；summary 字段主控自产（convergence_score 见 convergence-rules.md）；`consensus.final.json` 与 pcf-finalizer 输出 schema 完全兼容，无需转写。

## metrics 采集

skill 执行末尾，主控把以下计数写入 .build/metrics.latest.json，供人工 current-vs-baseline 比对（自动评估链已退役；共识度越大越好，其余三项越小越好）：

```json
{
  "rounds": "<实际收敛轮次>",
  "convergence_score": "<最后轮 summary 的 convergence_score>",
  "residual_risks_count": "<consensus.final.json 的 residual_risks 数组长度>",
  "overturn_rate": "<人工填，决策后续被推翻的比率，%>"
}
```

## 关联

- 多轮协议与视角裁剪：见 delphi-protocol.md
- 收敛判定与共识度公式：见 convergence-rules.md
