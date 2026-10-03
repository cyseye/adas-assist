#!/usr/bin/env python3
"""P7 红队堵法回归——\\x2f 类转义字面量绕过 secret-scan 解码管道。

背景：红队实测反斜杠 x2f 转义形态的私有 ssh config 路径全模式 MISS（2026-09-22
P7 堵法轮）。堵法：normalized_texts 增 esc 变体——原文含 ≥2 个 `\\xHH`/八进制
`\\NNN` 转义序列时才生成（密度门控防误伤：单处字面转义串如正则文档不触发），
仅解码 \\xHH 与八进制（不碰 \\n/\\t 等控制转义），解码产物入池受 L2 模式
匹配自然过滤（命中回验）。

运行：python3 test_p7_escape.py　（全 PASS exit 0）
"""
import importlib.util
import json
import re
import sys

import pathlib
_ROOT = pathlib.Path(__file__).resolve().parents[3]
SS = str(_ROOT / "skills/_shared/scripts/secret-scan.py")
PAT = str(_ROOT / "skills/_shared/security-patterns.json")

spec = importlib.util.spec_from_file_location("ss_p7", SS)
ss = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ss)

pats = json.load(open(PAT))["patterns"]
comp = [(p["id"], re.compile(p["re"])) for p in pats]


def scan(text: str) -> set:
    """与 G1/G2 双门等价的池匹配（变体池 + 粘连后验 + seg 解码通道）。"""
    hits = set()
    pool = ss.normalized_texts(text)
    for v in pool.values():
        for pid, rx in comp:
            m = rx.search(v)
            if m and pid.startswith("cred-") and ss.is_word_fused(v, m.start()):
                continue
            if m:
                hits.add(pid)
    for vv in {pool.get("clean", ""), text}:
        for _seg, dec in ss.decoded_segments(vv):
            for pid, rx in comp:
                if rx.search(dec):
                    hits.add(pid)
    return hits


# ---- 阳性（应命中）：P7 原型 + 3 变体 ----
# payload 运行时构造（chr(92) 拼接）：本件会入仓并被双门扫描，落盘文本若含
# ≥2 个连续字面转义序列将自绊（esc 变体解码出真私有路径）——同款自指伪装惯例。
_B = chr(92)  # backslash


def _esc(*parts) -> str:
    r"""('x','2f') → 反斜杠x2f；('o','057') → 反斜杠057；(None,'Users') → 字面量。"""
    out = []
    for kind, val in parts:
        out.append(_B + {"x": "x", "o": ""}.get(kind) + val if kind else val)
    return "".join(out)


positives = {
    "p7-lowercase-hex": _esc(("x", "2f"), ("", "Users"), ("x", "2f"), ("", "cc"),
                             ("x", "2f"), ("", ".ssh"), ("x", "2f"), ("", "config")),
    "p7b-uppercase-hex": _esc(("x", "2F"), ("", "Users"), ("x", "2F"), ("", "Cc"),
                              ("x", "2F"), ("", ".ssh"), ("x", "2F"), ("", "config")),
    "p7c-octal": _esc(("o", "057"), ("", "Users"), ("o", "057"), ("", "cc"),
                      ("o", "057"), ("", ".ssh"), ("o", "057"), ("", "config")),
    "p7d-mixed-plain": _esc(("x", "2f"), ("", "Users"), ("x", "2f"), ("", "cc")) + "/.ssh/id_rsa",
}

# ---- 阴性（不得误伤）：单处/普通字面转义串 ----
legit = {
    "doc-regex-single-esc": r"match path with \x2f separator in regex docs",
    "doc-regex-nonpath": r"use \x41\x42 for literal AB demo",
    "log-literal-escape": "json dump shows \\x2f inside one field only",
}

failures = []
print("=== P7 阳性对照：应命中 ===")
for name, q in positives.items():
    hits = scan(q)
    ok = bool(hits)
    print(f"{name}: {'HIT ' + ','.join(sorted(hits)) if ok else '!! MISS (hole open)'}")
    if not ok:
        failures.append(name)

print("\n=== 误伤防线阴性：字面转义串应放行 ===")
for name, q in legit.items():
    hits = scan(q)
    ok = not hits
    print(f"{name}: {'PASS' if ok else '!! FALSE-POSITIVE ' + repr(sorted(hits))}")
    if not ok:
        failures.append(name)

print(f"\nSUMMARY: {'ALL PASS' if not failures else 'FAIL: ' + repr(failures)}")
sys.exit(0 if not failures else 1)
