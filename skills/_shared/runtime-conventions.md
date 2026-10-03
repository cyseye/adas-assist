# skill 运行时公共约定（canonical）

> 各 skill「运行约定 / 指标采集 / 产物生命周期 / 私有 agents 调度」的共性约定单一真相源。
> SKILL.md 一律以一句指针引用本文件，仅保留本 skill 特有项；共性规则改动只改此处，全族生效。
> 相邻协议不在此重复：失败降级正文见 [`standards/common/skill-failure-protocol.md`](../../standards/common/skill-failure-protocol.md)；spawn 编排约束（串行/禁 background/prompt 只传路径）见 [`review-gate-skeleton.md`](review-gate-skeleton.md)。
> 引用句式：`> 运行约定（目录/指标/生命周期）见 _shared/runtime-conventions.md，本 skill 仅列特有项：{…}`（按需裁剪）。基座恒为 `~/.claude/skills/_shared/`；跨仓消费者一律写全路径，禁 bare 短式出仓。

## §1 运行目录与中间产物

- `{task_dir}` = 当前任务工作目录（默认 cwd）；`{skill_dir}` = 本 skill 目录
- 中间产物统一写 `{task_dir}/.build/{skill 名}/`（或 skill 自定子路径），**`.build/` 须加入 .gitignore**
- agent 间文件传递走 `.build/*` 路径，prompt 只传路径不内联正文（编排约束主控自控（review-gate-skeleton 未包含））

## §2 指标采集（接 skill-evolution 的 skill 适用）

| 文件 | 性质 | 写法 |
|---|---|---|
| `{task_dir}/.build/metrics.latest.json` | **已退役**：无生产义务/无自动消费方（evolve 评估链退役），历史字段说明靠 git | 不再写入 |
| 调用留痕 | 自动采集 | 由 PostToolUse hook（collect.py）自动追加至全局单轨 `skill-evolution/registry/invocations.jsonl`（per-skill registry 已退役，禁手写、禁读 per-skill 路径） |

> 不产指标的 skill（如 audit-page-quality）此节整体不适用。

## §3 产物生命周期

1. **交付物**（代码 / 文档 / ADR 索引等最终产物）→ 按性质入库或按 skill 规定本地保留
2. **`.build/` 中间产物** → 执行后清理；Stop hook（cleanup-builds.py，**`.build` 清理唯一归口**；cleanup-ledger 轮转的 retention-gc.py 本仓未包含，轮转由 cleanup-builds 自身 rotate 承载）会自动清扫各 skill `.build/`，依赖后续读取的产物（metrics.latest.json、用户要求保留项）除外
3. **验证标记 / 运行时状态** → 写 `.claude/.state/`（勿放 `.build/`——会被按中间产物清理）
4. **spawn 失败**：重试 1 次，再失败即 hard fail / 升级主控裁决
5. **并发限流/429 重试流程（2026-09-27 用户指令补齐；先例=BACKLOG R1「D1 spawn 遭 429 全灭缩面主控直做」暴露无重试缺口）**：〔层界：本条管主控层 spawn，重试 ≤2 次/dead 判定〕
   - **即时 error（限流/5xx）**：当场补发（§4.1.1）不计入本条退避序列
   - **持续限流**：主控并发降档（在途 spawn 减半）→指数退避重试 ≤3 次（≈30s→2m→8m，长等待用 ScheduleWakeup/定时等价物，禁忙等）→两轮退避后仍限流→**缩面处置**（改主控直做/降批量/拆批次错峰），缩面决定在轮末总账留痕，禁静默丢臂（R1 先例口径）
   - **检索通道 429**：不计检索预算（`retrieval_budget.error_calls_free`）且换道不绕过（同 budget 域内 engines 切换，F4 口径）
   - **定性**：API 速率限流系外部硬约束不可解除，处置=重试+降速+错峰，不做「绕过」尝试；与 §5 长任务断链预案衔接（跨窗中断走断链预案，即时限流走本条）

## §4 私有 agents 调度约定

> skill 子目录下的 `agents/*.md` **不被平台注册**，禁止按名 `subagent_type` spawn（会断链回退）。

统一声明句式（含私有 agents/ 目录的 SKILL.md 头部置入）：

```
> 调度说明：agents/ 目录未包含，「委托 X」一律主控自演，禁止按名 spawn；spawn 模型路由纪律（执行档类别名路由、禁写死型号、裁决/终审/澄清除外）原单源 standards/model-governance.md 未包含，主控按 low/medium/high 直判。
```

角色被 ≥2 skill 复用时提升到 `~/.claude/agents/` 顶层（重名加域前缀）再按名 spawn。

### §4.1 并发 spawn 三步核验（多 agent 并行写文件时强制；源自审计轮 F2/F3 事故，postmortem 2026-09-14）

0. **并行会话提交纪律（2026-09-26 增补，宪法#1 双实证：同日两次 批被并行会话全量 add 卷入同一 commit）**：多会话/并行 共享工作区时，各方 commit 前须 `git add <显式文件清单>`（只加本批产物），**禁 `git add -A`/`git add .` 等空范围 add**；入库后发现卷入他方文件时补 `--allow-empty` 归属勘误提交并在 BACKLOG 留指针。

1. **launch 结果逐条↔名字映射核对**：并行发 N 个 agent 后，逐条确认 success/error 各对应哪个 name，禁止按返回顺序默认配对；spawn 失败（限流等）**当场补发**，严禁进入「等通知」心智（实证：error 被按序号错配，空等数轮后才发现 agent 从未启动）。
2. **文件白名单分区**：多 agent 写同一目录树时，spawn prompt 给每个 agent **显式文件白名单**（正向清单）；禁用「对象+禁入清单」式负向圈地——实证被 agent 泛化职责理解越界写入，并发撞车产生 7 文件重复章节。
3. **改动后机械断言**：对有门限的文件（SKILL.md ≤150 行等）改动后立即 `wc -l`/grep 断言；给文件补章节必须联动瘦身检查，防「只加不减」反弹超行（实证 149→155）。

## §5 长任务断链预案（编排 / 长循环 skill 适用）

> 与 §3.4 划界：§3.4 管 spawn 即时失败（重试→hard fail）；本节管**运行中的长任务被中断**（用量限额窗口、进程退出、会话断链）后的恢复。
> 首选架构姿态：**谁都不持有跨 task 的长上下文**——调度状态外置磁盘（manifest/分配包/slice/per-task commit），中断只落 task 边界，恢复即脚本重建现场（实证：单 orchestrator 包办长循环跨限额窗 ×2 断链，扁平 per-task 分配后恢复路径收敛为一条脚本调用）。

- **spawn 前对齐窗口**：预估跨用量限额窗口的长任务，先核对窗口剩余时间——per-task 分配下预估粒度=单 task 时长（分钟级），不够则少跑 N 个 task 或预告断点锚点，不留半途黑箱
- **中断续跑不重跑**：限额/中断后按既有产物锚点接续——per-task 分配循环（dev-implement）恢复=重跑入口判断 + `next-task.sh`（脚本从 manifest 现场重建调度队列，在途单 task 重 spawn，损失上限=单 task 在途工作）；以批为节奏的编排（dev-plan 批 spawn）批内产物落盘、后续批次照常；存量的长生命周期编排 agent 在途场景才用 SendMessage 接续；禁止全量重跑已 done 的部分
- **进度留痕**：per-task 循环天然产出一行进度（task_id/status/commit），即断链恢复现场锚点；仍以批为节奏的编排维持每批一次阶段摘要落盘
- **定时唤醒续跑（可行）**：429 中断后 ScheduleWakeup 定时到限额重置点——per-task 分配下唤醒轮=轻轮次（脚本+spawn），续跑成本与正常轮一致，不再是留观项

## §6 常驻面禁易变内容（战役 20260917 采纳 #9）

- **禁 fastmover 进常驻面**：skill/agent frontmatter description、CLAUDE.md、README/MAP 速查层等 system-prompt 常驻字节，禁内嵌核验日期戳（如「已核验 2026-09-16」）——核验记录落正文或台账，日期变更即全局前缀缓存报废（B3-1 实证，arch-governance 先例已修）。
- **快照数禁入正文**：「N 篇〔实测 2026-09-17〕」式静态计数保质期 <1 天（B1-F3 实证：44→45 当天即破），正文一律查询式（脚本 `ls|wc -l`）或指针「以 README 机器锚为准」。
- **豁免**：数据文件 `_history`/日志类时间戳、计数锚的括注日期（非 description 层）不在此列。
