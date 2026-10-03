# improve 映射

> 与其他 skill 边界 + 产物字段映射 + metrics 采集 + 沉淀与复发闭环。

## 与其他 skill 边界

> 边界单源 = `decision-improve/SKILL.md §不启用清单`（skill-evolution/record/verify/consensus/dev-implement 各自归位）。仅补一句链向：重大 CAPA 措施可转 record 沉淀 ADR；verify 发现的系统性问题可触发 improve；根因分歧大可转 consensus。

> 一句话：improve 是独立可用的复盘组件，产生复盘+CAPA；代码修复按 dev-implement 流程执行，决策沉淀交 record，根因分歧交 consensus。

## 产物字段映射

| 产物 | 字段 | 来源 |
|------|------|------|
| `{slug}.md` | title | 用户/主控 |
| | date / incident_date | 主控 |
| | severity(1-4) | 主控（Orient 步） |
| | category | 主控（复发匹配键） |
| | status | draft→accepted |
| | related_postmortem | 主控（复发时链回） |
| | 五要素 | 主控（根因步+五要素步） |
| `{slug}-capa.md` | postmortem_id | 链回 postmortem slug |
| | status(整体) | 映射规则=capa-protocol.md §CAPA 闭环状态机 |
| | actions[] | 主控（CAPA 规划步） |

## metrics 采集

skill 执行末尾（SKILL.md Step 8），主控把以下写入 `{task_dir}/.build/metrics.latest.json`：

```json
{
  "postmortem_quality": "<五要素非空完成率，0-1，进自动评估>",
  "action_count": "<CAPA action 总数>",
  "capa_closed_count": "<本调用=0，闭环发生在后续>",
  "action_completion_rate": "<纵向，本调用 null，跨调用填>",
  "recurrence_rate": "<纵向，需对比同类别历史 postmortem，本调用 null>",
  "recurrence_category": "<跨调用匹配键，= postmortem category>"
}
```

> 指标均供人工 current-vs-baseline 比对（自动评估链已退役）；`action_completion_rate`/`recurrence_rate` 越小越好且跨调用，记录时注意方向（对齐 consensus 模式）。

## 沉淀与复发闭环（概念定位，非运行时依赖）

沉淀动作单源=SKILL.md Step 7（KNOWLEDGE 索引 + 跨类型链，本节不复述）；复发判定闭环：下次同类问题 → improve Step2 读 KNOWLEDGE 找历史 postmortem → 判复发 → 评估历史 CAPA 失效原因（规则=`capa-protocol.md §复发判定`）。
