---
name: io-governance
description: "IO 组统管：注入/回传/命名合规审计，预算唯一写者。触发词：I/O 审计/注入预算/回传合规/调整注入上限。"
---

# io-governance · 运行治理部 IO 组统管

负责 I/O 审计、对账与预算维护。主控串行执行；协议见 `skills/_shared/io-protocol.md`，数值单源为 `skills/_shared/io-budgets.json`。

## 审计（默认动作）

对照 io-budgets.json 核查本次显式提供的输入、回传和产物。按实际文件或消息计数，未提供的数据标为 no_data，不假设存在自动注入日志或审计工具。

| 检查项 | 口径 | 数据源 |
|---|---|---|
| 委派输入 | 必要目标、文件、写域、验收及 spawn_prompt 预算 | 本次委派消息 |
| 回传合规 | 通用 schema 或角色专用 JSON、subagent_return 预算 | 本次实际回传 |
| 命名契约 | 产物命名与协议一致、路径可访问 | 本次产物文件 |
| 长输出 | 完整证据可访问、摘要未代替反例 | 本次日志和摘要 |

零违例也须打印分母（查了几项/几条），零信号≠通过。

## 预算写者

调整数值：改 io-budgets.json 对应键 + `_history` 追加一行（ts/action）。数值变更属行为改动，须用户确认后执行；核查现有消费者与受影响题面后复验。

## 边界

- 不建探测器 hook、不做实时拦截（组织裁决：可执行条款+审计入口足够）。
- 叙述性 I/O 原则不在本 skill 管辖（见共享 runtime-conventions 与 io-protocol）。

## 资源

| 文件 | 用途 |
|---|---|
| `_shared/io-budgets.json` | 数值单源（本 skill 唯一写者） |
| `_shared/io-protocol.md` | 底层协议 canonical |
| `_shared/runtime-conventions.md` | 运行时公共约定（引用不重写） |
