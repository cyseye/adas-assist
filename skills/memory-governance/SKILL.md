---
name: memory-governance
description: "记忆目录治理：本仓 memory/ 或宿主显式目录与 MEMORY.md 对账及 ADR/KNOWLEDGE 分流。触发词：memory 治理/记忆清理/教训沉淀（纠偏类信号沉淀归 corrections 单源，决策/ADR 沉淀归 decision-record，本件管 memory 层资产治理）/memory 压缩/索引对账/召回回放。"
---

# memory-governance · memory 层治理

治理宿主显式提供的 memory 数据与 ADR/KNOWLEDGE 的重复与结构漂移。核心哲学：**机器只做结构对账，语义判断留主控**；治理对象可能不在 git，删改以召回回放兜底。Codex 环境不假定可访问平台隐藏 memory。

Codex 对项目 memory/fixture 必须显式指定 `--memory-root`；回放还必须指定隔离的 `--data-root`。格式和边界见 [host compatibility](references/host-compatibility.md)。缺参拒绝，不回退宿主目录。

合并保留原条目名、关键词与来源指针，修改后同步 MEMORY.md 索引和计数；回放只与同输入、同实现口径的基线比较。

## Step 0：范围界定（三层 memory 哪层）

**本仓 Codex 特化**：治理对象是仓库 `memory/`，先读 `memory/MEMORY.md` 索引再按需读正文；索引仅标题/路径/检索词，正文在 `memory/` 单源维护。宿主记忆只保留定位指针，不存正文副本；不沿用其他宿主路径、静态文件数量或历史命中率。决策类正文仍归 `decisions/` 等既有权威目录，由 `decisions/KNOWLEDGE.md` 索引，不复制进 memory。具体规则见 [host compatibility](references/host-compatibility.md)。

| 层 | 位置 | 本 skill 动作 |
|---|---|---|
| 平台 memory | `{memory_root}/`（散文件+MEMORY.md 分组索引） | **治理对象** |
| 跨机偏好 | `{preferences_file}` | 不动（仅声明在范围） |
| 项目业务约定 | 项目 `.adas-assist/memory/*.md` | 不动（仅声明在范围） |

> 沉淀归口（战役 20260917 #3）：memory 写路径唯一责任人在 decision-record 记忆沉淀尾步；本 skill 只治不改源。

## Step 1：机器扫描（结构对账）

```bash
# Codex：使用宿主明确提供的 MEMORY.md 目录与隔离数据目录
python3 skills/memory-governance/scripts/scan-memory.py --memory-root memory
python3 skills/memory-governance/scripts/recall-replay.py r1 --memory-root memory --data-root .build/memory-replay-fixture
```

五项对账（信号统一 `memory-structure-drift`，low 风险）：

| 项 | 判定 | 修复动作 |
|---|---|---|
| 孤儿索引行 | 索引行指向已删文件 | 删该索引行 |
| 漏索引文件 | 散文件未登记索引 | 补索引行（含钩子） |
| 悬空 `[[链接]]` | 指向不存在条目 | 修链接或删引用 |
| 计数锚点 | `<!-- 计数：N -->` ≠ 实际散文件数 | 回填 N |
| 索引行钩子缺失 | 索引行 `— ` 后为空 | 补钩子（召回锚点=title+hook，钩子空=锚点减半） |

结构信号由本次显式扫描产出；主控按当前授权执行后续治理。

## Step 2：交叉对照五裁决（语义判断，主控做）

对照源 = 元层 ADR（`decisions/adr/`）+ 两源 KNOWLEDGE。逐条 memory 给其一：

| 裁决 | 判据 | 动作 |
|---|---|---|
| ① 纯重复 | ADR 已承载结论、memory 无增量 | memory 压 1-2 行结论 + ADR 路径指针 |
| ② 细节回灌 | memory 含 ADR 缺的应用细节（跨项目通用 + ≥2 次实证） | 细节进 ADR **勘误段**（ADR 不可变，禁改写正文）；memory 压缩留指针。回灌不破单份 ADR 40 行线，破线只回灌指针 |
| ③ 正文佚 | ADR/项目侧原文已不存在，memory 是唯一存活载体 | memory **升格事实载体** + 标注承接关系 |
| ④ 无重叠 | 用户偏好/前端规则/项目复盘等 | 保留不动 |
| ⑤ 同类合并（v3 增补） | 多条目同 `type` 且语义同域（如多份授权裁决） | 按 type 合一，**节名=原条目名**+「承接原条目」前缀别名进钩子；外部指针改指 `件名.md §节名`（ADR 内文字提及不动） |

## Step 3：用户确认后执行

- 高风险面（删/并/回灌各抽代表）用户交互 抽查确认后再执行
- 执行后重建 MEMORY.md 索引：分组结构保持，**承接条目的钩子补入被并条目关键词**（防召回衰减），同步计数锚点

## Step 4：终验（三件全绿）

1. **机械终扫**：`scan-memory.py` 零信号
2. **召回回放**：`recall-replay.py`（显式指定 memory/data 根，读取同一组探针；不依赖工作目录推定宿主）：
   ```bash
   python3 skills/memory-governance/scripts/recall-replay.py r1 --memory-root memory --data-root .build/memory-replay-fixture
   ```

   使用相同输入先运行 r0，再运行 r1 对比；无探针日志则标 no_data。历史命中条目不可无承接删除。
3. **净行数负增长**：治理前后 `wc -l` 对比（压缩验收纲）

## Step 5：效果回填

本次治理完成后将结构结果、前后回放、未验证项与下一步并入既有任务记录。缺探针标 no_data，不能将零信号当作语义或效果通过。后续复验仅在用户要求或新问题出现时执行，无自动日档或周评估。

## 反模式

| 禁止 | 正确做法 |
|---|---|
| 语义去重机器化 | 五裁决留主控人肉判断 |
| 扫 frontmatter description 缺失 | 召回锚点=索引行（title+hook）+frontmatter `trigger:`；description 不参与召回 |
| 回灌改写 ADR 正文 | ADR 不可变，只加勘误段 |
| memory 文件 git 提交 | 平台 memory 不在版本管理 |
| 删条目不留承接 | 钩子补关键词 + 回放验证衰减 |
| 一轮治理跳过终验 | 结构检查通过，回放有证据或明确待验 |
| 验证脚本自写索引解析 | 一律走本地单源解析器 `recall_core._load_memory_index`（自写正则曾出正臂假 0 歧义） |
| 命中率冲分不提质 | 锚点吞他域词/embedding 吞并=挤占注入位+误召回，域分流口径下考核责任域 |
