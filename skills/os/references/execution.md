# 任务契约与质量闭环

优先复用项目已有任务记录，不因使用 os 创建第二套。复杂任务没有既有载体时，可选择人工 TASK.md 或可选 task.py；同一任务只选一个状态源。用 CLI 时 task.json 是唯一状态源，说明/接力文档只引用它，不另维护状态表。

## 状态与边界

```text
planned -> active -> done
             |  ^     | reopen（说明原因）
             v  |     v
           blocked -> active
planned / active / blocked -> cancelled（说明依据）
```

CLI 的 start / block / resume / finish / reopen / cancel 只负责上述转换；blocked 表示实际缺前提，不能代替“工作量大”。finished 后代码或证据再变化，status 会报告漂移；它不会偷偷改状态，需要 reopen 后补验证。这里的文件状态不是后台执行服务。

人工模式复用 [TASK 模板](../templates/TASK.md)。CLI 模式状态在项目 `.adas-assist/tasks/<slug>/task.json`，写锁覆盖读取、校验、原子替换；锁冲突立即失败。崩溃遗留锁需先核所有者和任务文件再人工恢复，不自动抢锁。任务 JSON 可被使用者手改，工具不是防篡改或身份认证边界。

旧任务若保存了当前不支持的模式，status 仍可只读核查并报告模式问题，ready_to_finish 为 false；变更命令拒绝，不自动改写状态或模式。需先保留原文件，显式核对迁移到当前模式及受影响验收，不能把只读兼容视为旧入口仍可执行。

## 任务工具流程

维护源为 `skills/os/scripts/task.py`。下面在仓库根运行；`--project` 必须放在子命令前。所有 input/evidence 路径相对项目根，不接受符号链接、绝对路径或上跳。

```sh
python3 skills/os/scripts/task.py --project . init demo --goal '实现功能' --scope '当前任务授权范围' --accept R1=行为正确 --input src/example.py --independent-review
python3 skills/os/scripts/task.py --project . start demo
```

`--input` 可重复，列明受验代码、配置与关键依赖文件；待创建/删除的文件可以不存在，其缺失也被记录。范围不完整会漏检漂移，目录不作为输入。修改并真实验证后保存证据，立即 record：

```sh
python3 skills/os/scripts/task.py --project . record demo --criterion R1 --result passed --kind executed --summary '实际运行检查的结果' --evidence checks/test-output.txt
python3 skills/os/scripts/task.py --project . review demo --reviewer '真实评审来源' --verdict passed --summary '独立审查结论' --evidence checks/review.md
python3 skills/os/scripts/task.py --project . finish demo
python3 skills/os/scripts/task.py --project . status demo
```

record 的 result=passed/failed/not_run，kind=executed/static；工具不会代跑命令。review 的 verdict=passed/changes_required，只记录来源声明，不证明身份或独立性。finish 要求所有验收有 passed 声明，证据仍存在且内容一致，声明时的 input 范围/内容未变；启用 independent-review 的任务还须当前通过的评审声明。哈希一致不等于业务正确、测试充分或独立性成立，不能补录旧检查为新代码背书。

阻断/恢复需 `block/resume <slug> --reason '原因' --next '下一步'`；done 后补工作用 reopen，参数同上。取消需 `cancel <slug> --reason '用户或任务取消依据'`。CLI 不维护步骤队列、租约、心跳或重试调度。只用它管理必要验收，避免拆成大量小任务。

## 执行与验证

维护协作能力本身时使用 [质量清单](quality.md)，覆盖本批入口、角色、共享规则、工具与宿主链路；普通业务任务仅核命中能力，不默认扩大为体系审计。

- 先确定工作域、授权与项目写入边界。开工核 Git 状态、规则和实现，保留他人改动，不以整树干净作为验收条件。
- 目标与验收对应；计划写依赖、输出与必要检查。共享接口先查调用方，优先既有能力、平台原生与标准库。
- 生产写入、破坏性迁移、发布等难撤销动作，执行前核授权、验证/回退与必要独立复核；条件不齐停在可审阅产物。此门不由 finish 代替。
- 委派需要当前环境支持和授权，输入只带目标、约束、文件、写域和验收；写域重叠就顺序执行，负责人串行合并。
- 验收 → 产物 → 实际检查/静态判断 → 结果与限制逐项对应。核心架构或重要风险需要独立评审；能力缺失保持待验，不以自审替签。
- 失败定位域、错误、证据和修复方向，定向整改复验。任务根因改进不连长期知识与自进化管线。

## 接力

关键节点保存目标与授权、状态来源、工作树和变更文件、决策、实际验证、未决、下一步。长日志保留可访问指针。

recover 先读状态再核实际工作树、文件与证据。CLI status 可检测声明输入和证据漂移；其他未纳入输入的文件、外部服务与环境变化仍需人工判断。只复验受影响部分，不假设宿主压缩前自动保存，也不将旧 done 直接当当前成功。
