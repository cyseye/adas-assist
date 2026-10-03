# report-protocol — 托管收口汇报域化细则（单源）
> 加载条件：托管语义（CEO 托管/全权交给你/榨干等）会话产最终总结时读本件。**档位轴 L0/L1/L2 以本表为准**（handoff-modes.md 本仓未包含，纲收编于下表）——只做收口时点的域化细则：L1/L2 的机械判据落地 + 增量水位机制。定位：汇报=既有台账的收口投影，非第五台账；执法在主控，不建新 hook/常驻脚本（io-budgets 元规则：无 on_read_fail 语义键不新增脚本读者）。
## 档位映射（本件正本）
| 收口场景 | L 档（纲） | 本件补的机械判据 | 形态上限 |
|---|---|---|---|
| 关键项 | L2 逐项点名 | 轮内出现任一：escalate 判词 / must_fix / 治理红线被违反且主控已记录 / PENDING 用户裁决待办新增 / 水位解析失败行 | ≤5 项，每项一行=任务+进度+决策+证据指针；超出截断+报计数 |
| 常规项 | L1 增量缺省 | 水位差分命中且非关键项 | 每任务一行+状态，≤10 行 |
| 无变化项 | L1 末行 | 无差分命中或已完成无新落盘差分 | 一行计数「N 项无变化」（fail-close：无差分≠静默） |

升档触发器：常规项两次汇报间复现 ≥2 → 按关键项展开。复现判定落水位件 `strike` 计数（见水位节），机械可算。
频控：每 slug 每水位消费 1 次（items_hash 相同=已报，跳过展开仅一行）；轮询心跳仅一行。L0 场景（夜批/headless）不展开，仅异常即报+轮末总账行（L0 判：异常即报不展开）。
## 水位机制
- **件**：`.state/report-watermark.json`，slug 复合键 `{last_ts, items_hash, prev_hash, strike}`；并行需求各占键，禁全局单行（PENDING.md:46 互踩事故型）。
- **并发写防护**：写该件必须复用 `skill-evolution/scripts/shared_state.py` 既有 helper——`flock_ctx`（:68）+`atomic_write`（:126），禁裸 open-write（3d5d2c9 并行卷积先例、knowledge-recall N1 同款风险）。
- **差分口径**：全局差分——台账行无 slug 字段，跨会话体系活动均在汇报射程内（用户需求「近期所有任务」原意）；输出按议题/部门分块职责分离去噪。
- **ts 解析**：秒级源用 原 stop-gate _parse_ts 口径（脚本已移除，口径文字保留）（仅认 `%Y-%m-%d %H:%M:%S`）；**日粒度源（ceo-verdicts 等）系独立判分支**：取日期段与水位日期比较，不经 _parse_ts；两口径外格式=解析失败行，fail-close 计关键项待报，禁静默吞（格式漂移实证：invocations.jsonl:968/1463/1512/1513 四形态在案）。
- **写时点**：汇报产出同回合最后一步写水位（flock+atomic）；items_hash=当轮已报项拼接摘要 hash，prev_hash 存上轮值——hash 相同=重复收口，跳过展开防重报；strike=同项连续出现轮数，≥2 触发升档。
- **fail-close**：无差分命中 ≠ 静默，按「N 项无变化」一行报。
## 形态约束
- 分块：对内优化/对外探索等按议题分块，内容不交叉（USER-PREFERENCES.md:15）。
- 行数：沿用所在域既有 `report_inline_max_lines`（域=30，io-budgets.json 同名键）；键缺位时主控裁决暂沿用用 30（同笔 PENDING 登记，禁内联另立数值单源）。
- 表达：五要素（简洁/层次/条理/严谨/精炼）；关键项必带仓内证据指针；澄清集中末尾（托管语义，USER-PREFERENCES.md:23）。
- **表达结构 v2·BLUF 折叠式（2026-09-30 表达战役 R10-R14 双通道定版；本条为汇报档现役基准格式；格式换代治理=skills/_shared/expression-scorecard.md，本条为现役基准格式）**：汇报/日汇总/任务总账的行文骨架——①首行 BLUF 三段式总结论（结果面 ✅ 计数/遗留面 ⏳ 计数/状态面「等待 X」），只读首行即全况；②中段每议题一紧凑行：`议题 ✅/⏳（关键数值）→ 箭头指向触发器或下一步`，状态标记 ✅/⏳ 统一符号系；③尾行读数+下一步（首尾呼应闭环）。机械指标定版锚：关键信息保留 10/10、字符压缩 -63% vs 旧分层 bullet、黑帽盲评 19/20 全维第一（ranking B3>B1>B2>B4，评分件在案）；已知缺陷=单行指针化解码成本，缓解=触发器旁挂仓内文件锚。适用射程=L1/L2 汇报与轮末总账；L0 与逐项展开档不适用（仍按各档既有形态）。外参锚：BLUF（en.wikipedia.org/wiki/BLUF_(communication)）、Minto 金字塔答案先行+MECE（managementconsulted.com/pyramid-principle/）。
## 依据锚
- 纲与立项：汇报档位轴（2026-09-26 立，7 天画像 72% 托管语义+两次显式提出，handoff-modes.md 本仓未包含）；USER-PREFERENCES.md:22-26（档位硬标准/托管不打断/自修改克制/骨架优先）。
- 外部锚：openstatus severity-matrix（档=影响阈值×更新节奏×升级路径查表）、sre.google managing-incidents（受众分层）、chezmoi apply verbose（since-last-check diff 形态）、arXiv:2604.23049（HITL 解耦）、arXiv:2609.06063（trace-faithful 报告）、docs.langchain.com langgraph interrupts（结构化送达）——URL 全列见 BACKLOG 本轮登记行。
- 审查留痕：异质化探针修正 4 点（全局差分口径/_parse_ts 复用边界/hash 频控锚/域键缺位登记）+ task-driver R1 评审 escalate 2 项处置（L 档归并消双头/水位并发写补 flock+atomic），评审件 `.state/task-driver-reviews/report-proto-r1.json`。
