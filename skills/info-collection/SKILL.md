---
name: info-collection
description: "采集+ADR 知识分类统一维护入口（门面）；采集格式权威声明，执行不重写：采集 hook 自动跑、ADR 归 decision-record。触发词：采集格式/进化数据/采集数据/.state 清理/ADR 分类维护/索引排查。"
---

# info-collection · 采集与知识分类统一维护

三块职责：格式权威声明 + 数据生命周期 + 分类维护门面。**只声明与索引，不复制执行**——采集/写 ADR/信号扫描的运行逻辑各归其主。

## 统管边界（知识进化部，V3 实施 1）

- **归口**：本 skill 为知识进化部统管行动实体；memory-governance（memory 层治理）为本部辖属，session-search 未包含，三 skill 边界=数据流互指——memory 治理发现采集格式问题→转本 skill 职责 1；检索命中历史结论→沉淀走 decision-record/本 skill 职责 3。
- **机器门**：hooks 归口登记（新 hook 接入须在本表职责 1 登记行）+ 周评估查调用数（invocations 单轨对账，零调用 4 周期→lifecycle cold-skill 核验）。
- 部门壳挂起按首战 B.1 前置门执行（挂 MAP 推迟表 #20），不单独立机制。

## 职责 1：采集格式统一权威

改任何采集格式**须在此登记**（单一权威，散改即漂移）：

| 采集点 | 格式权威位置 | 落盘（全部仅本地不入库） |
|---|---|---|
| 纠偏信号 + Evolution Record | `skill-evolution/scripts/reflex-check.py` `_append_evolution_record`（三档判定 + source/context_summary 收窄 schema，勘误见 adr/meta/skill-evolution-spiral-loop） | `.state/evolution-pool/evolution-records.jsonl` |
| skill 级用户纠正 | `_shared/templates/corrections-template.md`（六字段） | `.state/corrections/<skill>.md` |
| Skill/Agent 调用留痕 | `skill-evolution/scripts/collect.py`（ts/session_id/tool/target/success） | 全局单轨 `skill-evolution/registry/invocations.jsonl`（per-skill registry 已退役） |
| 全工具调用留痕 | `skill-evolution/scripts/collect-all-tools.py`（ts/session_id/tool/summary/success；无 matcher 全工具，口径独立于 invocations；未包含） | `skill-evolution/registry/tool-calls.jsonl` |
| 教训召回命中 | `skill-evolution/scripts/knowledge-recall.py`（只读召回，非采集） | `.build/reflex-hooks.jsonl`（运行日志） |
| 后台分析段（智能面产出） | `skill-evolution/scripts/weekly-eval.py` `_model_analysis`（触发=仅超线⚠；轻度思考硬上限；频率=全局 analysis marker 7 天节流，用户主动 `--force` 豁免） | `.build/weekly-eval-report.md` 尾部分析段（运行数据，仅本地；生命周期依赖 cleanup-builds 白名单含 weekly-eval-report.md——两处同改） |

**版本管理红线**：用户输入信息采集数据仅本地、永不入库——`.claude/.state/`、registry/、reflex-hooks.jsonl 全部 gitignore（L0/L1 层语义见 knowledge-lifecycle；用户裁决重申）。

## 职责 2：.state 数据生命周期

- **evolution-pool**：append-only 候选池；event_id 确定性 hash 去重；消费 = 周评估「候选池消化」条目（`_shared/evolution-discipline.md §周评估`，过滤 `evolution_action.status == pending_validation` 逐条闭环/升级/作废）；写入方 = reflex-check `_append_evolution_record`，session-review 不消费此池
- **corrections**：状态机 new→merged→stale→purged（模板内置）；写者/转移执行者（T127①，2026-09-28 登记）：`new` 写者=主控（reflex-correction 提醒驱动）手写实例表，`new→merged` 转移执行者=主控条款落地轮当轮转移（状态加 `@日期`），机械核=session-review 周扫 `correction-*` 信号（提示注入不代写，T126 PCF 上限）；冗余清理挂 session-review 周期信号，不新建扫描
- **训练轨**（skill_updated/training_dataset 标记）仅落盘不训练，积累量级后离线处理（推迟登记 #17）

## 职责 3：ADR 分类维护门面（排查入口统一）

| 维度 | 权威位置（执行转交，不在此重写） |
|---|---|
| 命名/归域/合并/取代 | `standards/common/doc-naming.md`（规范）+ decision-record（写侧执行） |
| 一致性/治理/累进/经验汇总信号 | `skill-evolution/scripts/session-review.py`（自动扫描→PENDING→分级消化） |
| 索引 | `decisions/KNOWLEDGE.md`（唯一索引，decision-record Step 5/7 维护；adr-index 已废并入） |

排查路径：用户报「索引不对/分类错/采集数据异常」→ 本 skill 定位权威位置 → 机械问题主控直修 / 结构问题转 decision-record 或登记信号。

## 何时启用 / 不启用

**启用**：用户说「采集格式 / 进化数据 / 采集数据 / .state 清理 / ADR 分类维护 / 索引排查」
**不启用**：写 ADR→decision-record；跑采集→hook 自动；产物验证→decision-verify；skill 增删评估→decision-lifecycle

## 运行约定

- 主 agent 交互式执行，不 spawn；格式/生命周期规则变更先在此登记，再由权威文件归属者执行
- 产物：KNOWLEDGE 索引更新（登记变更时）

## 反模式

| 禁止 | 正确做法 |
|---|---|
| 在此复制 schema/规则全文 | 声明+索引到权威位置 |
| 直接改采集脚本逻辑 | 登记变更→按 skill-evolution 归属改 |
| 采集数据入库 | 全部仅本地（版本管理红线） |
| 新建扫描/巡检机制 | 挂既有 session-review 信号 |
