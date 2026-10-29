# adas-assist v1.0 当前计划

本仓仅支持 Codex。本文汇总当前状态、验收边界与下一步；命令和规则正文以对应本地文件为准。历史版本的重复计划、过时计数和临时目录指针已收敛。

## 目标与边界

- 六模式任务协作、内部修饰符、初始化、质量检查与恢复。
- 根 skills/commands/agents/standards 是维护单源，直接复用已有资产。
- 按用户最新裁决移除独立分发层，os 与既有技能统一放在 skills/，不保留安装器、导出清单或副本同步。
- 不修改用户全局配置或既有安装，不提交、推送、发布或启动后台任务；保留本批之外的在途修改。

## 当前实现

| 范围 | 状态与本地单源 |
|---|---|
| os | 六模式及 init/help；维护源 skills/os/ |
| 内部组合 | +b/+k/+l/+v/+c/+n，见 modifiers.md；plan/review 边界优先 |
| 命令 | commands/ 保存本次可读正文；Codex 当前使用 $os 适配，不把 Markdown 当作已注册斜杠命令 |
| 角色 | agents/ 与技能内角色保留职责正文，移除其他宿主元数据；按当前工具类型委派 |
| Codex入口 | .agents/skills/ 相对软链接指向根技能，直接修改维护源 |
| 初始化 | 只读项目根盘点；有效指引、Git、真实发现另验 |
| 质量 | quality.md 覆盖入口、command、模式、agent、共享规则、工具与宿主 |
| 本仓记忆 | memory/MEMORY.md→本仓正文；决策索引 decisions/KNOWLEDGE.md→决策正文 |
| 文件工具 | 记忆扫描/回放要求显式目录；共用状态要求成对显式资产/数据根 |

已移除第二宿主安装分支、CLAUDE 指引、bootstrap 模板、事件脚本及无消费者的配套配置。复用的解析与分词迁至 memory-governance/scripts/recall_core.py，状态工具迁至 _shared/scripts/shared_state.py；没有宿主全局目录回退。工作区中的原内容在删除前保留恢复副本，未据此覆盖其他在途修改。

## 关键整改

- gate：输入严校验，维度底线、必须修复项、终轮与停滞分支按协议判定。
- PCF：主控核证据并按摘要/JSON交接，角色输出原样落盘；planning 接受当轮任一合法候选 ID 或 neither。
- ADR：检查正确根、状态、双向链和计数；无实际 ADR 时 no_data，不建立空条目。
- memory：索引/正文分工、显式目录、同一解析器、越界和软链接反例；缺探针为 no_data。
- 共享规则：改为当前任务显式消费，无自动指标、采集、召回、清理、后台评估或提交门禁。
- 文档：仅本地路由，清理重复用法、外参入口与过时兼容说明。

## 前序逐技能检查与保留边界

以下保留既有最小题面结论，不代表本轮重新运行，也不代表完整 workflow 或生产效果验收。

| 技能 | 前序实际检查（历史记录） | 保留边界 |
|---|---|---|
| decision-explore | 有目标的澄清产物；目标缺失不执行；补齐收敛协议 | 未逐条运行全部追问/拒答分支 |
| decision-consensus | 共识计算；3独立视角→去标识摘要→独立finalizer文件交接（4/4要点一致=100） | 单轮无争议演练；多轮分歧/critic分支未验 |
| decision-improve | 证据与假设区分、复盘/CAPA字段；纠正severity反向及复发链字段矛盾 | CAPA真实实施及效果回填未执行 |
| decision-lifecycle | 一次性不新增、重复且可测才建议；产物字段与门槛 | 未真实增删/拆合技能 |
| decision-record | ADR产物；meta/data正反fixture、状态/双向取代、计数与路径边界 | 本仓实际ADR=0，检查输出no_data；未创建真实ADR充数 |
| decision-verify | 实跑gate clean/底线/must-fix/终轮/停滞/非法输入；独立反例复验 | 未执行full全部红蓝轮次与全部PCF分支 |
| devils-panel | 修正模板消费者字段/零挑战裁判分支；独立正反各两轮→第三上下文裁判，结果compromise | 独立角色为虚构题面；零挑战/reject分支只做静态复核 |
| effect-governance | 有/无证据判定及no_data、评估协议与路由 | 无真实账单/调用日志，不能报告效果或省token收益 |
| finish-check | 已知缺项题面按BLOCKER判；不滥用real-run免检；batch标记文件工具fixture | 未完整运行双reviewer/full评分流程；无自动提交拦截 |
| info-collection | 采集格式/ADR分类分流、拒绝原文入git；旧采集相关隔离测试 | 当前仅显式手动维护 |
| io-governance | 真实预算JSON、合规/违规虚构回传核对 | 无真实3会话注入/回传读数，不计算总体违规率 |
| memory-governance | 显式memory/data根扫描、复用生产parser/tokenizer回放、正负/空数据/越界fixture | 不接隐藏Codex memory；不读写宿主隐藏记忆；不声称生产命中率 |
| skill-evolution | 准入/拒绝题面、前序隔离套件（相关脚本现已移除）；缺JSON fixer改为原角色重发一次后失败停机 | 未部署自动进化、worktree变更或定时任务；无效果数据不进化 |
| os | 本次真实读取并按managed执行；task.py隔离init/start/record/finish及输入漂移 | 六模式完整行为、周期实际触发及真实宿主调度未全验 |


## 本批验证

维护者交付前运行下列命令，并在本节填写实际读数。检查命令以仓库根为工作目录。

| 检查 | 命令 |
|---|---|
| 任务状态与边界 | python3 -B -m unittest discover -s skills/os/tests -v |
| 共享规则、状态与仓库契约 | python3 -B -m unittest discover -s skills/_shared/tests -v |
| 记忆边界 | python3 -B -m unittest discover -s skills/memory-governance/tests -v |
| ADR 边界 | python3 -B -m unittest discover -s skills/scripts/tests -v |

2026-10-29 根资产迁移基线：此前独立分发套件44/44、共享30/30、记忆12/12、ADR4/4通过；这些是历史读数，不作为迁移后验证。按用户最新裁决迁移 os 及其15项任务行为测试，删除29项只覆盖已退役安装/导出的测试，不将测试数量下降当作同等覆盖。

迁移后初跑：任务15/15通过；共享测试发现软链接数量固定15的旧断言，现改为按根技能集合和目标逐项核对。整改后实跑：任务15/15、共享30/30、记忆12/12、ADR4/4全部通过；git diff --check通过。相对链接与外部指向静态扫描无残留独立分发路径。独立 reviewer（Sol；实际用量未知）复跑同一61项测试通过；从迁移前备份核11件os有效源均保留，task.py、模板、UI与resources共4件字节一致，15个测试函数AST一致。全部16个入口（14技能与2辅助）为可跟踪相对软链接；指定迁移范围无未处置must-fix。审查为风险定向核验，不据此推算总体漏检率。

已移除独立分发目录、安装器、回执与导出清单；根任务脚本不改协议，初始化按本地契约手动检查，所有技能由相对软链接供 Codex 发现。未修改用户全局配置、创建后台任务或提交发布。

## 未决与下一步

1. 新 Codex 会话的技能发现、UI 与完整行为矩阵仍需宿主验收；文件检查不代替模型行为。
2. 自定义斜杠命令和仓内角色的原生注册尚未完成验证；当前只确认共享正文、$os 适配及环境提供的代理类型。
3. 全技能多轮争议、CAPA实际效果、长期进化及生产召回率未由最小题面证明。
4. 没有可得真实用量，不报告额度、金额或节省比例；公开许可和发布保持未完成。
