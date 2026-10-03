# adas-assist

adas-assist：面向 Claude Code 的自进化元层体系：保留自进化闭环（反射层八脚本+进化宿主）、决策体系（record/verify/improve 三件+explore/consensus/lifecycle/devils-panel 配套）与治理族五件。clone 即用，零本机基建依赖。

## 项目定位

- 本仓 = 聚焦核心闭环，**只保留重点功能**（见下「已裁剪清单」）。
- 架构图（三块）：

```
+--------------------------------------------------------------+
|                    反射层（hooks 八脚本）                      |
|  SessionStart 注入 / Stop 自审+清理 / UserPromptSubmit 知识召回|
|  PostToolUse 采集                                             |
+------+-----------------------------------------------+-------+
       |                                               |
       v                                               v
+------------------+    触发/指令     +------------------------------+
| 决策三件 skills/  | <-------------> | 进化宿主                      |
| decision-record  |                 | skill-evolution（SKILL.md    |
| decision-verify  |                 | +脚本八件+周评估 weekly-eval）|
| decision-improve |                 | /evolve 多方向轮快捷入口       |
+--------+---------+                 +---------------+--------------+
         |                                           |
         v                                           v
+--------------------------------------------------------------+
| 知识层：decisions/（KNOWLEDGE 索引+ADR+复盘台账）             |
|         memory/（用户画像）  standards/（安全+知识协议）       |
+--------------------------------------------------------------+
```

## 目录结构

```
CLAUDE.md            用户级指引（会话注入件，≤25 行）
bootstrap/           hooks 接线模板（跨机）+ settings 迁移模板
commands/            os / evolve 快捷入口
standards/           安全协议 + common 知识协议五件
skills/              决策三件 + skill-evolution + _shared 协议库
scripts/             adr-mdcheck.py（ADR 机械校验）
decisions/           KNOWLEDGE 索引+ADR+postmortems（运行时数据，不入库）
memory/              用户画像（运行时数据，不入库）
```

## 新机接入三步

> **部署位置硬约束**：hooks 接线模板按 `$HOME/.claude/...` 解析，**本仓仅支持 clone 到 `~/.claude`**；clone 到其他目录时反射层会静默失效（Claude Code 跳过不存在的 hook 脚本）。
> 依赖：`jq`（brew install jq）。

1. `git clone <本仓> ~/.claude`（已有 `~/.claude` 时先备份迁移）。
2. 合并反射层接线（全新机器无 settings.json 时 `test -f` 兜底）：
   ```bash
   test -f ~/.claude/settings.json || echo '{}' > ~/.claude/settings.json
   cp ~/.claude/settings.json ~/.claude/settings.json.bak
   jq -s '.[0] * .[1]' ~/.claude/settings.json ~/.claude/bootstrap/settings.hooks.json > /tmp/settings.json && mv /tmp/settings.json ~/.claude/settings.json
   ```
   （env/apiKey 等本机配置不随模板，按需自配；可参照 `bootstrap/settings.migrate.json`。）
3. 重启 Claude Code 会话——SessionStart 注入、Stop 自审、知识召回等反射层即生效。

## 已裁剪能力清单

### 本轮裁剪（2026-10-01）

| 能力 | 状态 |
|---|---|
| rules/ 全局常驻规则四件（表达/工程/调研/触发映射） | 删；个人风格件非重点功能 |
| agents/ 扩展成员（审计族/task-driver 等治理编排 agent） | 删；仅留 PCF 三件套+review-rule（skill 内引用，主控 Read 后自演不按名 spawn） |
| BLUEPRINT.md 战略蓝图 | 删 |
| 治理族 skill（model/session-search/arch-governance 等 7 件） | 删；io/effect/memory/info/finish-check 五件随仓（未随仓脚本已在 SKILL.md 标注人工口径） |
| decision-explore/consensus/lifecycle/devils-panel | 随仓保留（决策体系配套）；重度编排（PCF spawn 链）主控自演 |
| 反射层扩展脚本（compact-events/daily-archive/usage-stats/g1-outbound-guard/collect-all-tools/surge-stop-gate 等） | 删；只留八脚本（含 cc-commit-gate/t38-settings-guard） |
| os-report 快捷入口 / commands 扩展 | 删 |
| 脚本 io-audit/model-call-audit/retention-gc/meta-regression/glm-pollution-probe/finish_check/expression-eval/rules_audit/worktree-evolve.sh | 删；脚本只留 adr-mdcheck.py |
| 数据件 skill-evolution/registry/token-baseline.json（expect/measured 台账） | 删；主控按周评估报告对账 |
| standards 扩展（skill-design/skill-naming/automation-protocol/cache-hygiene/model-governance） | 删 |
| _shared 扩展协议（org-formations/pattern-router/pcf-execution-flow/review-gate-skeleton/handoff-modes/assessment-protocol/socratic-inquiry/investment-committee/quota-tracker，及触发路由表、表达体系规范） | 删 |
| io-budgets.json 无读者键组（session_relay/compaction_tiers/main_tier_drift/bash_output 等） | 删，保持 JSON 合法 |

### 首轮分发裁剪（沿用）

| 能力 | 状态 |
|---|---|
| 外部检索通道 | 未配置；外源判定一律 confidence=低并标注无外检通道，内建 WebSearch 如可用可用作降级 |
| 资讯探针 | 未包含；外参轮改为「内建 WebSearch 如可用，否则跳过」 |
| 本机定时调度 | 未包含；周评估由会话触发，不内置 launchd/cron |
| 宿主扩展协作机制 | 未包含；跨机/宿主侧扩展的协作接口不随分发 |

## 自进化闭环说明

闭环五环：**信号采集**（hooks 自动落 invocations/PENDING）→ **周评估**（`skills/skill-evolution/scripts/weekly-eval.py` 出报告+超线信号）→ **分档消化**（`/evolve` 路由：low 自动/mid 批量确认/high AskUser）→ **效果回填**（主控对账 expect/measured）→ **沉淀留痕**（EVOLUTION/ADR/KNOWLEDGE）。全环节只依赖仓内落盘数据，无外部通道也可运转；外参调研为可选增强（机制占位）。
