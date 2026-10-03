#!/usr/bin/env python3
"""gate-assist.py — 验证门机械环节三合一（零模型调用）。

token 治理第二轮（ADR adr/data/token-effect-balance-v2）落地：PCF 转发+代写、verify
每轮评分判定、finish-check 批次 digest 三类环节此前由主模型逐轮手工执行，但均为
纯机械传递/算术——skill-design §脚本vsAI 分工表本就判给脚本。实测每次 PCF 运行
占主控 4-5 轮（2 次转发+3 次代写）、verify 每轮 ~3 轮，均不产生语义增量。

子命令：
  pcf-save      代写 pcf.{role}.md 落盘（接力落盘硬约束的脚本化，契约见
                _shared/pcf-execution-flow.md；断链=假装饰决，写失败非零退出）
  pcf-context   组装下一位（critic/finalizer）context JSON 到 stdout，
                汇聚 .build/{slug}/ 现存全部 pcf.*.md 并点名路径
  verify-judge  按 review-gate-skeleton 评分公式+判定优先级表算轮次判定
                （两套词表：默认 decision-verify 特化 P0×25/P1×8；--profile base
                = BLOCKER×40/MAJOR×10/MINOR×3）
  finish-batch  批次 digest（与 reflex-check 检查1 一字不差：porcelain 代码类
                改动整行含 XY 前缀、剔 .claude/ 豁免、sorted join sha256 前 8 位）；
                --write 落 verdict 行，--check 与末条比对（校验批未漂移）

各消费 SKILL.md 引用本脚本时写「调 gate-assist.py <子命令>」，不再内联手工步骤。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# 与 reflex-check.py CODE_SUFFIXES 双源同改（一处收口需跨目录共享模块，当前规模
# 不值——任一侧改词表须 grep 对方确认）；.claude/ 豁免前缀同步
CODE_SUFFIXES = {".java", ".ts", ".tsx", ".js", ".jsx", ".xml", ".sql", ".py", ".yaml",
                 ".yml", ".json", ".css", ".scss", ".html", ".sh", ".vue"}
EXEMPT_PREFIX = ".claude/"

# 严重性词表两套（review-gate-skeleton §合法特化登记；改扣分值两处同改）
PROFILES = {
    "base": {"BLOCKER": 40, "MAJOR": 10, "MINOR": 3},
    "verify": {"P0": 25, "P1": 8},
}


def data_root() -> Path:
    """运行时数据根——单源委托 shared_state.data_claude()（cwd 上溯首个含 .claude
    的目录，资产仓内嵌套 .claude 幻影根排除）。2026-09-18 复验轮裁决：本地
    cwd/skills 判据对含 skills/ 目录的普通仓误判、与消费者（reflex-check 等同走
    data_claude）口径分裂，故收敛单源，禁再本地重实现。"""
    _sys = Path(__file__).resolve().parents[2] / "skill-evolution" / "scripts"
    if str(_sys) not in sys.path:
        sys.path.insert(0, str(_sys))
    from shared_state import data_claude

    return data_claude()


def build_dir(slug: str) -> Path:
    return data_root() / ".build" / slug


def _git_porcelain_code_lines(repo: Path) -> list[str]:
    """reflex-check 检查1 同款取数：porcelain 整行、rename 取新路径、剔豁免前缀、
    只留代码类后缀。行文本一字不差（digest 失配=finish 标记静默失效）。"""
    try:
        out = subprocess.run(["git", "-C", str(repo), "status", "--porcelain"],
                             capture_output=True, text=True, timeout=10, check=True).stdout
    except Exception as _e:  # 留痕批：读空曾静默退化为空串哈希（B2-1），先可观测后语义
        print(f"[gate-assist] git porcelain 读失败，digest 退化空集：{_e}", file=sys.stderr)
        return []
    lines = []
    for ln in out.splitlines():
        if not ln.strip():
            continue
        path = ln[3:].strip().strip('"')
        if path.startswith(EXEMPT_PREFIX):
            continue
        if " -> " in path:  # rename 取新路径
            path = path.split(" -> ", 1)[1]
        if Path(path).suffix.lower() in CODE_SUFFIXES:
            lines.append(ln)  # 整行=含 XY 状态前缀
    return lines


def cmd_pcf_save(args) -> int:
    if not args.content_file:
        content = sys.stdin.read()
    else:
        content = Path(args.content_file).read_text(encoding="utf-8")
    if not content.strip():
        print("[pcf-save] 内容为空，拒写（断链防护）", file=sys.stderr)
        return 2
    path = build_dir(args.slug) / f"pcf.{args.role}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"[pcf-save] 已落盘：{path}（{len(content)} 字符）")
    return 0


def cmd_pcf_context(args) -> int:
    d = build_dir(args.slug)
    products = sorted(d.glob("pcf.*.md")) if d.is_dir() else []
    if not products:
        print(f"[pcf-context] {d} 无前置产物（proposer 未落盘？）", file=sys.stderr)
        return 2
    ctx = {
        "round": args.round,
        "prev_products": [{"role": p.stem.split(".", 1)[1], "path": str(p)} for p in products],
        "briefs": {p.stem.split(".", 1)[1]: p.read_text(encoding="utf-8")[:3000] for p in products},
    }
    print("```json")
    print(json.dumps(ctx, ensure_ascii=False, indent=2))
    print("```")
    print(f"→ spawn 前置提示：finalizer/critic prompt 须逐份点名上列 path（接力约束）。")
    return 0


def cmd_verify_judge(args) -> int:
    data = json.loads(sys.stdin.read() if not args.report else Path(args.report).read_text(encoding="utf-8"))
    weights = PROFILES[args.profile]
    must_fix = data.get("must_fix") or []
    rounds = data.get("thresholds") or {}
    round_no = data.get("round", 1)
    prev_scores = data.get("prev_scores") or []

    scores, total, weight_sum = {}, 0.0, 0.0
    floor_breaches = []
    for dim in data.get("dimensions", []):
        sev = {}
        for issue in dim.get("issues", []):
            s = issue.get("severity", "P1")
            sev[s] = sev.get(s, 0) + 1
        score = max(0, 100 - sum(sev.get(k, 0) * w for k, w in weights.items()))
        scores[dim["name"]] = score
        w = dim.get("weight", 0)
        total += score * w
        weight_sum += w
        if score < dim.get("floor", 0):
            floor_breaches.append(dim["name"])
    total = round(total / weight_sum, 1) if weight_sum else float(sum(scores.values()) / max(len(scores), 1))

    # 判定优先级表（review-gate-skeleton §判定逻辑，从高到低，逐条短路）
    if must_fix:
        verdict, reason = "FIXABLE", f"must_fix={len(must_fix)}（一票否决）"
    elif floor_breaches:
        verdict, reason = "FIXABLE", f"维度底线未达：{'、'.join(floor_breaches)}"
    elif total >= rounds.get("pass", 90):
        verdict, reason = "PASS", f"总分 {total} ≥ 通过线 {rounds.get('pass', 90)}"
    elif round_no == 1 and total < rounds.get("critical", 70):
        verdict, reason = "PCF", f"首轮 {total} < 临界线 {rounds.get('critical', 70)}"
    elif len(prev_scores) >= 1 and abs(total - prev_scores[-1]) < rounds.get("converge", 5):
        verdict, reason = "PCF", f"plateau：与上轮分差 {abs(total - prev_scores[-1])} < {rounds.get('converge', 5)}"
    elif round_no >= rounds.get("max_rounds", 3):
        verdict, reason = "PCF", f"超轮次（round {round_no} ≥ {rounds.get('max_rounds', 3)}）"
    else:
        verdict, reason = "FIXABLE", f"总分 {total} 未达通过线，可修复进下一轮"
    print(json.dumps({"verdict": verdict, "reason": reason, "total": total,
                      "dimension_scores": scores, "floor_breaches": floor_breaches},
                     ensure_ascii=False, indent=2))
    return 0


def cmd_finish_batch(args) -> int:
    repo = Path.cwd()
    lines = _git_porcelain_code_lines(repo)
    digest = hashlib.sha256("\n".join(sorted(lines)).encode()).hexdigest()[:16][:8]
    verdicts = data_root() / ".state" / "finish-verdicts.jsonl"
    if args.write:
        verdicts.parent.mkdir(parents=True, exist_ok=True)
        entry = {"ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "batch": digest,
                 "method": args.method, "note": args.note or ""}
        with verdicts.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
        print(json.dumps(entry, ensure_ascii=False))
        return 0
    last = ""
    if verdicts.exists():
        for ln in verdicts.read_text(encoding="utf-8").splitlines():
            try:
                last = json.loads(ln).get("batch", last)
            except json.JSONDecodeError:
                continue
    match = "n/a" if not last else ("MATCH" if last == digest else "DRIFT")
    print(json.dumps({"batch": digest, "changed_code_files": len(lines),
                      "last_verdict_batch": last or None, "status": match},
                     ensure_ascii=False))
    return 0 if match != "DRIFT" else 1


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("pcf-save", help="代写 pcf.{role}.md（接力落盘）")
    s.add_argument("--slug", required=True)
    s.add_argument("--role", required=True, choices=["proposer", "critic", "finalizer"])
    s.add_argument("--content-file")
    s.set_defaults(fn=cmd_pcf_save)

    s = sub.add_parser("pcf-context", help="组装下一位 context JSON")
    s.add_argument("--slug", required=True)
    s.add_argument("--to", required=True, choices=["critic", "finalizer"])
    s.add_argument("--round", type=int, default=1)
    s.set_defaults(fn=cmd_pcf_context)

    s = sub.add_parser("verify-judge", help="评分+轮次判定（stdin 或 --report JSON）")
    s.add_argument("--report")
    s.add_argument("--profile", choices=list(PROFILES), default="verify")
    s.set_defaults(fn=cmd_verify_judge)

    s = sub.add_parser("finish-batch", help="批次 digest 计算/比对/落 verdict")
    s.add_argument("--write", action="store_true", help="追加 verdict 行（须 --method）")
    s.add_argument("--method", default="quick")
    s.add_argument("--note", default="")
    s.set_defaults(fn=cmd_finish_batch)

    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
