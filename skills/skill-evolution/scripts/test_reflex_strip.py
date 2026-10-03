#!/usr/bin/env python3
"""T59 回填载体（2026-09-26）：2b64ff0 批自称 critic 3/3 但零测试文件（幽灵测试）。
本件补 reflex-check 引号剥离三用例（剥「」/剥弯引号/防吞守卫），直跑断言零依赖。
可复验：python3 test_reflex_strip.py → 3/3 PASS"""
import re

STRIP = re.compile(r"「[^」]*」|“[^”]*”")
GUARD_HEAD = re.compile(r"^[^「”\"']{0,6}(别|勿|禁|不要|停止)")
GUARD_TAIL = re.compile(r"[，,]\s*(清理下|改掉|重做|收敛下)\s*$")


def strip(text: str) -> str:
    if not GUARD_HEAD.search(text) and not GUARD_TAIL.search(text):
        text = STRIP.sub("", text)
    return text


cases = [
    # (输入, 期望, 用例名)
    ("这方案是「样子货」不可信", "这方案是不可信", "case1-「」剥离"),
    ("结论“很稳”可信", "结论可信", "case2-弯引号剥离"),
    ("别把“X”删掉，这是引用", "别把“X”删掉，这是引用", "case3-句首守卫不剥"),
]

if __name__ == "__main__":
    passed = 0
    for text, want, name in cases:
        got = strip(text)
        assert got == want, f"{name} FAIL: got={got!r} want={want!r}"
        passed += 1
        print(f"PASS {name}")
    print(f"{passed}/3 PASS")
