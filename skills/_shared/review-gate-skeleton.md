# 评审门公共约束

具体检查项、严重度、权重和阈值由调用方特化协议定义：decision-verify 与 finish-check 的 review-gate-protocol。两套词表不得混用；本文件不再复制数值。

## 编排与判定

- 主控读原始证据，选择档位，安排 reviewer，核输出与输入 schema。没有执行的步骤记 not_run。
- must-fix 与维度底线控制“是否可以通过”；轮次、停滞和争议控制“是否继续修复或交裁决”。达到上限仍有 must-fix 时升级，不能继续无限 FIXABLE，也不能接受为通过。
- 无评分档按其布尔检查表判定，不向计分工具伪造维度。评分档按选定 profile/tier 计算，输入错误应拒绝。
- finish-check 不带自动 fixer；修复须遵守其清单与现有授权。验证事实由原始文件/实跑结果支持。

## PCF 决策空间

| 决策 | 前置条件 | 后续 |
|---|---|---|
| fix_targeted | 问题可定位且修复在授权范围 | 按特化协议修复或 handoff，随后重新验证 |
| accept_with_flags | 无 must-fix；剩余取舍逐条有非空理由且在允许接受范围 | 保留未决问题与理由，不改写严重度掩盖问题 |
| escalate_to_user | 必要信息、权限、独立评审或可靠证据缺失 | 输出阻断、证据及所需裁决 |

## Finalizer 约束

只裁决当前证据和候选，不自行改规则、删除 must-fix、增加授权或伪造独立来源。输出选中方案、理由、未决风险及后续验证。必须修复项仍存在时，不得 `accept_with_flags`。协议冲突先报告，不静默挑选较宽松规则。

合法特化：verify 使用 P0/P1，finish-check 使用 BLOCKER/MAJOR/MINOR；数字以各特化协议为准。

## 评分与产物 schema

计分档：每维从100按该profile严重度扣分并截断在[0,100]，总分为各维分数乘该维权重之和；权重必须为正且总和为1。维度底线、通过线、升级轮次与具体词表由特化协议定义，不能用高总分抵消must-fix或底线失败。轻评审门为该skill定义的布尔检查表，重评审门为其评分/独立角色流程，档位不是新授权。

通用回传schema单源为io-protocol §3；验证/收尾报告schema仍由各自SKILL、references及模板定义，consensus保留自身proposal/summary/final及转写规则。通用命名：`{skill}.round.{N}.*.json` / `report.{skill}.final.json`；这些skill特化命名不强改为通用名。新增特化在此登记并指向具体单源，不复制字段定义。
