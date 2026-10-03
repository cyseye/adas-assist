# Checklist 维度与对象特化

## 用途

本文件是 review-rule（红队）的 checklist 输入，通过 review-rule 的 `checklist` 参数传入。定义 4 个通用验证维度 + 4 类对象的特化检查项。

review-rule 逐项校验后产出 issue，每条 issue 的 `dimension` 字段取值为本文件的维度名（正确性/安全性/规范性/完整性），供评审门按维度归档评分。

## 维度

| 维度 | 关注点 |
|------|--------|
| 正确性 | 逻辑/状态/数据是否符合预期 |
| 安全性 | 认证/授权/注入/越权 |
| 规范性 | 命名/格式/引用/结构约定 |
| 完整性 | 覆盖度/清单/场景是否齐全 |

> 评分权重真值=`verify-mapping.md` 权重表（默认 0.40/0.30/0.20/0.10，code 对象安全性 0.35）；本文件只定义维度供 issue.dimension 取值。

## 项格式

每项：`- [check_id] 规则描述 | severity: P0|P1 | 类型: 机械|AI`

- **机械项**：脚本可静态判定（格式/结构/命名/引用有效性），可由脚本或 review-rule 直接校验
- **AI项**：需语义判断（逻辑/安全/覆盖），由 review-rule 的 agent 能力评估

severity 映射（review-rule 执行）：error/high → P0；warning/medium/low → P1。

---

## 通用检查项（所有对象适用）

### 正确性（dimension: 正确性）

#### 机械项
- [COR-M01] 公开符号有显式类型/签名声明 | severity: P1 | 类型: 机械
- [COR-M02] 引用的标识符在作用域内已定义（无未定义引用） | severity: P0 | 类型: 机械
- [COR-M03] 控制结构闭合匹配（括号/标签/配对） | severity: P1 | 类型: 机械

#### AI项
- [COR-A01] 状态机含终态且无不可达状态 | severity: P0 | 类型: AI
- [COR-A02] 分支覆盖边界值（空/单/满/溢出） | severity: P1 | 类型: AI
- [COR-A03] 异常路径有显式处理（非静默吞没） | severity: P0 | 类型: AI

### 安全性（dimension: 安全性）

#### 机械项
- [SEC-M01] 外部输入进入查询/命令前显式参数化 | severity: P0 | 类型: 机械
- [SEC-M02] 敏感字段不在日志/响应中明文输出 | severity: P1 | 类型: 机械

#### AI项
- [SEC-A01] 鉴权检查覆盖所有越权路径（水平/垂直） | severity: P0 | 类型: AI
- [SEC-A02] 信任边界处做输入校验（非仅在内部校验） | severity: P1 | 类型: AI

### 规范性（dimension: 规范性）

#### 机械项
- [STD-M01] 命名符合约定（大小写/前后缀/词根） | severity: P1 | 类型: 机械
- [STD-M02] 文件/路径引用真实存在（无死链/空引用） | severity: P0 | 类型: 机械

#### AI项
- [STD-A01] 注释解释"为什么"而非复述代码 | severity: P1 | 类型: AI

### 完整性（dimension: 完整性）

#### 机械项
- [CMP-M01] 清单声明项与实际产出项一一对应 | severity: P1 | 类型: 机械

#### AI项
- [CMP-A01] 关键场景全覆盖（正常/异常/边界/并发） | severity: P0 | 类型: AI
- [CMP-A02] 需求点逐条有对应实现（反遗漏） | severity: P1 | 类型: AI

---

## 对象特化项

特化项叠加在通用项之上。对象类型判定见 `verify-mapping.md`。

### code 对象特化

- [C001] 状态机枚举含终态（如 CLOSED/FAILED），无悬挂中间态 | severity: P0 | 类型: AI | dimension: 正确性
- [C002] 异步操作有超时与取消处理 | severity: P0 | 类型: AI | dimension: 正确性
- [C003] 共享资源访问有并发保护（锁/队列/不可变） | severity: P0 | 类型: AI | dimension: 正确性
- [C004] SQL/命令拼接使用参数化，无字符串拼接注入面 | severity: P0 | 类型: 机械 | dimension: 安全性
- [C005] 依赖版本固定且无已知高危漏洞版本 | severity: P1 | 类型: 机械 | dimension: 安全性

### design 对象特化

- [D001] 设计与需求/既有组件一致（无臆造组件/属性） | severity: P0 | 类型: AI | dimension: 正确性
- [D002] 边界场景有交互设计（空/错/超时/极限） | severity: P1 | 类型: AI | dimension: 完整性
- [D003] 无交互死循环/无出口流程 | severity: P0 | 类型: AI | dimension: 正确性

### prd 对象特化

- [P001] 字段表/实体与原文一致（反幻觉：对照 .source/chapters） | severity: P0 | 类型: AI | dimension: 正确性
- [P002] 交叉引用真实可达（无死链/错链） | severity: P0 | 类型: 机械 | dimension: 规范性
- [P003] 章节结构完整（无缺失必要章节） | severity: P1 | 类型: 机械 | dimension: 完整性

### adr 对象特化

ADR 文档产物（`{slug}.md` + `KNOWLEDGE.md` 索引行）。ADR 对象特化项单源=`decision-record/references/adr-checklist.md`（28 项，review-rule 逐项校验），本表只列 verify 特有维度（dimension 归规范性/完整性，安全性基本不适用 ADR）。

### generic 对象特化

沿用上方通用项；无额外特化。调用方可在 checklist 追加自定义项（须含 check_id/规则/severity/dimension）。
