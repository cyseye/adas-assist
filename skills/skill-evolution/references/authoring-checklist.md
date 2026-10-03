# Skill 写作检查单（官方 authoring best practices 收口）

> 来源：Anthropic 官方 Skill authoring best practices（platform.claude.com，2026-06 版）提炼收口，一处定义。新建 skill 写作时对照；skill-evolution Step 1b 对无专属 checklist 的目标 skill 以此为通用审查依据。

## 1. frontmatter 硬约束

- `name`：≤64 字符，仅小写字母/数字/连字符；禁 XML 标签与保留词（anthropic/claude）
- `description`：≤1024 字符非空；**第三人称**（注入 system prompt，视角不一致致发现失败）；**what + when 双要素** + 具体关键词——从 100+ skill 中被选中的唯一依据，禁 vague（"帮助处理文档"）

## 2. 精简原则（token 是公共资源）

- 默认假设：模型已经聪明——只写模型不知道的；每段自问"这段值不值这些 token"
- SKILL.md 正文 **<500 行**，逼近即拆分

## 3. 自由度分级（按任务脆弱度选）

| 级别 | 形态 | 适用 |
|------|------|------|
| 高 | 文本指引（多种做法皆可） | 上下文决定路径，如 code review |
| 中 | 伪码/带参模板 | 有首选模式但允许变化 |
| 低 | 精确脚本+禁改声明 | 脆弱操作/顺序敏感，如迁移脚本 |

## 4. 渐进式披露（三种官方模式）

- 高层指引+references / 按域组织文件（问 sales 只读 sales.md）/ 条件细节（基础在正文、进阶按需链接）
- **引用一层深**：所有 reference 直接从 SKILL.md 链接，**禁嵌套引用**（reference 引 reference——模型会 head 预览致信息不完整）
- reference **>100 行加目录**（TOC）

## 5. 工作流与反馈环

- 复杂多步任务给**可复制进回复逐项勾选的 checklist**
- 质量关键任务带 validate → fix → repeat 反馈环，验证不过不前进

## 6. 内容纪律

- 无时效信息（过期即错）；旧方法放"old patterns"折叠节留历史
- 术语一致（选定一个词贯穿，禁 endpoint/URL/route 混用）
- 示例具体可仿（输入/输出对优于抽象描述）

## 7. 通用模式

- Template：严格要求用"ALWAYS use this exact template"，弹性用"sensible default, use judgment"
- Examples：给 2-3 个输入→输出对传达风格
- 条件工作流：决策点显式分支（Creating? → A 流程；Editing? → B 流程）

## 8. 脚本类 skill 附加项

- **solve, don't defer**：错误在脚本内处理（FileNotFound 建默认文件），不抛给模型兜
- 无 voodoo 常量：每个值注明理由（"30s 因慢连接；3 次因多数间歇故障二次即解"）
- 依赖显式：所需包在指令中列明并给安装命令；执行 vs 阅读意图写明（"Run x.py" vs "See x.py"）
- 高风险批量操作走 **plan-validate-execute**：中间产物（changes.json 类）先脚本验证再执行
- 路径一律正斜杠；MCP 工具用全限定名 `ServerName:tool_name`

## 9. 测试与迭代（对照本体系落点）

| 官方要求 | 本体系对照 |
|---------|-----------|
| 评估先行（先建 ≥3 场景评估再写文档，测真实缺口非想象需求） | skill-evolution baseline 自然回填（骨架优先哲学：先最小骨架后量化——差异已记 ADR，维持本体系） |
| A/B 双实例迭代（Claude A 写、Claude B 用、观察回改） | 主控写 skill + 真实使用观察（invocations 留痕 + 纠偏三档）等价承载 |
| 观察模型实际怎么用（意外路径/漏跟链接/过度依赖/忽略文件） | session-review 冷/热/死 skill 信号 + 用户纠正沉淀 |

## 10. 交付前检查（官方 checklist 收口）

- [ ] description 双要素+第三人称+关键词
- [ ] 正文 <500 行；细节已按需拆分
- [ ] 引用一层深；>100 行 reference 有 TOC
- [ ] 无时效信息；术语一致；示例具体
- [ ] 复杂工作流有 checklist；关键任务有反馈环
- [ ] （含脚本）错误处理内聚；常量有理由；依赖显式；高危操作有可验证中间产物
