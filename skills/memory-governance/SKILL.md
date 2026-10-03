---
name: memory-governance
description: "平台 memory 层治理：projects memory↔MEMORY.md 对账及↔ADR/KNOWLEDGE 分流。触发词：memory 治理/记忆清理/教训沉淀（纠偏类信号沉淀归 corrections 单源，决策/ADR 沉淀归 decision-record，本件管 memory 层资产治理）/memory 压缩/索引对账/召回回放。"
---

# memory-governance · memory 层治理

治理平台 memory（`~/.claude/projects/<slug>/memory/`）与 ADR/KNOWLEDGE 的重复与结构漂移。核心哲学：**机器只做结构对账，语义判断留主控**；治理对象不在 git，删改以召回回放兜底。

> **结构形态 v3 定版（2026-09-30，单源 ADR knowledge-management-v3-memory-tiering-20260930）**：平台 memory=3 件按 `type` 三分类（user 画像合一 / feedback 授权六合一 / project 基建事实）。新增条目先问能否并入既有件（对齐用户画像件数最少偏好）；确需新建须归入三分之一并同步分组索引+计数锚点。合并时**节名=原条目名**、旧名以「承接原条目：…」前缀保留进钩子（承接锚点别名制，防召回衰减+外部指针语义不断）。frontmatter `trigger:` 词表参与召回锚点，新件应设。验证口径为**域分流**（`recall-replay.py` 的 `domain_split`）：报数须同时给责任域命中率与混合口径，单独引用混合口径无效。

## Step 0：范围界定（三层 memory 哪层）

| 层 | 位置 | 本 skill 动作 |
|---|---|---|
| 平台 memory | `~/.claude/projects/<slug>/memory/`（散文件+MEMORY.md 分组索引） | **治理对象** |
| 跨机偏好 | `~/.claude/memory/USER-PREFERENCES.md` | 不动（仅声明在范围） |
| 项目业务约定 | 项目 `.claude/memory/*.md` | 不动（仅声明在范围） |

> 沉淀归口（战役 20260917 #3）：memory 写路径唯一责任人在 decision-record 记忆沉淀尾步；本 skill 只治不改源。

## Step 1：机器扫描（结构对账）

```bash
python3 ~/.claude/skills/memory-governance/scripts/scan-memory.py          # JSON 信号
python3 ~/.claude/skills/memory-governance/scripts/scan-memory.py --quiet  # 仅计数
```

五项对账（信号统一 `memory-structure-drift`，low 风险）：

| 项 | 判定 | 修复动作 |
|---|---|---|
| 孤儿索引行 | 索引行指向已删文件 | 删该索引行 |
| 漏索引文件 | 散文件未登记索引 | 补索引行（含钩子） |
| 悬空 `[[链接]]` | 指向不存在条目 | 修链接或删引用 |
| 计数锚点 | `<!-- 计数：N -->` ≠ 实际散文件数 | 回填 N |
| 索引行钩子缺失 | 索引行 `— ` 后为空 | 补钩子（召回锚点=title+hook，钩子空=锚点减半） |

结构信号由 session-review Stop hook 自动产出（import 本 skill 脚本），低风险主控自动消化走 Step1→Step3。

## Step 2：交叉对照五裁决（语义判断，主控做）

对照源 = 元层 ADR（`~/.claude/decisions/adr/`）+ 两源 KNOWLEDGE。逐条 memory 给其一：

| 裁决 | 判据 | 动作 |
|---|---|---|
| ① 纯重复 | ADR 已承载结论、memory 无增量 | memory 压 1-2 行结论 + ADR 路径指针 |
| ② 细节回灌 | memory 含 ADR 缺的应用细节（跨项目通用 + ≥2 次实证） | 细节进 ADR **勘误段**（ADR 不可变，禁改写正文）；memory 压缩留指针。回灌不破单份 ADR 40 行线，破线只回灌指针 |
| ③ 正文佚 | ADR/项目侧原文已不存在，memory 是唯一存活载体 | memory **升格事实载体** + 标注承接关系 |
| ④ 无重叠 | 用户偏好/前端规则/项目复盘等 | 保留不动 |
| ⑤ 同类合并（v3 增补） | 多条目同 `type` 且语义同域（如多份授权裁决） | 按 type 合一，**节名=原条目名**+「承接原条目」前缀别名进钩子；外部指针改指 `件名.md §节名`（ADR 内文字提及不动） |

## Step 3：用户确认后执行

- 高风险面（删/并/回灌各抽代表）AskUserQuestion 抽查确认后再执行
- 执行后重建 MEMORY.md 索引：分组结构保持，**承接条目的钩子补入被并条目关键词**（防召回衰减），同步计数锚点

## Step 4：终验（三件全绿）

1. **机械终扫**：`scan-memory.py` 零信号
2. **召回回放**：`recall-replay.py`（**必须从项目根跑**——REPO 依赖 cwd 上溯，在 memory 目录跑探针归零；读数看 `domain_split.memory_domain_rate`=责任域命中率，基线见下）：
   ```bash
   python3 ~/.claude/skills/memory-governance/scripts/recall-replay.py r1   # 与 r0 对比
   ```

   基线（2026-09-30 finish-check F3 勘误后，同生产 4 分口径）：责任域 **0.8378**（r10；前读数 0.9784 系 2 分松口径高估作废）
   硬线：证据集（历史真实命中过的条目）零丢失；条目消失须核对承接条目锚点已覆盖其关键词
3. **净行数负增长**：治理前后 `wc -l` 对比（压缩验收纲）

## Step 5：效果回填环（闭环收口，挂既有节奏不一刀切）

memory 生命周期闭环：**采集（hook 自动）→沉淀（decision-record）→召回（knowledge-recall）→消费（会话注入）→效果回填（本步）→治理（本 skill）→进化（skill-evolution）**。回填三档：

| 档 | 触发 | 动作 |
|---|---|---|
| 日档（自动） | session-review 结构信号 | 低风险自动消化（同 Step1→Step3） |
| 周档（挂周评估） | effect-governance 周评估 | 跑 `recall-replay.py` 一发，责任域命中率对账基线（单源 66 行，当前 0.8378·4 分口径）；跌破 -2pp 才立案，微小波动不追 |
| 决策档（用户门） | 结构变更（合并/拆分/口径改动） | v3 ADR 勘误+全流程，回放前后对照落台账 |

## 边界（知识进化部互指，V3 实施 1）

本 skill=memory 层治理（projects/<slug>/memory/ 散文件与索引结构）；三 skill 知识数据流边界单源 info-collection §统管边界，本件不复写。

## 反模式

| 禁止 | 正确做法 |
|---|---|
| 语义去重机器化 | 五裁决留主控人肉判断 |
| 扫 frontmatter description 缺失 | 召回锚点=索引行（title+hook）+frontmatter `trigger:`；description 不参与召回 |
| 回灌改写 ADR 正文 | ADR 不可变，只加勘误段 |
| memory 文件 git 提交 | 平台 memory 不在版本管理 |
| 删条目不留承接 | 钩子补关键词 + 回放验证衰减 |
| 一轮治理跳过终验 | Step 4 三件全绿才算闭环 |
| 验证脚本自写索引解析 | 一律走生产解析器 `kr._load_memory_index`（自写正则曾出正臂假 0 歧义） |
| 命中率冲分不提质 | 锚点吞他域词/embedding 吞并=挤占注入位+误召回，域分流口径下考核责任域 |
