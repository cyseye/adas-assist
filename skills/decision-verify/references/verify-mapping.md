# Verify Mapping — 对象泛化映射

对象类型判定 + checklist 选择 + 评分权重调整 + 主控编排映射。

## 1. 对象类型判定

优先级：用户显式 `--type` > 自动判定 > generic。

| 对象 | 自动判定信号 |
|------|-------------|
| code | 目录含 `src/`/`*.java`/`*.ts`/`*.py`/`pom.xml`/`package.json` |
| design | 目录含 `design/` 或文件名含 `design`/`spec`/`详设` |
| prd | 目录含 `PRD-*.md`/`PRD-global.md`/`.source/chapters/` |
| adr | 目录含 `adr/` 或文件为含 frontmatter（`title`/`status`）的 `{slug}.md` |
| generic | 以上均不匹配 |

无法判定 → generic + 输出 `[INFO] 未识别对象类型，使用 generic 通用 checklist`。

## 2. checklist 选择表

各对象叠加的特化项（通用 4 维项见 `checklist-dimensions.md` §通用检查项）：

| 对象 | 特化项 | 来源 |
|------|--------|------|
| code | C001-C005（状态机终态/异步超时/并发/SQL注入/依赖版本） | checklist-dimensions §code |
| design | D001-D003（设计一致性/边界场景/死循环） | §design |
| prd | P001-P003（反幻觉字段表/死链/章节完整） | §prd |
| adr | ADR-M01~M21 + ADR-A01~A07（frontmatter/五要素/编号/状态机/索引一致/跨类型链） | decision-record/references/adr-checklist.md |
| generic | 无特化，仅通用 4 维 | §generic |

## 3. 评分权重调整表

默认权重：正确性 0.40 / 安全性 0.30 / 规范性 0.20 / 完整性 0.10。

| 对象 | 正确性 | 安全性 | 规范性 | 完整性 | 调整理由 |
|------|--------|--------|--------|--------|---------|
| code | 0.35 | **0.35** | 0.15 | 0.15 | 代码安全性权重↑ |
| design | 0.40 | 0.20 | 0.20 | 0.20 | 设计完整性↑，安全性↓ |
| prd | 0.40 | 0.10 | 0.30 | 0.20 | PRD 规范性↑，安全性↓ |
| adr | 0.20 | 0.10 | 0.40 | 0.30 | 文档产物规范性+完整性优先，安全性降至 0.10 |
| generic | 0.40 | 0.30 | 0.20 | 0.10 | 默认 |

> 调整后权重须同步 `review-gate-protocol.md` §4 总分公式（review-gate 按本表权重计算）。code 对象的权重调整反映"代码产物中安全缺陷的发布风险高于规范瑕疵"。

## 4. 主控编排映射（不委托 review-gate）

主控按 SKILL.md Phase 1-2 直接 spawn 叶子 agent（嵌套 background 通知断裂，不委托 review-gate，见 SKILL.md §4 注）：

```yaml
work_dir: "{target_dir}"                      # 主控拼 {work_dir}/.build/ 写产物
skill_dir: "~/.claude/skills/decision-verify"   # 主控据此定位 references
reviewer:
  subagent_type: review-rule                  # 主控直接 spawn（非嵌套）
  args: >
    target_files={target_files}
    checklist={skill_dir}/references/checklist-dimensions.md
    rules={skill_dir}/references/red-blue-protocol.md
    output={work_dir}/.build/report.red-team.round.{round}.json
fixer_spec: "{skill_dir}/agents/exec-review-fixer-blue.md"
fixer_args: "target_dir={target_dir} object_type={object_type}"
```

- 主控产出：`report.review.round.{N}.json` + `report.review.final.json`（评分按 review-gate-protocol.md）
- review-rule 产出：`report.red-team.round.{N}.json`（issues 按 dimension 归 4 维）
- exec-review-fixer-blue 产出：`report.fix.round.{N}.json`

## 5. 示例

### 示例：订单状态机 code 验证
```
target_dir=/proj/order-service  (含 src/Order.java, pom.xml)
→ 自动判定 code；checklist: 通用4维 + C001-C005；权重: 0.35/0.35/0.15/0.15
→ 红队发现: C001(状态机缺终态,P0,正确性) + C004(SQL拼接,P0,安全性)
→ review-gate: must_fix=2 → FIXABLE → 蓝队修复 → 重跑 → PASS
→ verify-report.json: status=pass, final_score=92
```

## 6. 转交边界（闭环下游）

verify-report 落地后的转交映射（本节为单源，SKILL.md §9 只留指针）：

| 信号 | 转交 skill | 触发 |
|---|---|---|
| must_fix>0 / 系统性缺陷 / 复发 | `decision-improve` | 系统性缺陷需 postmortem 根因+CAPA；止于报告则经验不沉淀 |
| PASS / 重大架构裁决 | `decision-record` | 架构决策沉淀 ADR 可追溯 |

主控在 `verify-report.json` 写 `handoff` 字段（`proposed_skill`/`reason`/`evidence_refs`/`propose_trigger`）标提议 + 证据（issue 列表 / 裁决要点），用户确认后转交；handoff 是提议态，verify 收尾写入即止，不自动触发下游。不绕过 verify 直接 improve——improve 启用条件（“缺陷复发 / 反复返工”）由 verify 的复发判定接入，复用现有触发边界不另建。
