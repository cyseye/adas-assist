#!/usr/bin/env python3
"""t38-settings-guard.py — PreToolUse(Bash) 机械门（T38③，2026-09-26 CPE 缓解，用户授权挂载）。

背景：arXiv 2609.01222 C-4 向量——诱导写项目级/用户级 .claude/settings.json 即可注入
hooks 任意命令，本仓 defaultMode=bypassPermissions 下 permissions.allow 不构成闸。
本门=第二道闸：拦 Bash 工具对 */.claude/settings.json（用户级+项目级）的写类操作
（重定向/sed -i/tee/mv/cp/rm）。Edit/Write 工具不走本门（仍受权限系统管）。
合法变更路径=Edit/Write 工具+授权留痕（ADR 三要件）。
红线对账：纯机械正则，零模型调用；任何自身异常 fail-open exit 0（门故障不锁死会话）。
"""
from __future__ import annotations
import json
import re
import sys

# 写指示×目标耦合匹配（T111 收敛，2026-09-27 第5次活体误拦终修）：原「指示词全文命中 ∧
# 目标全文命中」松与，只读命令含 '>settings' 字符串/比较符即双中招。改为写形态直接
# 作用于 settings 目标：①重定向目标含 settings（>&file、2>file、>file 全覆盖，
# /dev/null 与 fd-dup 天然不中——目标不含 settings 字样即不匹配）；②写动词命令行
# 涉 settings；③python open(...,'w') 写 settings（heredoc 注入面）。
# (?<!-)仍排 '->' 箭头字样。
WRITE_TO_SETTINGS = re.compile(
    r"(?<!-)>\s*&?\s*\S*\.claude/settings\.json"
    r"|\b(?:tee|cp|mv|rm|truncate|dd)\b[^|;]*\.claude/settings\.json"
    r"|sed\s+-i[^|;]*\.claude/settings\.json"
    r"|open\s*\(\s*['\"][^'\"]*\.claude/settings\.json[^'\"]*['\"]\s*,\s*['\"][r+]*w"
)
SETTINGS_TARGET = re.compile(r"\.claude/settings\.json")  # 保留：报告文案判定用


def main() -> int:
    try:
        env = json.loads(sys.stdin.read() or "{}")
        if env.get("tool_name") != "Bash":
            return 0
        cmd = str((env.get("tool_input") or {}).get("command") or "")
        if WRITE_TO_SETTINGS.search(cmd):
            print("[t38-settings-guard] 拦截：Bash 写 settings.json 属 CPE C-4 注入向量面"
                  "（hooks 自改任意命令）。", file=sys.stderr)
            print("合法路径：用 Edit/Write 工具改（走权限系统），且须用户明示授权+ADR 记载+"
                  "git 备份三要件。", file=sys.stderr)
            return 2
        return 0
    except Exception:
        return 0  # fail-open：门故障不得锁死会话


if __name__ == "__main__":
    sys.exit(main())
