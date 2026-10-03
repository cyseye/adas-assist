---
name: finish-check
version: 1.0.0
description: "执行完成检查收尾/交付前检查门，三档+real-run 免检。触发词：收尾检查/交付前检查/提交前检查/开启 agent teams + subagent + PCF 辩论检查。"
---

# finish-check · 执行完成检查收尾

独立可用的验收质量门，承接任意编排上游。**检查为主 + 轻修复门控**：P2 及以下轻量修复（≤5 处、文档/注释级）随报告列清单、用户一次确认后主控执行+grep 复验；P1/must-fix 仍须单独裁决（门控哲学见 `_shared/handoff-modes.md` 未包含——原则：确认的是清单整体，不为单处修复反复往返）。

> 运行约定公共项（`.build/`、gitignore、产物生命周期、失败降级）见 `~/.claude/skills/_shared/runtime-conventions.md`，本文件只列特有项。
>
> 定位：与 verify（P4 单产物对规范红蓝验证）/ improve（P5 事后复盘）正交——交付前时点、表达+抽取+提交+跨任务一致性维度、检查报告+提议产物，三轴均不同；与 verify 重叠时标记后 handoff 深验，不重复验证。
>
> scope：编排层（无固定测试集），自身不接入 skill-evolution；与 flow-dev 同构的转交契约/门控写法暂不抽 `_shared`（守克制，第 4 编排 skill 或同构维护痛点时立项 ADR）。agentos 仓成员（2026-09-12 迁入，ADR test-system-regroup）：检查依据走双根协议——standards/project-rules/rule-registry 等按 cwd 解析当前项目 `.claude/` 下对应文件。

## 运行约定

- `{target}` = 检查对象：产物路径（清单 A）/ git 未 push+已提交文件范围（清单 B）；`{work_dir}` = 任务工作目录
- 主控**顶层串行** spawn 叶子 agent（reviewer 结构按档位见「梯度选择」，单点权威不重复）；**禁止 background 委托** review-gate 类 agent——实证嵌套 spawn 孙 agent 通知断裂（memory `review-gate-nested-bg-limit`）；永不 TeamCreate，升级转交 `decision-consensus`
- reviewer 复用 `Explore`/`general-purpose`/`pcf-*`，不新建 agent 类型（file 模式 reviewer 须 general-purpose——Explore 无 Write 权限）
- 编排契约 + 评分公式 + PCF 决策空间复用 `_shared/review-gate-skeleton.md`（未包含，判定语义以 references/review-gate-protocol.md 特化值为准）；本 skill 特化的判定语义 + must-fix + severity 映射 + 判级纪律 + 维度权重/阈值在 `references/review-gate-protocol.md`

**产物策略（`--artifacts=inline|file`，缺省按档位：quick=inline、standard/full=file）**：

- **inline（零文件）**：reviewer 禁止 Write 任何文件，回传 findings 压缩索引（每条一行 `id/file:line/severity/issue+证据片段`，≤15 行），主控会话内汇总汇报（inline 争议时会话内裁决，见执行流程 Phase 3）
- **file（PCF 裁决需文件基线）**：reviewer 仅允许 Write 到主控指定的**精确路径**，禁止在 `.build/` 其他位置创建任何文件（实证 reviewer 曾散落产物到 `.build/` 根）
- **清理（file 模式汇报完成后）**：主控删除本次全部产物——pattern `report.finish-check*` / `finish-context*` / `finish-check-report*` / `finish.pcf.*` / `checklist_*`（含散落越界的），`KEEP_INTERMEDIATES=1` 跳过；只匹配本 skill pattern，不触碰其他 skill 产物

**验证标记（reflex-check 联动，收尾提醒消除路径）**：

- 检查完成（任一档位）或等效验证成立后，主控 append 一行 `{"ts","batch","method","note"}` 到 `shared_state.data_claude()/.state/finish-verdicts.jsonl`（**动态同根**，与消费者 reflex-check/gate-assist data_root 单源一致）：
  - 路径解析：元层仓 cwd 即 `~/.claude/.state/`，项目仓 cwd 为 `<项目>/.claude/.state/`；禁写死绝对根（消费者读不到）也禁相对拼接（元层仓 cwd 会落幻影双 `.claude` 根，2026-09-18 双实证修复）
  - 写法：gitignored 状态域，仅追加；文件增长到影响读取时再议滚动清理，登记 README 推迟表；勿放 .build——会被按中间产物清理，实证丢失
- method 取 `quick/standard/full`（检查完成）或 `real-run`（等效验证）；reflex-check 命中同 batch 即静默
- batch 算法**禁止主控手算**（算错即静默失效）：调 `python3 ~/.claude/skills/_shared/scripts/gate-assist.py finish-batch [--write --method <档位> --note <...>]`——算法（porcelain 代码类改动整行含 XY 前缀、剔 `.claude/` 豁免、sorted join sha256 前 8 位）与比对/落 verdict 行均由脚本承载，与 reflex-check 检查 1 双源同改

**等效验证（real-run）判据**——四条全满足才可声明，防滥用：①本批为代码/脚本类改动 ②编译/lint 通过 ③**行为级断言实跑通过**（非仅静态 review，如构造场景验证/真实运行）④结果已向用户汇报。等效验证 ≠ 规范验证（后者归 decision-verify），仅作收尾提醒消除凭据。

## 何时启用

**启用**：用户说「收尾检查 / 交付前检查 / 提交前检查 / 开启 agent teams + subagent + PCF 辩论检查」+ 检查对象

**不启用（用更专的）**：

| 场景 | 改用 |
|------|------|
| 产物对规范红蓝验证 | decision-verify |
| 事后根因+CAPA 复盘 | decision-improve |
| 多角色 Delphi 共识收敛 | decision-consensus |
| 单条 DB 缺陷修复 | 无专项 skill（主控直接修或走 dev-implement） |
| dev 链阶段产物/代码专项审计 | audit-fix（全链 P1~P5）/ dev-review（implement/test 代码深审）；本 skill 清单与其维度重叠时标记后 handoff，不重复审 |

## 梯度选择（重武器按需点火，不全量执行）

> 对齐「开局定点单 skill · 按需路由」哲学与 `_shared/review-gate-skeleton.md`「轻/重评审门」两种形态。**各档共享硬约束：B0 git 盘点（规则见清单 B0 行）+ 5 项 must-fix 兜底（清单见协议）+ 轻修复门控（见开头总纲）。**

| 档位 | 适用 | reviewer 结构 | 判定 | PCF | 门控 |
|------|------|--------------|------|-----|------|
| quick 快速扫 | 单文件小改动 / 提交前快检 | 1 个合并 reviewer 全维扫描（重点 must-fix 5 项） | 三值判定（无评分） | 无 | 无中间门控 |
| standard 标准 | 常规交付（缺省） | 清单 A / B 各 1 个合并 reviewer | 三值判定（无评分） | 仅 reviewer 争议 | 无中间门控 |
| full 深度 | 重大交付 / 跨多任务收尾 | 2 个合并 reviewer（A 组 A1-A4 / B 组 B1-B5，评分仍按 9 维逐维计） | 加权评分 + ≤3 轮 | 全触发条件 | 每 phase 门控 |
| real-run 等效验证 | 已有行为级实跑凭据的本批改动（免检路径，非检查档） | 无 reviewer——主控按四判据自查 | 四判据全满足（见「运行约定·等效验证」） | 无 | 无 |

**档位推断**（用户未显式指定）：git 未 push 改动 <2 文件 或 产物单文件 → quick；多文件/多任务交付 → standard；用户说「深度/全量检查」或跨多任务收尾 → full；本批已有行为级实跑凭据（构造场景验证/真实运行通过且已汇报）→ 记 real-run 免检，不再跑检查档。显式指定覆盖推断：`/finish-check quick <target>`。

## 用户输入

- 检查对象（必需）：产物路径 / git 未 push+已提交范围 / 两者
- 清单选择（可选，缺省按对象推断：产物→A，git 范围→B，模糊→AskUserQuestion）
- 档位（可选）：quick / standard / full，缺省按「梯度选择」推断规则
- 产物策略（可选）：`--artifacts=inline|file`，缺省按档位（见运行约定）
- 修复模式（可选）：`--fix=ask|off`，缺省 ask（报告附 P2 及以下修复清单）；off=纯检查

## 检查清单（提炼两话术，执行机制统一）

### 共用执行机制

主控串行 spawn reviewer（档位结构见「梯度选择」）→ 按产物策略分流（见运行约定）→ 争议项触发 PCF 三件套（`pcf-proposer`→`pcf-critic`→`pcf-finalizer`，顶层串行 spawn；inline 时会话内裁决）→ 产检查报告（findings + severity + handoff 提议；`--fix=ask` 时附修复清单）→ 写验证标记（见运行约定）。

### 清单 A 产物质量（话术1，对象=刚产出内容/产物）

| 维度 | 检查项 | 依据 |
|------|--------|------|
| A1 冗余无效清理 | 冗余/无效/废文/死代码标记（深查转交 `audit-code-structure`） | 当前项目 `standards/common/refactor-cleanup.md`（双根） |
| A2 表达质量 | 简洁/层次/条理/逻辑/精炼 | 表达体系规范（本仓未包含，主控按通用表达标准判 A2；项目侧有 `comment.md`/`format.md` 时叠加项目判据）；机械预筛通道=`scripts/expression-eval.py`（本仓未包含，主控人工判 A2） |
| A3 实现细节满足要求 | 是否满足**用户原始要求**（非规范符合——归 verify） | 用户需求原文 |
| A4 规范合规不过度设计 | 按 project rules 优化 + 不为设计而设计 | 当前项目 `project-rules.md`（双根）/ `evolution-discipline.md` |
| A5 前端实现专项 | 前端交付物的复用/规则合规/适配多视口深查转交 `audit-page-quality`（full 档且对象含前端页面时） | 项目仓 skill（按名转交，路径随项目） |

### 清单 B 提交一致性（话术2，对象=未 push+已提交文件）

| 维度 | 检查项 | 依据 |
|------|--------|------|
| B0 git 提交盘点 | 未 push+已提交文件清单（**只读** `git status`/`log`/`diff`，不提交——提交归 dev-implement/flow-dev 归档环；发现未提交/未 push 但用户预期已提交 → 必须人工确认才继续，防漏提交混入收尾通过） | — |
| B1 功能交叉公共抽取 | 跨任务重复实现未抽取到公共 | `refactor-cleanup.md` / 复用优先 |
| B2 串联功能 | 需串联未串联（跨任务断链） | `responsibility-split.md` |
| B3 上下文一致 | 跨任务/跨模块上下文一致（verify 是单产物视角，本 skill 跨任务） | — |
| B4 逻辑闭环 | 跨功能逻辑闭环（verify 是单产物状态机，本 skill 跨功能）；文档指针目标存在性（§锚点/脚本路径/编号锚 grep 核验，防收敛后指针悬空）；机械预筛可选=`~/data/tools/nodetools/node_modules/.bin/remark --quiet --use remark-validate-links <files>`（仓内相对路径核验，2026-10-01 引入，外链禁用） | — |
| B5 commit 规范 | commit 消息是否符合 commit-conventions.md 格式（type/scope/subject） | 当前项目 `standards/common/commit-conventions.md`（双根；**条件件**——agentos 元层仓无此件，仅项目仓存在时检，元层仓 B5 跳过如实报，2026-09-26 finish-check 实证断链勘误） |

> **边界**：A3/B3/B4 与 verify 视角不同（单产物对规范 vs 跨任务交付），重叠时 handoff 深验（见开头定位）。B5 检查逻辑：从 `git log -1 --pretty=%B` 获取最新 commit 消息，解析 type/scope/subject 是否符合格式，不符合标记为 P2（轻修复）。

## 执行流程

| Phase | 动作 | 产物 |
|-------|------|------|
| 1 装配 | 读用户需求原文 + 召回 `~/.claude/decisions/KNOWLEDGE.md` 相关条目（**上游有 clarified-requirements.md 时：先读其 frontmatter `recall_refs` 直读命中条目，命中不足再全索引扫描**（转交指针化，ADR adr/data/token-effect-balance-v2）；standard/full 加读当前项目 `project-rules.md` 加载 standards（双根）） | file：`.build/finish-context.json`；inline：会话内 |
| 2 检查 | 按档位 spawn reviewer（结构见「梯度选择」）；B0 git 盘点（见清单 B0 行，各档保留） | file：`.build/report.finish-check.round.{N}.json`；inline：压缩索引回传 |
| 3 裁决 | 争议 → PCF 三件套（顶层串行 spawn `pcf-proposer`→`pcf-critic`→`pcf-finalizer`），触发分级按梯度表 PCF 列，详版触发条件见协议 | file：`.build/finish.pcf.*.json`；inline：无（争议时会话内裁决） |
| 4 汇总 | 汇总 findings + severity + handoff 提议；`--fix=ask` 时附修复清单（约束见开头总纲；超限或涉代码逻辑 → 拆单独任务）一并呈报 | file：`.build/finish-check-report.json`；inline：会话内报告 |
| 5 清理 | file 模式按运行约定「产物策略·清理」条执行（pattern/时机/`KEEP_INTERMEDIATES=1` 均在彼处）；inline 天然零文件 | 无（产物即删） |
| 6 标记 | 调 `gate-assist.py finish-batch --write` 写验证标记（batch=本批改动 digest；method=档位或 real-run，见运行约定） | 一行 append |

**修复执行（清单获批后）**：按开头总纲执行——主控 Edit 逐处+每处独立 grep 复验，失败如实报告不带病放行；P1/must-fix 不入此清单，单独裁决。

**门控（单点）**：哲学见 `_shared/handoff-modes.md`。quick/standard 无中间门控（一次跑完出报告，报告后用户裁决 handoff 去向）；full 每 phase 门控。唯一硬约束：B0 git 盘点的人工确认条款（见清单 B0 行）。

## 转交契约映射表（与 flow-dev 同构写法，预留 _shared 抽离点）

派生方式三类定义见 `_shared/handoff-modes.md`。

| 转交 | 上游产物 | 下游输入契约 | 派生方式 |
|------|---------|-------------|---------|
| 任意编排上游→收尾 | code commits + 产物 | finish-check `{target}` | 契约直通：归档前主控提议触发 finish-check |
| P3.5→P4 | `finish-check-report.json`（含 handoff） | verify `target_dir` | 契约字段：handoff 提议需 verify 深验的项 |
| finish-check must_fix→improve | `finish-check-report.json`（must_fix>0/系统性/复发） | improve 触发事件 | 契约字段：复用 verify §9 handoff schema |
| finish-check PASS→record | `finish-check-report.json`（含重大交付决策） | record 决策主题 | 主控人工桥接：检查结论→决策主题 |

> inline 模式下上表 `finish-check-report.json` 均由**会话内报告内容**承载（主控人工桥接转交，无需落盘）；file 模式在 Phase 5 清理**前**完成转交读取。

## 降级

降级按 `_shared/handoff-modes.md` 公共模式；file 模式 paused 可跨会话续跑（读 report 恢复，前提未触发 Phase 5 清理或 `KEEP_INTERMEDIATES=1`）；inline 模式不落 report 故无跨会话续跑（重跑代价低，直接重启）。

**静态扫描通道**：`python3 ~/.claude/skills/_shared/scripts/finish_check.py --diff`（本仓未包含，由主控按清单人工静态自检），FAIL 项入 findings（exit 1 不阻断）。

## 资源

| 文件 | 用途 |
|------|------|
| `references/review-gate-protocol.md` | 收尾检查特化协议（must-fix/severity 映射/维度权重/阈值，复用 `_shared/review-gate-skeleton.md`） |
| `templates/finish-check-report.json` | 产物 schema |
| `_shared/review-gate-skeleton.md` | 编排契约 + 评分公式 + PCF 决策空间（复用；未包含） |
| `~/.claude/agents/pcf-{proposer,critic,finalizer}.md` | PCF 三件套（复用） |
| 当前项目 `.claude/rules/project-rules.md` + `.claude/standards/`（双根，按 cwd 解析） | A4 检查依据 |
| 当前项目 `standards/frontend/rule-registry.md`（双根） | 前端规则源索引（A5 转交 audit-page-quality 的规则同源；前端检查项命中规则时经本表解析路径） |
