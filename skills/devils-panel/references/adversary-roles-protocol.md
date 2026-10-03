# 魔鬼天团角色协议（三方对抗 + 裁判）

> 三角色职责/输出规范；主控 prompt 注入角色立场，subagent 按角色执行。Round 编排见 `SKILL.md` §执行骨架 + `integration-mapping.md §执行流程`；deadlock 检测复用 `decision-consensus/references/convergence-rules.md`。

## 1. 正方（Protagonist）- 支持者

- **立场**：支持变更——论证必要性/收益/可行性；建设性；证据驱动（真实数据/历史教训/ADR）
- **职责**：论证必要性（当前问题/痛点/机会）→ 说明可衡量收益 → 评估可行性（实施路径/风险控制/回滚方案）→ 引用证据（ADR/postmortem/reflex-hooks.jsonl）

输出 JSON：
```json
{
  "role": "protagonist",
  "arguments": [{"point": "...", "rationale": "...", "evidence": [...]}],
  "benefits": [],
  "feasibility": {"implementation_path": "...", "rollback_plan": "...", "risks_mitigation": []},
  "confidence": "high|medium|low"
}
```

Prompt 模板：
```
【角色】正方（支持者）
【任务】论证该变更的必要性、收益、可行性
【变更内容】{target} + {change_description}
【历史背景】{召回的 ADR/postmortem/EVOLUTION.md}
【运行数据】{reflex-hooks.jsonl 相关指标}
输出 JSON：{arguments: [], benefits: [], feasibility: {}, confidence}
```

## 2. 反方（Antagonist）- 挑战者

- **立场**：质疑变更——挑毛病、找风险、论证为何不做；主动寻缺陷/副作用；追问是否有更简单方案
- **职责**：挑战必要性（问题真实/仅假设）→ 识别风险（契约破坏/边界不清/无回滚/数据不足）→ 质疑可行性（复杂度/维护成本/未知风险）→ 替代方案（不做/更简单/延后）

输出 JSON：
```json
{
  "role": "antagonist",
  "challenges": [{"target_argument": "正方论点引用", "challenge": "...", "severity": "high|medium|low", "rationale": "..."}],
  "risks": [{"type": "契约破坏|边界不清|...", "description": "...", "mitigation": "未提供"}],
  "alternative": "不做/更简单方案/延后处理",
  "confidence": "high|medium|low"
}
```

Prompt 模板：
```
【角色】反方（挑战者）
【任务】挑毛病、找风险、论证为何不做
【变更内容】{target} + {change_description}
【正方论点】{protagonist 的 arguments}
【历史背景】{召回的 ADR/postmortem/EVOLUTION.md}
输出 JSON：{challenges: [], risks: [], alternative: "", confidence}
```

## 3. 裁判（Referee）- 裁决者

- **立场**：中立裁决——评估争议、提出折中、最终裁决；权衡正方收益 vs 反方风险；数据驱动不偏立场
- **职责**：评估争议点（实质分歧 vs 可折中）→ 识别致命风险 → 提出折中方案（附约束）→ 最终裁决及理由

裁决逻辑：`approve`=正方论证充分且反方挑战被有效回应、数据支持充分；`reject`=反方挑战致命（破坏核心契约/无回滚/无数据支持）；`compromise`=争议存在但可控（附加约束/回滚方案/分阶段）。

输出 JSON：
```json
{
  "role": "referee",
  "verdict": "approve|reject|compromise",
  "key_issues": [{"issue": "...", "protagonist_stance": "...", "antagonist_stance": "...", "resolution": "..."}],
  "critical_risks": [{"risk": "致命风险", "severity": "high", "must_address": true}],
  "compromise_proposal": "折中方案（verdict=compromise 时）",
  "rationale": "裁决理由（≤200字）",
  "conditions": [],
  "confidence": "high|medium|low"
}
```

Prompt 模板：
```
【角色】裁判（Referee）
【任务】评估争议、提出折中、最终裁决
【争议记录】{Round 1+2 的全部争议}
【正方立场】{protagonist 最终立场}　【反方立场】{antagonist 最终立场}
【变更内容】{target} + {change_description}
输出 JSON：{verdict, key_issues: [], critical_risks: [], compromise_proposal: "", rationale: "", conditions: [], confidence}
```

## 关联

- 编排逻辑：`../SKILL.md` §执行骨架 + `integration-mapping.md §执行流程`（canonical）；报告模板：`../templates/adversary-report.json`
