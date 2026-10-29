# 知识生命周期

| 层级 | 内容 | 本仓落点 | 保留方式 |
|---|---|---|---|
| 长期 | 项目规则、技能、决策 | AGENTS.md、skills/、standards/、decisions/ | 按项目版本管理约定 |
| 中期 | 项目记忆、偏好、结论索引 | memory/、decisions/KNOWLEDGE.md | 正文与索引分开维护 |
| 会话 | 当前计划、执行状态、未决 | 项目既有任务载体 | 关键节点更新，恢复时核时效 |
| 临时 | 检查日志、中间产物 | .build/、.adas-assist/ | 核消费者后定向清理 |

原始用户输入、凭证、会话日志和私有运行数据不入库。项目 memory 与宿主隐藏记忆分别管理；仅使用明确授权的输入。

知识晋升须有真实来源、复用价值和当前授权；一次性纠错留本次记录，稳定规则进入对应正文，决策走 decision-record。索引只保留定位信息，不复制正文。

纠偏记录用 skills/_shared/templates/corrections-template.md；主控在本次任务维护 new→merged→stale→purged，合并须有落点与验证。无自动扫描、晋升或清理。

删除和合并先核引用及唯一事实载体，保留来源与承接关系；治理后复验索引、引用及必要回放。记忆治理归 memory-governance，决策维护归 decision-record。
