# 对抗评审接入

仅在当前任务授权和宿主工具支持下执行。读取 SKILL.md 的分级与角色协议，体系关键争议需要真实独立上下文；同一 agent 的多视角只标分析。

| 接入点 | 输入 | 消费与后续 |
|---|---|---|
| decision-lifecycle | 资产存废方案、依赖、证据 | 输出取舍，按授权实施或保留未决 |
| skill-evolution | 根因、影响面、退化反例、候选 | 检查是否回应根因，定向回归 |
| effect-governance | 用户明确要求的效果审计与证据 | 反驳结论、核口径，不自动改规则 |
| decision-record | 待记录决策及其裁决来源 | 记录真实裁决，不以记录代裁决 |

主控核输入并限制读写域，正方提出论证，反方给可证伪挑战，裁判独立裁决；不能在裁判输入预设推荐。未满足必要条件停止依赖动作，不补造来源。

## 交接和模板消费者

每轮按 templates/adversary-summary.json 维护：round、round_status（continue/converged/deadlock）、protagonist_args、antagonist_challenges、unresolved_issues、converged_issues、critical_issues。关键问题未解决不能以无挑战或轮数耗尽判通过。

最终报告按 templates/adversary-report.json 维护：target、change_type、adversary_mode、timestamp、rounds、final_verdict、protagonist_summary、antagonist_summary、unresolved_issues、referee_rationale、compromise_conditions、linked_adr、metrics。

final_verdict 为 approve/reject/compromise；protagonist_summary 包含 key_arguments、benefits、feasibility、confidence；antagonist_summary 包含 key_challenges、risks、alternative、confidence。metrics 中 rounds_to_convergence、issues_raised、issues_resolved、consensus_score 只记录实际可得数值，不为填表制造共识。

零挑战也须裁判核证；reject 保留失败和下一步，compromise 逐条列条件与复验。linked_adr 仅在真实建立决策记录后填写。结果按共享 I/O 协议回传，原始报告并入当前任务证据，必要消费者结束前不清理。
