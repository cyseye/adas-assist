# 知识分层与生命周期规范

> 四层分层模型与生命周期规约（决策见 ADR knowledge-doc-governance-consolidation）。主体守「层越高注入越频繁 → 高层必短、低层明细只检索不注入」。

## 一、四层模型

| 层 | 内容类型 | 存储位置 | 作用域 | git 策略 |
|----|---------|---------|--------|---------|
| L3 长期 | 纪律/规范/决策/技能定义/业务文档 | `CLAUDE.md`、`.claude/standards/`、`~/.claude/decisions/adr/`、`.claude/skills/*/SKILL.md`、`.claude/rules/`、`project-docs/prd/` | 全仓；CLAUDE.md 每会话注入，其余按需读取 | 分档：decisions 活跃域入库（knowledge-doc-governance-consolidation）；其余入库 |
| L2 中期 | 教训/结论/偏好/索引/进化记录/纠正追溯 | `~/.claude/decisions/KNOWLEDGE.md`、用户 memory（`~/.claude/projects/<proj>/memory/`）、`.claude/memory/`、`.claude/skills/*/EVOLUTION.md`、`.claude/.state/corrections/` | 项目级；召回式检索不注入全量 | 分档：KNOWLEDGE/postmortems 入库；PENDING 本地；.claude/memory/ 入库；EVOLUTION/corrections 本地（gitignore 覆盖） |
| L1 短期 | 会话/计划/待处理信号 | transcript（宿主管理）、`.claude/plans/`、`~/.claude/decisions/postmortems/PENDING.md` | 单会话~数天 | 全 ignore |
| L0 临时 | 中间产物/运行时状态 | `.build/`、`.claude/.build/`（白名单 2 项）、`.claude/.state/`（**运行时状态域，白名单不清理**）、`.claude/worktrees/` | 单任务 | 全 ignore |

## 二、层间流动

**晋升 L1→L2**（触发任一）：同类纠正/偏好 ≥2 次表达（reflex-check 检查3）；任务教训（主控当场）；验证结论（verify pass）；澄清结论（AskUserQuestion）。

- 压缩原则：写结论不写过程（summary ≤30 字）；不留 .build 路径引用（产物清理后必断链）；同主题 >3 条即合并。

**晋升 L2→L3**（触发任一）：机制/结论经 ≥2 次真实使用验证有效；决策级（跨会话架构/体系决策）；体系总结显式提取（adas-assist 大轮总结）。

- 压缩原则：ADR ≤40 行、决策语义优先（实现细节归 skill 条款）、slug 语义全局唯一禁编号、Supersedes 双向记录。

**老化**：L3 被取代且零活跃引用→物理删除（历史靠 git，无 archive 堆叠层）；**tombstone 例外流（2026-09-16 战略日历轮）**：无价值/暂不处理的探索与产物，用户确认后清理，但 KNOWLEDGE 留 tombstone 条目（判死理由+**复活条件**入摘要）——新知识/新战役命中复活条件时周批复盘提议复评，「删而可捡」；L2 零召回/超量合并→删、EVOLUTION 滚旧轮、corrections 清理 stale 与超量 merged；L1 plans>7 天清、PENDING 消除自清空。**老化 = 压缩或删除，不降层存储**（防内容下沉双层冗余）。

## 三、skill 纠正记录

- 模板：`~/.claude/skills/_shared/templates/corrections-template.md`；实例按 skill 落 `.claude/.state/corrections/<skill>.md`（用户原话含隐私，不入库、扫描范围外）
- 字段六项：id / 纠正原文 / 类型枚举（behavior/process/expression/artifact/bugfix）/ 生效条款位置+内容摘要（不写版本号）/ 验证方式 / 状态；维护规则：清理周期
- 状态机：`new`（记录未生效）→ 条款生效转 `merged`（保留追溯）→ 被取代/条款回退转 `stale` → 清理轮删 `purged`（仅保留最近 5 条 merged）
- 维护：新纠正当场追加；merged 验证 ≥2 轮可删（教训已由条款承载）；清理周期默认 8 轮/30 天（**试点期走人工门**——主控例行检查 + 用户确认；scanner 自动提醒待试点成熟后登记，不预建）

## 四、生命周期机制

- 自动发现：session-review.py（Stop 扫描 → PENDING.md）
- 分级消化：session-start.py（低风险自动仅汇报 / 高风险 AskUserQuestion）
- 自动清理：cleanup-builds.py（L0/L1 每会话；plans>7 天；final 守卫防误清活跃迭代）
- 人工门：L2/L3 删除、ADR 废弃删除、memory 清理——主控提议 + 用户确认

**护栏五条**：final 守卫（无收敛标志不清活跃产物）；白名单反转（.claude/.build 仅留运行数据）；只标记不删（删除类信号只写 PENDING）；三分法 + 主控 grep 复核；可恢复优先（入库删走 git 可恢复，本地文件双人门）。

## 五、边界核对

- 新增知识资产先判层再落位；分层边界与 .gitignore 分档不一致时以本规范为准并同步 .gitignore
- 召回侧（knowledge-recall.py / KNOWLEDGE 协议）不变——分层是写侧/清理侧约束
