# adas-assist

adas-assist：面向 Claude Code 的自进化元层体系：保留自进化闭环（反射层八脚本+进化宿主）、决策体系（record/verify/improve 三件+explore/consensus/lifecycle/devils-panel 配套）与治理族五件。clone 即用，零本机基建依赖。

## 项目定位

- 本仓 = 聚焦核心闭环。
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

## 自进化闭环说明

闭环五环：**信号采集**（hooks 自动落 invocations/PENDING）→ **周评估**（`skills/skill-evolution/scripts/weekly-eval.py` 出报告+超线信号）→ **分档消化**（`/evolve` 路由：low 自动/mid 批量确认/high AskUser）→ **效果回填**（主控对账 expect/measured）→ **沉淀留痕**（EVOLUTION/ADR/KNOWLEDGE）。全环节只依赖仓内落盘数据，无外部通道也可运转；外参调研为可选增强（机制占位）。
