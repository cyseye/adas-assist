# Skill 失败降级协议

> 各 decision-* skill 共用的失败降级模式。各 skill §降级策略 引用本文件，不重复写。
> 目标：空输入/全拒绝/产物缺失/spawn 失败 四类常见失败都有确定路径，不静默、不阻塞、不悬空。

## ① 空输入 / 必需参数缺失

用户直接回车、给空字符串、缺必需参数：
- 提示「必需参数 X 缺失，请提供」一次
- 仍空 → 取合理默认（若存在，如 verify 对象 → generic）或转显式假设记录
- 连续 3 次无有效输入 → `[INFO]` 记录 + 退出本 skill（不阻塞会话），建议用户补全后重试

## ② 用户全拒绝 / 无响应

AskUserQuestion 连续拒绝回答所有提问（explore 提问、improve 事实收集、record 确认等）：
- 未答项全部转显式假设（按各 skill 假设协议记录），不编造
- 关键决策点拒绝 → 标 `[BLOCKED]` + escalate_to_user，不强行下结论
- 拒绝率 >50% → 标 `[LOW_CONFIDENCE]`，强烈建议转 consensus 或人工确认后再推进

## ③ 上游产物缺失（跨 skill 转交兜底）

转交入口（consensus→record、lifecycle→record、verify→improve 等）必做前置检查：
- 检测必需上游产物是否存在（如 record 检查 consensus.final.json、improve 检查 verify-report.json）
- 缺失 → `[ERROR]` 硬失败 + 列出缺失项 + 回溯建议（「走 decision-consensus 共识裁决」）
- **禁止静默继续**：下游不能在缺上游时凭空填充字段

## ④ Agent spawn 失败

subagent（reviewer/fixer 类，主控自演时跳过本条）spawn 失败：
- 重试 1 次
- 仍失败 → 降级为主控代行（标注 `主控代行:spawn失败`）或 escalate_to_user
- proposer/critic 并行 spawn 失败率 >30% → 中止本轮 + 提示减少视角或重试，不取残缺结果

## ⑤ 级联失败（连续失败不悬空）

任一环节失败到无法自动恢复 → 标 `[BLOCKED]` + 记 `recovery_action`（回溯上游重跑 / 人工介入）+ 写 PENDING 跟进。上游产物缺失见 §③，spawn 失败见 §④，不在此枚举每个边缘组合。

## 通用原则

- 所有降级必须在产物（metrics/registry/最终 artifact）留痕，便于主控/人当下读产物时追溯。降级是会话内当下处理（hard-fail 阻断 / 主控代行 / escalate），不依赖 session-review 事后扫描；session-review 只收体系级跨会话信号（dead-skill / stale-eval / verify-must-fix），二者分层不混淆
- 降级 ≠ 失败：是「带约束地继续」，约束必须显式标注
- 静默吞错是反模式：异常要么处理留痕，要么 escalate，绝不消失
