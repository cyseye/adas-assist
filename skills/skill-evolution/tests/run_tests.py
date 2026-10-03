#!/usr/bin/env python3
"""skill-evolution 反射层 hook 测试（纯 stdlib，python3 tests/run_tests.py）。

隔离：每用例把 scripts+signal-tiers 复制进 tempfile 假树（hook 的 _repo_root 从
__file__ 向上解析，落进假树即天然隔离），session_id 强制 test- 前缀
（evolution-discipline 测试规范），绝不触碰真实 PENDING/reflex-start-state/jsonl。
"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# 与布局解耦：scripts/_shared 恒为本 tests 目录的祖父级邻接（仓内 skills/skill-evolution/tests
# 与安装位 .claude/skills/skill-evolution/tests 两形态同构）。原「上溯找 .claude 目录」在
# 仓内形态会爬到宿主 ~/.claude——测的是宿主脚本而非本仓脚本（R1 体检 2026-10-02 实证）。
HOST = Path(__file__).resolve().parent.parent  # .../skill-evolution
SCRIPTS = HOST / "scripts"
SHARED = HOST.parent / "_shared"


def build_tree(pending: str = "", adr_files: dict | None = None) -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="hooktest_"))
    sc = tmp / ".claude/skills/skill-evolution/scripts"
    sc.mkdir(parents=True)
    for f in ("session-review.py", "session-start.py", "shared_state.py"):
        shutil.copy(SCRIPTS / f, sc / f)
    (tmp / ".claude/skills/_shared").mkdir(parents=True)
    shutil.copy(SHARED / "signal-tiers.json",
                tmp / ".claude/skills/_shared/signal-tiers.json")
    # session-start 读 pending 预算走 asset 根 io-budgets（缺读=fail-tight 只留指针），
    # 假树须同拷，否则提案类断言恒空（t1/t6 假失败根因）
    if (SHARED / "io-budgets.json").exists():
        shutil.copy(SHARED / "io-budgets.json",
                    tmp / ".claude/skills/_shared/io-budgets.json")
    for d in ("meta", "data"):
        (tmp / ".claude/decisions/adr" / d).mkdir(parents=True)
    if pending:
        pm = tmp / ".claude/decisions/postmortems"
        pm.mkdir(parents=True)
        (pm / "PENDING.md").write_text(pending, encoding="utf-8")
    for rel, content in (adr_files or {}).items():
        f = tmp / ".claude/decisions/adr" / rel
        f.write_text(content, encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=tmp, check=True)
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t",
                    "commit", "-q", "--allow-empty", "-m", "init"], cwd=tmp, check=True)
    return tmp


def run_ss(tmp: Path, sid: str = "test-r1") -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(tmp / ".claude/skills/skill-evolution/scripts/session-start.py")],
        cwd=tmp, input=json.dumps({"session_id": sid}), capture_output=True, text=True)


ADR = "---\ntitle: 测试决策——示例条目\nstatus: Proposed\ndate: 2026-09-03\n---\n# t\n"
PEND = ("# 待处理信号\n\n## 按建议 skill 分组\n\n### → `decision-record`（1 项）\n\n"
        "- adr-consistency `adr/`: KNOWLEDGE 缺条目 foo-demo——按 KNOWLEDGE 单源对账机械回填/修复\n")

CASES = []


def case(fn):
    CASES.append(fn)
    return fn


@case
def t1_proposal_rendered():
    """缺条目 → 注入附精确追加行（title/status/date 齐全）。"""
    tmp = build_tree(PEND, {"meta/foo-demo.md": ADR})
    r = run_ss(tmp)
    assert "↳ 提案（确认才改）" in r.stdout, r.stdout[-500:]
    assert "- [测试决策——示例条目](adr/meta/foo-demo.md) | adr |" in r.stdout


@case
def t2_pending_untouched():
    """核心断言：提案零侵入——PENDING 字节级不变。"""
    tmp = build_tree(PEND, {"meta/foo-demo.md": ADR})
    before = (tmp / ".claude/decisions/postmortems/PENDING.md").read_bytes()
    run_ss(tmp)
    after = (tmp / ".claude/decisions/postmortems/PENDING.md").read_bytes()
    assert before == after, "PENDING 被写入——提案必须只走 stdout"


@case
def t3_mute_coupling():
    """提案随狼来了抑制：同 session 第 3 次连跑不再附提案。"""
    tmp = build_tree(PEND, {"meta/foo-demo.md": ADR})
    run_ss(tmp, "test-mute")
    run_ss(tmp, "test-mute")
    r3 = run_ss(tmp, "test-mute")
    assert "↳ 提案" not in r3.stdout, "第 3 次应随 mute 折叠，不再附提案"


@case
def t4_clean_tree_silent():
    """健康树（空 PENDING）→ 零提案文案（零噪声回归）。"""
    tmp = build_tree()
    r = run_ss(tmp)
    assert "↳ 提案" not in r.stdout


@case
def t5_malformed_tolerant():
    """slug 文件缺失/畸形行 → 不崩溃、不产提案、exit 0（容错）。"""
    tmp = build_tree(PEND)  # 未建 foo-demo.md
    r = run_ss(tmp)
    assert r.returncode == 0, r.stderr[-300:]
    assert "↳ 提案" not in r.stdout


@case
def t6_title_fallback_h1():
    """frontmatter 无 title（部分 ADR 靠 H1 承载）→ 提案标题回退 H1 而非 slug。"""
    adr_no_title = "---\nstatus: Accepted\ndate: 2026-09-02\n---\n# H1 承载的标题\n\n正文\n"
    tmp = build_tree(PEND, {"meta/foo-demo.md": adr_no_title})
    r = run_ss(tmp)
    assert "- [H1 承载的标题](adr/meta/foo-demo.md) | adr |" in r.stdout, r.stdout[-500:]


def main() -> int:
    failed = 0
    for fn in CASES:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {fn.__name__}: {e}")
    print(f"{len(CASES) - failed}/{len(CASES)} pass")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
