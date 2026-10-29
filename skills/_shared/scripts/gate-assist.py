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
  finish-batch  批次 digest（本次文件变化的porcelain 代码类
                改动整行含 XY 前缀、剔 .adas-assist/ 豁免、sorted join sha256 前 8 位）；
                --write 落 verdict 行，--check 与末条比对（校验批未漂移）

各消费 SKILL.md 引用本脚本时写「调 gate-assist.py <子命令>」，不再内联手工步骤。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# 批次摘要只覆盖列出的代码后缀与当前项目变更。
CODE_SUFFIXES = {".java", ".ts", ".tsx", ".js", ".jsx", ".xml", ".sql", ".py", ".yaml",
                 ".yml", ".json", ".css", ".scss", ".html", ".sh", ".vue"}
EXEMPT_PREFIX = ".adas-assist/"

# 严重性词表两套（review-gate-skeleton §合法特化登记；改扣分值两处同改）
PROFILES = {
    "base": {"BLOCKER": 40, "MAJOR": 10, "MINOR": 3},
    "verify": {"P0": 25, "P1": 8},
}


def data_root() -> Path:
    """运行数据根必须由调用者显式提供。"""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from shared_state import data_root as resolve
    return resolve()


def validate_data_path(path: Path) -> Path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from shared_state import validate_data_path as validate
    return validate(path)


def build_dir(slug: str) -> Path:
    if not isinstance(slug, str) or not slug or slug in {".", ".."} or Path(slug).name != slug or "/" in slug or "\\" in slug:
        raise ValueError("slug 必须是非空单段名称")
    return validate_data_path(data_root() / ".build" / slug)


def _git_porcelain_code_lines(repo: Path) -> list[str]:
    """本批取数：porcelain 整行、rename 取新路径、剔豁免前缀、
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
    path = validate_data_path(build_dir(args.slug) / f"pcf.{args.role}.md")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"[pcf-save] 已落盘：{path}（{len(content)} 字符）")
    return 0


def cmd_pcf_context(args) -> int:
    d = build_dir(args.slug)
    products = [validate_data_path(p) for p in sorted(d.glob("pcf.*.md"))] if d.is_dir() else []
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
    try:
        data = json.loads(sys.stdin.read() if not args.report else Path(args.report).read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("输入必须是 JSON object")
        if args.tier == "quick":
            raise ValueError("quick 档不走计分 verify-judge；按 SKILL.md quick 简化判定处理")
        if data.get("tier", args.tier) != args.tier:
            raise ValueError("输入 tier 与 --tier 不一致")
        round_no = data.get("round", 1)
        if type(round_no) is not int or round_no < 1:
            raise ValueError("round 必须是正整数")
        cfg = {"pass": 90, "critical": 60, "converge": 5,
               "max_rounds": 3 if args.tier == "standard" else 5}
        thresholds = data.get("thresholds", {})
        if not isinstance(thresholds, dict):
            raise ValueError("thresholds 必须是 object")
        for key, value in thresholds.items():
            if key not in cfg or type(value) not in (int, float) or not math.isfinite(value):
                raise ValueError(f"非法 threshold: {key}")
            if value != cfg[key]:
                raise ValueError(f"threshold {key} 与 {args.tier} 契约值 {cfg[key]} 不一致")
        prev_scores = data.get("prev_scores", [])
        if not isinstance(prev_scores, list) or any(type(v) not in (int, float) or not math.isfinite(v) for v in prev_scores):
            raise ValueError("prev_scores 必须是有限数值数组")
        must_fix = data.get("must_fix", [])
        if not isinstance(must_fix, list):
            raise ValueError("must_fix 必须是数组")
        dimensions = data.get("dimensions")
        if not isinstance(dimensions, list) or not dimensions:
            raise ValueError("dimensions 必须是非空数组")
        if args.profile == "verify":
            required = {"正确性", "安全性", "规范性", "完整性"}
            names = {d.get("name") for d in dimensions if isinstance(d, dict)}
            if names != required or len(dimensions) != 4:
                raise ValueError("verify profile 必须且只能包含四个协议维度")
        scores, total, weight_sum = {}, 0.0, 0.0
        floor_breaches, detected_must_fix = [], []
        for dim in dimensions:
            if not isinstance(dim, dict) or not isinstance(dim.get("name"), str) or not dim["name"].strip():
                raise ValueError("每个 dimension 都必须有非空 name")
            name = dim["name"]
            if name in scores:
                raise ValueError(f"重复维度: {name}")
            weight, floor = dim.get("weight"), dim.get("floor")
            if type(weight) not in (int, float) or not math.isfinite(weight) or weight <= 0:
                raise ValueError(f"维度 {name} 的 weight 必须是正有限数")
            if type(floor) not in (int, float) or not math.isfinite(floor) or not 0 <= floor <= 100:
                raise ValueError(f"维度 {name} 的 floor 必须是 0 到 100 的有限数")
            if args.profile == "verify" and floor != 80:
                raise ValueError(f"verify profile 维度 {name} 的 floor 必须为协议值 80")
            issues = dim.get("issues")
            if not isinstance(issues, list):
                raise ValueError(f"维度 {name} 的 issues 必须是数组")
            deductions = 0
            for issue in issues:
                if not isinstance(issue, dict) or issue.get("severity") not in PROFILES[args.profile]:
                    raise ValueError(f"维度 {name} issue severity 缺失或不属于 {args.profile} 词表")
                severity = issue["severity"]
                deductions += PROFILES[args.profile][severity]
                if args.profile == "verify" and name == "安全性" and severity == "P0":
                    detected_must_fix.append(issue)
            score = max(0, 100 - deductions)
            scores[name] = score
            total += score * weight
            weight_sum += weight
            if score < floor:
                floor_breaches.append(name)
        if args.profile == "verify" and abs(weight_sum - 1.0) > 1e-9:
            raise ValueError("verify profile 权重总和必须为 1")
        total = round(total / weight_sum, 1)
        must_fix.extend(detected_must_fix)
    except (OSError, json.JSONDecodeError, ValueError, TypeError, OverflowError) as exc:
        print(f"[verify-judge] 输入无效：{exc}", file=sys.stderr)
        return 2

    constraints = []
    if must_fix:
        constraints.append(f"must_fix={len(must_fix)}")
    if floor_breaches:
        constraints.append(f"floor_breaches={','.join(floor_breaches)}")
    if not must_fix and not floor_breaches and total >= cfg["pass"]:
        verdict, reason = "PASS", f"总分 {total} ≥ 通过线 {cfg['pass']}"
    elif args.profile == "verify" and args.tier == "full" and round_no == 1 and total < cfg["critical"]:
        verdict, reason = "PCF", f"首轮 {total} < 临界线 {cfg['critical']}"
    elif len(prev_scores) >= 1 and abs(total - prev_scores[-1]) < cfg["converge"]:
        verdict, reason = "PCF", f"plateau：与上轮分差 {abs(total - prev_scores[-1])} < {cfg['converge']}"
    elif round_no >= cfg["max_rounds"]:
        verdict, reason = "PCF", f"终轮未通过（round {round_no} ≥ {cfg['max_rounds']}）"
    elif must_fix:
        verdict, reason = "FIXABLE", f"must_fix={len(must_fix)}（一票否决）"
    elif floor_breaches:
        verdict, reason = "FIXABLE", f"维度底线未达：{'、'.join(floor_breaches)}"
    else:
        verdict, reason = "FIXABLE", f"总分 {total} 未达通过线，可修复进下一轮"
    result = {"verdict": verdict, "reason": reason, "total": total,
              "dimension_scores": scores, "floor_breaches": floor_breaches}
    if verdict == "PCF":
        result["constraints"] = constraints
        result["must_fix_count"] = len(must_fix)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_finish_batch(args) -> int:
    repo = Path.cwd()
    lines = _git_porcelain_code_lines(repo)
    digest = hashlib.sha256("\n".join(sorted(lines)).encode()).hexdigest()[:16][:8]
    verdicts = validate_data_path(data_root() / ".state" / "finish-verdicts.jsonl")
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
    s.add_argument("--tier", choices=["quick", "standard", "full"], default="standard")
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
