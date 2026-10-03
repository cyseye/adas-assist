# Worktree 隔离验证 SOP

回归验证在独立 worktree 中运行，验证通过后仅将 skill 文件变更归档到当前分支。产物随 worktree 删除，不污染用户工作区。

可用自动化脚本：`scripts/worktree-evolve.sh {skill} {ts}`

## 隔离流程（5 步）

```
1. 建隔离 worktree：
   git worktree add .claude/worktrees/evolve-{skill}-{ts} -b evolve/{skill}-{ts}

2. 在 worktree 中运行目标 skill（固定测试集）：
   cd .claude/worktrees/evolve-{skill}-{ts}/
   # 执行目标 skill，产物落在 worktree 内

3. 回归验证：在 worktree 中重跑目标 skill（固定测试集），主控按效果信号判定（提升/下降/持平，见 evaluation-flow.md §回归验证 SOP）

4. 按判定归档（仅归档 skill 文件，不归档产物）：
   # 提升 → 将 skill 变更合并到当前分支：
   git checkout <当前分支> -- \
     .claude/skills/{target}/EVOLUTION.md \
     .claude/skills/{target}/<本次改动的 skill 设计文件，逐文件列出>
   # 下降/持平 → 不归档，记录原因

5. 清理 worktree：
   git worktree remove --force .claude/worktrees/evolve-{skill}-{ts}
   git branch -D evolve/{skill}-{ts}
```

## 隔离边界

| 在 worktree 里（随删除清理） | 归档到当前分支（仅这些） |
|---|---|
| 目标 skill 生成的所有产物 | `EVOLUTION.md` 更新 |
| PCF 辩论对话（无文件化） | 已通过回归验证的 skill 文件修改 |
| `report.evolution.json` | — |
