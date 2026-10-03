# 魔鬼天团接入点映射

> 本文件定义魔鬼天团与 adas-assist 体系 4 大接入点的调用逻辑、触发条件、数据流向。**按复杂度分级触发**——不是所有变更都需要完整对抗。

## 复杂度分级（三档）

| 级别 | 名称 | 判定标准 | 执行方式 |
|------|------|---------|---------|
| **L1** | 轻量 | 单 skill 内部调整 / 文档修订 / 配置微调 / 有明确回滚方案 | **不触发**魔鬼天团，主控自审即可 |
| **L2** | 中等 | 单 skill 新增/删除 / 协议局部修改 / 有争议但范围可控 | **单轮快审**：正方+反方各 1 次，裁判快速裁决 |
| **L3** | 重大 | 跨 skill 协议变更 / 核心纪律修改 / 不可逆操作 / 体系架构调整 | **完整对抗**：3 轮攻守互换 |

## 接入点总览

| 接入点 | 触发条件 | 默认级别 | 可升级条件 | 数据源 | 产出消费 | 落地状态 |
|--------|---------|---------|-----------|--------|---------|----|
| decision-lifecycle | skill 增删拆分评估 | L2 | 跨 skill 拆分 → L3 | EVOLUTION.md + reflex-hooks.jsonl（补注：另有 KNOWLEDGE.md 相关 ADR） | 魔鬼报告 `devils-panel.report.json` → 裁决输入；reject 时链接 decision-record ADR | ✅ lifecycle SKILL.md Step6 |
| skill-evolution | 退化 P0（周评估人工判定） | L2 | 核心纪律回滚 → L3 | reflex-hooks.jsonl（补注：另有 `metrics.latest.json` 退化前后指标、EVOLUTION.md 进化史） | 根因诊断报告 → 改进方向（compromise_conditions） | ✅ evaluation-flow §根因与影响面前置 |
| session-start | 周评估 weekly-eval-due | L1 | 体系架构建议且用户显式要求 → L2+ | reflex-hooks.jsonl + KNOWLEDGE.md | 只读汇报（周评估三指标+批量确认） | ✅ 主控自审（见接入点 3） |
| decision-record | 用户强行推进 reject | L1 | 用户强行推进 → L2 | 魔鬼报告（输入）+ 用户确认记录 | ADR 文件，记录"风险已知接受" | ✅ record SKILL.md Step0 转交源 |

---

## 接入点 1：decision-lifecycle（skill 增删拆分）

### 触发条件
- 用户触发 skill 增删拆分评估
- decision-lifecycle SKILL.md Phase 2 识别到 skill 生命周期变更

### 调用逻辑
```python
# decision-lifecycle/SKILL.md Phase 2 前插入
if change_type in ["skill_add", "skill_delete", "skill_split"]:
    # 召回上下文
    context = {
        "target": skill_name,
        "change_type": change_type,
        "evolution_history": read(f"{skill_dir}/EVOLUTION.md"),
        "runtime_data": read(".claude/.build/reflex-hooks.jsonl")
    }
    
    # 复杂度评估（决定执行级别）
    level = assess_complexity(context)  # L1/L2/L3
    if level == "L1":
        # 轻量变更：不触发魔鬼天团，主控自审即可
        return proceed_without_panel()
    
    # 调用魔鬼天团（L2 单轮 / L3 完整对抗）
    report = invoke_devils_panel(context, level=level)
    
    # 根据裁决决定是否继续
    if report["final_verdict"] == "reject":
        AskUserQuestion(
            question="魔鬼天团反对该变更，是否强行推进？",
            details=report["antagonist_summary"]["risks_identified"]
        )
        # 用户确认后记录 ADR
        if user_confirms:
            invoke_decision_record(
                change_type="skill_lifecycle",
                devils_report=report,
                rationale="用户已知风险仍推进"
            )
    elif report["final_verdict"] == "compromise":
        # 附加条件执行
        apply_conditions(report["conditions"])
```

### 数据源/产出
见总览表行内补注（2026-09-25 压缩批去重）。

---

## 接入点 2：skill-evolution（自进化退化 P0）

### 触发条件
- 退化 P0（效果指标较上次明显下降，周评估人工判定）
- skill-evolution SKILL.md 退化处理分支

### 调用逻辑
```python
# skill-evolution/SKILL.md 退化处理分支
if regression_detected and severity == "P0":
    context = {
        "target": f"{skill_dir}/EVOLUTION.md",
        "change_type": "evolution_regression",
        "regression_details": {
            "before": metrics_before,
            "after": metrics_after,
            "delta": regression_delta
        },
        "runtime_data": read(".claude/.build/reflex-hooks.jsonl")
    }
    
    # 调用魔鬼天团诊断根因
    report = invoke_devils_panel(context)
    
    # 根据裁决决定改进方向
    if report["final_verdict"] == "reject":
        # 回滚改进
        rollback_evolution_changes()
    elif report["final_verdict"] == "compromise":
        # 部分回滚 + 附加验证
        partial_rollback(report["conditions"])
```

### 数据源/产出
见总览表行内补注（2026-09-25 压缩批去重）。

---

## 接入点 3：session-start（周评估健康度扫描）

> **级别：L1 主控自审**（裁决见 adr/meta/smart-grading-tiering-consolidation）——周评估为只读汇报形态（weekly-eval.py 脚本预计算报告 + 批量确认，主控只读结论），每周全程对抗 spawn 3 agent 与克制原则冲突。下述调用逻辑为**按需升级路径**（体系架构建议且用户显式要求时才触发 L2+），非周评估默认行为。

### 触发条件（升级路径，默认 L1 不触发）
- 周评估到期（weekly-eval-due 信号；session-start.py 开局检测 marker 缺失或 >7 天）
- 仅当周评估产出体系架构级建议**且用户显式要求**时，才按 L2+ 走文末「执行流程（canonical）」调用魔鬼天团（context 构造同 Phase 0）
- 默认行为：weekly-eval.py 只读汇报 + 批量确认，完成后 `touch .claude/.build/weekly-eval.marker`

### 数据源
- `.claude/.build/reflex-hooks.jsonl`：近期运行数据
- `skills/*/registry/invocations.jsonl`：各 skill 使用情况
- `~/.claude/decisions/KNOWLEDGE.md`：历史决策

### 产出
- 体系健康度报告（魔鬼天团报告）
- 周评估完成 marker

---

## 接入点 4：decision-record（风险已知接受）

### 触发条件
- 魔鬼天团裁决 reject/compromise
- 用户强行推进变更

### 调用逻辑
```python
# decision-record/SKILL.md ADR 沉淀
if devils_report and devils_report["final_verdict"] in ["reject", "compromise"]:
    adr_content = {
        "status": "Accepted",
        "context": f"魔鬼天团反对该变更，用户已知风险仍推进",
        "decision": f"执行 {devils_report['target']} 变更",
        "consequences": [
            f"接受风险：{devils_report['antagonist_summary']['risks_identified']}",
            f"附加条件：{devils_report['conditions']}"
        ],
        "linked_devils_report": report_path
    }
    
    # 写入 ADR
    write_adr(adr_content)
```

### 数据源/产出
见总览表行内补注（2026-09-25 压缩批去重）。

---

## 调用规范

> 调用接口规范已并入文末「执行流程（canonical）」单源（2026-09-25 压缩批收敛双写）。

### 数据召回优先级
1. **KNOWLEDGE.md**：历史 ADR/postmortem（最高优先级）
2. **EVOLUTION.md**：目标 skill/protocol 的进化史
3. **reflex-hooks.jsonl**：近期运行数据（真实信号）
4. **memory/**：项目级教训（如有）

---

## 文件流向

```
接入点 → invoke_devils_panel()
      ↓
Phase 0：召回上下文
      ↓
Round 1-3：对抗审查
      ↓
写入报告：adversary-report.json
      ↓
消费报告：
  - decision-lifecycle → 裁决输入
  - skill-evolution → 根因诊断
  - session-start → 健康报告
  - decision-record → ADR 沉淀
```

---

## 执行流程（canonical，2026-09-14 合并执行流详版伪代码至此）

> 本节为执行细节唯一权威；SKILL.md §执行骨架只留摘要，改动须两处同改。

### Phase 0：上下文召回 + 复杂度评估

```
1. 读 ~/.claude/decisions/KNOWLEDGE.md → 找相关 ADR/postmortem
2. 读 {target_dir}/EVOLUTION.md → 历史变更轨迹（如有）
3. 读 .claude/.build/reflex-hooks.jsonl → 近期运行数据
4. 读用户输入的 change_description + 触发原因
5. 读 .claude/memory/ → 项目级教训（如有）
召回内容 → 构造 context
level = assess_complexity(context)  # L1/L2/L3
if level == "L1": return skip()  # 不触发，主控自审即可
```

### Round 1：正方提案 + 反方挑战

```python
summary = init_summary()
# Spawn 正方（template_path={skill_dir}/references/adversary-roles-protocol.md）
spawn Agent(subagent_type="claude", prompt=build_prompt(role="protagonist", context=context))
    → {work_dir}/protagonist.round1.json
summary["protagonist_args"] = read(...)["arguments"]

# Spawn 反方（可见正方输出）
spawn Agent(role="antagonist", context=context, protagonist_args=summary["protagonist_args"])
    → {work_dir}/antagonist.round1.json
summary["antagonist_challenges"] = read(...)["challenges"]
summary["round"] = 1
write("{work_dir}/adversary-summary.json", summary)

# 分流
if level == "L2":            goto Round 3（裁判快速裁决，仅基于 Round 1 数据）
elif challenges == 0:        verdict = "approve"; goto 收尾   # 无争议直接通过
else:                        goto Round 2                      # L3 完整对抗
```

### Round 2：反方提案 + 正方辩护（仅 L3）

```python
spawn Agent(role="antagonist", previous_challenges=..., task="alternative_proposal")
    → {work_dir}/antagonist.round2.json
spawn Agent(role="protagonist", antagonist_proposal=read(...)["alternative_proposal"], task="defense")
    → {work_dir}/protagonist.round2.json
summary["round"] = 2
summary["unresolved_issues"] = extract_unresolved(protagonist_output2, antagonist_output2)
write("{work_dir}/adversary-summary.json", summary)
goto Round 3   # 无论 converged 或 deadlock，均由裁判裁决（deadlock 检测复用 convergence-rules.md）
```

### Round 3：裁判介入 + 最终裁决（L2/L3 共用）

```python
round = 3 if level == "L3" else 1  # L2 实际只跑 1 轮对抗
# L2：裁判仅基于 Round 1 数据；L3：merge(Round1, Round2)
referee_input = {
    "controversy_history": summary,
    "protagonist_stance": merge(protagonist_output, protagonist_output2) if level == "L3" else protagonist_output,
    "antagonist_stance": merge(antagonist_output, antagonist_output2) if level == "L3" else antagonist_output,
}
spawn Agent(role="referee", **referee_input) → {work_dir}/referee.final.json
verdict = read(...)["verdict"]
if verdict == "reject":     return BLOCK                      # 阻断变更，返回接入点处理
elif verdict == "compromise": return CONDITION(referee_output["conditions"])
else:                       return PASS
```

### 收尾：写入最终报告

```python
final_report = {
    "target": context["target"], "change_type": context["change_type"],
    "adversary_mode": "protagonist-antagonist-referee",
    "timestamp": current_time(), "rounds": round, "final_verdict": verdict,
    "protagonist_summary": ... , "antagonist_summary": ...,   # L2 取单轮输出；L3 merge(Round1, Round2)
    "unresolved_issues": summary["unresolved_issues"],
    "referee_rationale": referee_output["rationale"],
    "compromise_conditions": referee_output.get("conditions", []),
    "linked_adr": "",  # 待 decision-record 填充
    "metrics": {"rounds_to_convergence": round,
                "issues_raised": len(summary["antagonist_challenges"]),
                "issues_resolved": len(summary["converged_issues"]),
                "consensus_score": calc_consensus(summary)}
}
write("{target_dir}/adversary-report.json", final_report)   # 永久产物；中间产物在 {work_dir} 执行后清理
update_knowledge_index(final_report)  # 按 knowledge-protocol.md 索引 KNOWLEDGE.md
return final_report
```

## 关联

- 角色协议：`adversary-roles-protocol.md`（3 角色定义）
- 编排逻辑：`../SKILL.md`（主控 Round 判定）
- 报告模板：`../templates/adversary-report.json`
