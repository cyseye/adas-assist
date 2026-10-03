---
name: decision-lifecycle
description: "skill 资产治理/skill 增删判断/skill 拆分合并（含口头：拆分下/专注各自职责/合并到一起）。门控+量化门槛，主 agent 交互式（不 spawn），高风险走 PCF，克制不自动执行。"
---

# decision-lifecycle · skill 资产治理

> 定位：决策体系「skill 资产治理」模式。判断 skill 体系的存废与边界（新增 / 拆分 / 合并）。与 skill-evolution 互补：本 skill 管「该不该有 / 该不该拆合」，evolution 管「怎么变得更好」。
> 流程：采集信号 → 量化门槛 → 风险评级 → PCF 裁决 → 产出增删建议（不自动执行）。

## 运行约定

- `{task_dir}` = 当前任务工作目录（默认 cwd）；工作目录 `{task_dir}/.build/`（须加入 .gitignore）
- 复用现有 agent（不新建）：PCF 三件套（`pcf-proposer`/`pcf-critic`/`pcf-finalizer`）；产物命名：`{task_dir}/.build/lifecycle-decision.json`

## 何时启用

**启用**：用户说「评估要不要新增 / 拆分 / 合并 skill」「skill 体系评估」，或 `decision-explore` Step7 转交，或主 agent 识别到反复绕过 / 拼凑现有 skill（≥3 次干预）。

**不启用**：现有 skill 的内容优化（规则 / 模板改进）→ `skill-evolution`；方案分歧多角色裁决 → `decision-consensus`；需求模糊需澄清 → `decision-explore`；产物质量验收 → `decision-verify`。

## 用户输入

- 评估对象（必需）：待评估的现有 skill 名 / 「新建场景」描述
- 触发信号（可选）：用户主动描述的重复模式 / 痛点，缺则主控从 registry 与观察中采集；拟议动作（可选）：用户倾向的新增 / 拆分 / 合并方向，缺则主控按信号归类

## 执行流程

| Step | 动作 | 工具 / 详情 |
|------|------|------------|
| 0 | 信号采集 + 召回 | 来源：用户主动 / explore 转交 / registry 累积 / 主 agent 观察；逐条记录证据；**读 `~/.claude/decisions/KNOWLEDGE.md` 评估待评估 skill 与既有知识沉淀的关系**（按 `standards/common/knowledge-protocol.md` 标准词表匹配相关 ADR/lifecycle 决策，判断是否已有相关裁决） |
| 1 | 信号归类 | 按 `references/lifecycle-signals.md` 匹配：新增 / 拆分 / 合并 / 无 |
| 2 | 量化门槛校验 | `lifecycle-signals.md §量化门槛`（复用率≥2 / 可定义指标 / 不重叠 / 拆后可测不降）；投委会语境（立项/投资机会）的收益量化模板见 `~/.claude/skills/_shared/investment-committee.md §收益量化模板`（未包含，本仓跳过投委会语境） |
| 3 | 不动清单过滤 | `lifecycle-signals.md §不动清单` → 命中即判定「不动」，跳 Step 7 |
| 4 | 风险评级 | `references/gate-rules.md §3`：新增=中、拆分/合并=高、仅识别=低；**追认禁令三条件 grep（org-formations U11）**：涉及对已静默删改的 skill「事后追认/合并」时，逐条核 `git log` 有变更 + 引用计数（U1 双 grep 路径全集）归零 + 无 revert commit——三条件齐即禁追认，补 revert 不洗白 |
| 5 | 决策表判定 | `lifecycle-signals.md §决策表`：建议动作 / 不动（记 memory）；**建议新增时拟名按组前缀制/见名知意/查重顺序校验**（skill-naming.md 本仓未包含，以此三查为人工口径），不合规范的名字不进建议 |
| 5.5（建议时）| 根因+影响面前置 | 仅建议动作时执行，判定「不动」跳过（对齐 `_shared/evolution-discipline.md §根因与影响面前置`）：① 一句话根因——信号为何发生、现有形态为何不行；② 影响面全量排查——拟动 skill 名的全仓引用点（各 SKILL.md 转交边界 / KNOWLEDGE.md / 全局调用台账 invocations.jsonl）精确 grep 可下放 sonnet 执行 agent，但回传必须含**命令原文+命中清单**（可复验）；语义影响面判断仍归主控——调研结论须经交叉验证（假阳性教训在案）；L1（仅识别）一句话豁免，L2+（跨 skill 拆合）全量四步 |
| 6（建议时）| PCF 辩论 | 风险中/高走 PCF：串行 spawn `pcf-proposer`→`pcf-critic`→`pcf-finalizer`（文件驱动，见 `references/gate-rules.md §4` + `~/.claude/skills/_shared/pcf-execution-flow.md`）；**Step 5.5 根因链+影响点清单并入提案材料（pcf-proposer 必读，提案不回应根因即 fail；清单即 pcf-critic 检查面）**；**L2+ 体系变更并触发 devils-panel**（PCF 论方案优劣，devils-panel 反方挑战"为何不做"——按 `devils-panel/references/integration-mapping.md 接入点1` 分档：L2 单轮快审/L3 完整对抗，报告作为裁决输入，正方材料复用提案不重复 spawn） |
| 7 | 产出 | 按 `templates/lifecycle-decision.json` schema 写 `{task_dir}/.build/lifecycle-decision.json` + `metrics.latest.json`（见 `references/lifecycle-mapping.md §metrics`） |
| 8 | 收尾 + 沉淀 | **建议动作等用户确认，不自动新建 / 拆分 / 合并**；按 `standards/common/knowledge-protocol.md` 索引 schema 更新 `~/.claude/decisions/KNOWLEDGE.md`：lifecycle 决策索引条目（type=lifecycle，tag 节按协议词表主题归属，关联待落地 ADR） |

## 输出规范

产物 `lifecycle-decision.json` schema（字段来源见 `lifecycle-mapping.md §产物字段映射`）：

```json
{
  "skill": "decision-lifecycle",
  "target_skill": "<被评估 skill 名，新建场景留空>",
  "signal": { "type": "new|split|merge|none", "evidence": ["..."] },
  "gate": { "threshold_met": true, "reason": "...", "risk": "low|mid|high" },
  "pcf": { "triggered": false, "decision": "approve|reject|escalate|null", "confidence": "..." },
  "verdict": "建议新增|建议拆分|建议合并|不动",
  "action": "<克制：仅建议，等用户确认>",
  "residual_risks": ["..."]
}
```

## 降级策略

> 通用失败降级（空输入/用户全拒绝/上游产物缺失/spawn 失败）见 `standards/common/skill-failure-protocol.md`，本节仅列 lifecycle 特有项。

| 场景 | 处理 |
|------|------|
| 信号证据不足（<2 次重现） | 判「观察期」，记 memory，verdict=不动 |
| 建议动作但根因/影响面给不出 | 判「观察期」记 memory，verdict=不动，不硬凑根因 |
| 无法定义可量化指标 | 判「不适合建 skill」，verdict=不动 |
| PCF agent spawn 失败 | 重试 1 次→仍失败 `escalate_to_user`，不静默下结论 |
| 触发条件与现有 skill 重叠无法区分 | 判「不动」，建议走 skill-evolution 优化现有 skill 触发边界 |
| PCF reject 新增/拆分/合并但原始痛点仍存 | 不阻塞当前任务；提议两路：① 走 skill-evolution 优化现有 skill 缓解痛点；② 记 registry 待人工决策 |

## 产物生命周期

- `lifecycle-decision.json` 落 `{task_dir}/.build/`（运行时产物本地保留；结论转 ADR 时 ADR 落 decisions/ 分层入库）
- `.build/` 中间 PCF 辩论产物（`.build/review.pcf.round.{N}.json`）评估后清理
- 建议动作落地（用户确认新增 / 拆分 / 合并）后，可转 `decision-record` 沉淀 ADR

## 资源

| 文件 | 用途 | 读取 |
|------|------|------|
| `references/lifecycle-signals.md` | 信号清单 + 量化门槛 + 不动清单 + 决策表 | 全量 |
| `standards/skill-naming.md` | skill 命名规范（本仓未包含；Step 5 拟名按组前缀/见名知意/查重人工口径） | 新增场景 |
| `references/gate-rules.md` | 接入前提 / 触发条件 / 风险评级 / PCF 触发 / 与 evolution 边界 | 全量 |
| `references/lifecycle-mapping.md` | 编排链路 + 转交边界 + 产物字段映射 + metrics 采集 | 全量 |
| `~/.claude/skills/_shared/pcf-execution-flow.md` | PCF 三件套执行流（共享） | 全量 |
| `templates/lifecycle-decision.json` | 产物 schema | 按需 |

## 反模式

| 禁止 | 正确做法 |
|------|---------|
| 自动新建 / 拆分 / 合并 skill | 仅建议，等用户确认后才落地 |
| 单次偶发信号就下结论 | 需 ≥2 次重现或明确量化门槛 |
| 把内容优化当增删；与 decision-explore 双份维护增删逻辑 | 内容优化走 skill-evolution 不归本 skill；explore 只识别信号转交，裁决归本 skill |
| 不走 PCF 直接建议拆分 / 合并 | 拆分 / 合并为高风险，须经 PCF 裁决 |
| 只给拆合建议不给根因链+影响面 | 必附（Step 5.5），提案材料同 PCF 输入——表面症状不得直接成为改动方案 |
| 拆合提案与已知失败反模式撞型（T120，2026-09-28） | 提案前 grep `~/.claude/.state/evolution-pool/anti-patterns-<当月>.md` 签名对账，命中即否决并附锚转登记；新增反模式随轮追加（锚义务同失败证据断言门） |
