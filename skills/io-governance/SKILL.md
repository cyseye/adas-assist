---
name: io-governance
description: "IO 组统管：注入/回传/命名合规审计，预算唯一写者。触发词：I/O 审计/注入预算/回传合规/调整注入上限。"
---

# io-governance · 运行治理部 IO 组统管

职能部门化组织（AGENTOS-MAP §组织架构）运行治理部 IO 组行动实体（归属细节归 AGENTOS-MAP，不复写）。职责=本域**审计+对账+预算写者**，quick 型（主控串行、零 PCF）。协议 canonical=`_shared/io-protocol.md`；数值单源=`_shared/io-budgets.json`。

## 审计（默认动作）

对照 io-budgets.json 逐项核查，产物为压缩索引报告（≤15 行，不落盘）。机械核对半边先直跑 `scripts/io-audit.py`（未包含，本仓主控按本表口径人工直出读数），模型只做语义判读与豁免裁决，不手工复跑：

| 检查项 | 口径 | 数据源 |
|---|---|---|
| 注入留痕覆盖 | 各注入面是否埋点 reflex-hooks.jsonl | reflex-hooks.jsonl 行的 hook 字段分布 |
| 注入体量 | 召回条数/摘要字数/PENDING 行数/周报行数是否在预算内 | 近窗口 jsonl 抽样 |
| 回传合规 | spawn 回传是否带 status/file_path/计数/risks≤3 | 近会话 transcript 抽样（≤3 个） |
| 命名契约 | 新增报告是否按 `{skill}.round.{N}/*final*` 契约 | .build/ 目录 glob |
| spawn prompt 体量 | >100 行内联是否已标注降级路径 | 最近 spawn prompt 字节数（探针：usage-stats） |

零违例也须打印分母（查了几项/几条），零信号≠通过。

## 预算写者

调整数值：改 io-budgets.json 对应键 + `_history` 追加一行（ts/action）。数值变更属行为改动，须用户确认后执行；涉及 hook 脚本硬编码同步的，登记「两处同改」义务再改。

## 边界

- 不建探测器 hook、不做实时拦截（组织裁决：可执行条款+审计入口足够）。
- 叙述性 I/O 原则不在本 skill 管辖（留原处：runtime-conventions/handoff-modes 四层契约；model-governance 未包含）。

## 资源

| 文件 | 用途 |
|---|---|
| `_shared/io-budgets.json` | 数值单源（本 skill 唯一写者） |
| `_shared/io-protocol.md` | 底层协议 canonical |
| `_shared/runtime-conventions.md` | 运行时公共约定（引用不重写） |
