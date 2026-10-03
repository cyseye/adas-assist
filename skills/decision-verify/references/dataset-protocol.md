# 红蓝测试数据集协议

> 单一权威源：数据集条目 schema、采集入口、注入方式、生命周期均以本文件为准。数据集本体在 `../data/red-blue-dataset.jsonl`（JSONL，一行一条；可选生成物——首次采集前文件不存在属正常态，非悬空）。

## 1. 定位

数据集 = 历史真实任务的完整链路记录（用户真实任务→Prompt→模型回答→用户是否接受→用户怎么改→最终产物→是否成功），供红蓝测试做**回归对比基线**：当前验证中若历史已解决的缺陷重现，红队标记回归而非普通缺陷。

**资产属性**：本地保留不入 git、**不做版本管理**——条目更新直接改行不留旧版，删除不可恢复。由此推出两条设计约束：准入从严（§3 优质门槛，宁缺毋滥，进集即优质）；清理须用户确认且明示不可恢复（§5，脚本只标记不删）。

## 2. 条目 schema

```json
{
  "id": "20260818-01",
  "task_type": "table-spec | base-spec | tech-spec | etl-split | skill-doc",
  "status": "active | deprecated | expired",
  "source": "generated | backfill",
  "last_verified": "YYYY-MM-DD",
  "task_chain": {
    "user_real_task": "用户真实任务一句话",
    "prompt_used": "实际触发 prompt（可截断 200 字）",
    "model_response_summary": "模型回答摘要（100 字内）",
    "user_accepted": "true | false | partial | unknown",
    "user_modifications": "用户后续怎么改（无则空串；不可考则 unknown）",
    "final_output_path": "最终产物路径（相对 repo 根）",
    "task_success": "true | false | unknown"
  },
  "verification": {
    "verify_report_path": "verify-report.json 路径（没跑过则空串）",
    "final_score": null,
    "must_fix_count": null,
    "regression_detected": false
  },
  "created_at": "YYYY-MM-DD",
  "product": "产品名"
}
```

约束：
- `source=backfill` 条目的 `task_chain` 用户侧字段（user_accepted / user_modifications / task_success）不可虚构，一律 `unknown`（git 无法还原）；有 verify-report 佐证的除外（PASS + 已入 git = 接受的事实依据，可标 true）
- `id` = `{创建日期 YYYYMMDD}-{两位序号}`，不做 UUID
- `final_score` 只填真实跑过的 verify 结果，禁止估算

## 3. 采集入口（优质准入）

**准入门槛（"优质"定义，全满足才入集，宁缺毋滥）**：
1. 终审 pass（must_fix=0）
2. 有回归对比价值：涉 ETL 宽表 / 修复了 P0/P1 缺陷 / 模式 B 校正了口径冲突——常规无修复价值的任务不入集
3. 链路字段真实：用户侧不可考处一律标 unknown（禁止虚构/估算），verification 仅填真实跑过的结果

| 入口 | 时机 | 动作 |
|------|------|------|
| 设计 skill 收尾（design-table-spec Phase 3 / design-base-spec Phase 4） | 满足准入门槛 | 生成草稿 `.build/*/dataset-entry-draft.json`，确认门控问用户 |
| 手动追加 | 用户显式要求记录某任务 | 按准入门槛 + schema 直接追加 JSONL |

确认门控三选项：`go`（用户审核后追加）/ `auto`（在准入门槛之上再要求 final_score≥90 且无 P0，主控直接追加）/ `skip`（丢弃草稿）。**默认不采集**，防灌水稀释数据集质量。

## 4. 注入方式（红蓝测试回归）

1. **召回**（decision-verify Phase 0）：object_type=design 时读数据集，按 `task_type` + `task_chain.final_output_path` 匹配当前验证目标，筛 `status=active` 条目
2. **注入**（Phase 1）：命中条目以路径列表加入 reviewer_args 的 `baseline_dataset` 参数，红队自行 Read
3. **回归判定**（红队）：对比当前产物与 baseline 条目——历史高分条目对应的缺陷在当前重现 → `regression_detected=true`，该 issue 升 must-fix
4. **回写**（Phase 3 收尾）：验证 PASS 后更新命中条目的 `last_verified`；检出回归则置 `verification.regression_detected=true`

**防误判纪律**：`source=backfill` 且用户侧字段为 unknown 的条目只做提示性基线，不作为 must-fix 强判据（弱基线误报会经 fixer 放大）；仅 `verification.final_score` 真实≥90 的条目可触发回归升级。

## 5. 生命周期

| 转换 | 条件 | 触发 |
|------|------|------|
| active → expired | `last_verified` 超 90 天且产物其后仍有改动（产物在变、基线未更新） | session-review.py 扫描标记，进 PENDING 分级消化 |
| active → deprecated | `task_chain.final_output_path` 指向的文件不存在（产物删除/迁移） | 同上 |
| expired/deprecated → 删除 | 用户确认后物理删行（**不可恢复**——数据集无版本管理，删前须向用户明示） | **仅人工确认**，脚本不自动删 |
| 任意 → active | 重新验证 PASS 后刷新 `last_verified` | decision-verify Phase 3 |

路径迁移不算 deprecated：文件在但路径记录过时 → 更新条目 `final_output_path`，属正常维护。