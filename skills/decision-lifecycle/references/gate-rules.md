# 增删门控规则

> **原则**：增删要克制，默认不动；不合适宁可不做。稳定优先于完美。信号与门槛见 `lifecycle-signals.md`，本文件定义接入前提、触发时机、风险评级与 PCF 触发条件。
> **canonical 指针（2026-09-25 C1 复核）**：通用门控（触发原则/不动清单/风险评级基座）单源 `skills/_shared/evolution-discipline.md`；本文件仅保留**增删特化差分层**（§2 触发源/§3 增删风险表/§4 PCF），与 canonical 冲突时以 canonical 为准——本件系特化非副本，禁整体并入（C1 证伪修正：与 evolution-discipline §70 判定维度不同）。

## §1 接入前提（判断前须满足）

- 待评估对象可观测：有触发日志、调用记录或主 agent 的明确观察（非凭空猜测）
- 新增场景须能定义可观测效果指标（否则无法后续评估进化）
- 拆分 / 合并对象须存在可对比的 metrics（验证拆 / 合后质量不降）

> 不满足 → 无法量化评估 → 标「观察期」，记 memory 待数据积累，不下结论。

## §2 触发条件（仅以下情况启动，**非每次执行**）

- 用户明确要求「评估要不要新增 / 拆分 / 合并 skill」
- `decision-explore` Step7 检测到信号，转交本 skill 做正式判断
- registry 累积数据出现明确模式（同类 prompt ≥3 次重现、反复误路由）
- 主 agent 在执行中反复绕过 / 拼凑现有 skill（≥3 次干预信号）→ **提议是否评估，等用户确认后才启动**

## §3 风险评级（量化 PCF 触发依据）

| 等级 | 判定（增删特化） | 处置 |
|------|------------------|------|
| 低 | 仅识别信号、无建议动作 / 建议记 memory | 直接出结论，不走 PCF |
| 中 | 建议**新增** skill（只增不改现有，可回退） | 走 PCF 辩论，需 metrics 可定义 |
| 高 | 建议**拆分 / 合并**（动现有 skill 边界，影响路由与产物） | 走 PCF 辩论 + 须验证拆 / 合后 metrics 不降 |

## §4 PCF 触发条件

风险为中 / 高且决策表判定为「建议动作」时触发 PCF（复用 `_shared/pcf-execution-flow.md`）：

- proposer：给出「增 / 拆 / 合」的具体方案 + 收益
- critic：挑战方案漏洞（路由冲突、metrics 下降、职责塌缩、维护成本）+ severity
- finalizer：裁决 `approve` / `reject` / `escalate_to_user`

> 风险为低（仅识别 / 记 memory）不触发 PCF，直接输出「不动」结论。
> `confidence=low` 时 finalizer 须 `escalate_to_user`，不自动 approve。

## §5 与 skill-evolution 的边界

| 维度 | decision-lifecycle | skill-evolution |
|------|--------------------|-----------------|
| 对象 | skill 的**存废与边界**（新增 / 拆分 / 合并） | 现有 skill 的**内容进化**（规则 / 模板优化） |
| 动作 | 改 skill **体系结构** | 改 skill **内部规则** |
| 评估 | 信号 + 门槛 + 风险 + PCF | metrics 双阈值 + 回归 |
| 关系 | 先判断要不要增删 → 增删后交给 skill-evolution 持续进化 | 接收已存在的 skill 做内容优化 |

> 一句话：lifecycle 决定「该不该有这个 skill / 该不该拆合」，evolution 决定「这个 skill 怎么变得更好」。两者串联，不重叠。

## §6 评估监控（轻量，不接入 evolution 回归）

> lifecycle 不满足 skill-evolution「固定测试集 + 客观正误」接入前提，故**不跑产物分回归**；仅记录轻量过程信号趋势，baseline 留 null（见 `lifecycle-mapping.md` §metrics）。以下阈值触发**人工审查**，不自动触发 evolution：

| 信号 | 阈值 | 动作 |
|------|------|------|
| 采纳率 `user_adoption_rate` | <50% 且 sample≥10 | 人工审查建议质量（是否误动 / 误不动） |
| 过程合规 `decision_quality` | <80% | 修复流程（信号采集/门槛/PCF 字段缺失），不动 PCF 裁决逻辑 |
| 升级率 `escalation_rate` | 持续偏高 | 复查门槛/不动清单是否过严，致 finalizer 频繁 escalate |

> 三类信号均**人工介入**，克制优先：lifecycle 评估目的是发现流程退化，而非自动演进规则（规则演进归 skill-evolution）。
