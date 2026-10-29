---
name: info-collection
description: "维护本仓采集格式、纠偏记录与知识分类入口；用于采集格式、数据生命周期、ADR 分类和索引排查。"
---

# info-collection

本次任务内维护显式提供的数据与格式；不注册自动采集或读取全局日志。运行约定见 [runtime-conventions](../_shared/runtime-conventions.md)。

## 格式与归口

| 对象 | 单源 | 动作 |
|---|---|---|
| 用户纠偏 | [corrections 模板](../_shared/templates/corrections-template.md) | 按真实用户输入记录，实例仅本地 |
| 调用/检查记录 | 当前任务既有载体 | 记录实际来源、结果和证据，不补造事件 |
| 记忆结构 | [memory-governance](../memory-governance/SKILL.md) | 显式目录扫描与回放 |
| ADR 分类、命名和索引 | [decision-record](../decision-record/SKILL.md) | 维护 decisions 正文与 KNOWLEDGE 索引 |
| 效果判定 | [effect-governance](../effect-governance/SKILL.md) | 同口径证据对照，无数据则 no_data |

## 执行

1. 明确数据范围、授权、格式权威和消费者。
2. 核对实际输入，定位格式、分类或索引问题。
3. 在授权内定向修改正文及必要引用，复验直接消费者。
4. 记录变更、结果、限制与下一步；无数据不判健康。

主 agent 交互式执行，不派生代理。原始输入、凭证和会话日志不入库；生命周期见 [knowledge-lifecycle](../../standards/common/knowledge-lifecycle.md)。
