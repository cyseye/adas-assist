#!/usr/bin/env python3
"""scan-memory.py — 平台 memory 层结构对账扫描（四项，全部机械可断言；语义判断不机器化）。

被 session-review.py import 复用（scan_memory_signals()），也可独立跑：
  python3 scan-memory.py            # 打印 JSON 信号列表
  python3 scan-memory.py --quiet    # 只打计数

memory 目录定位复用 knowledge-recall._user_memory()（importlib 加载防口径漂移）。
召回锚点事实（knowledge-recall._load_memory_index）：锚点 = MEMORY.md 索引行的
title+hook 拼接，散文件 frontmatter 不参与召回——故第四项校验索引行钩子而非
frontmatter（frontmatter description 缺失不影响召回，不扫）。

信号类型统一 memory-structure-drift（low 风险：结构对账类），suggest=memory-governance。
"""
from __future__ import annotations

import importlib.util
import json
import re
import sys
from pathlib import Path

KR_PATH = (Path.home() / ".claude" / "skills" / "skill-evolution"
           / "scripts" / "knowledge-recall.py")
# knowledge-recall 顶部 from shared_state import ...，须先让其目录可解析
sys.path.insert(0, str(KR_PATH.parent))

LINK_RE = re.compile(r"\[\[([a-z0-9][a-z0-9-]*)\]\]")
COUNT_RE = re.compile(r"<!--\s*计数：(\d+)\s*-->")
IDX_LINE_RE = re.compile(r"^- \[([^\]]+)\]\(([^)]+\.md)\)\s+—\s*(.*)$", re.M)


def _load_kr():
    """importlib 加载带连字符文件名的 knowledge-recall（模块级无写盘副作用，安全）。"""
    spec = importlib.util.spec_from_file_location("knowledge_recall", KR_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def scan_memory_signals() -> list[dict]:
    """四项结构对账；无 memory 层（目录/索引不存在）零信号。"""
    kr = _load_kr()
    idx = kr._user_memory()          # 返回 MEMORY.md 文件路径（非目录）
    if not idx.exists():
        return []
    mem = idx.parent
    text = idx.read_text(encoding="utf-8")
    entry_files = {p.stem: p for p in mem.glob("*.md") if p.name != "MEMORY.md"}

    signals: list[dict] = []

    # ① 索引 ↔ 散文件双向对账
    indexed = {Path(m.group(2)).stem for m in IDX_LINE_RE.finditer(text)}
    orphans = sorted(indexed - set(entry_files))       # 孤儿索引行（文件已删）
    missing = sorted(set(entry_files) - indexed)       # 漏索引（新文件未登记）
    if orphans or missing:
        parts = []
        if orphans:
            parts.append(f"孤儿索引行 {len(orphans)}（{', '.join(orphans[:3])}）")
        if missing:
            parts.append(f"漏索引文件 {len(missing)}（{', '.join(missing[:3])}）")
        signals.append({"type": "memory-structure-drift",
                        "edge": "；".join(parts), "suggest": "memory-governance"})

    # ② 悬空 [[链接]]（指向不存在的条目文件）
    dangling: set[str] = set()
    for p in mem.glob("*.md"):
        for name in LINK_RE.findall(p.read_text(encoding="utf-8")):
            if name not in entry_files:
                dangling.add(name)
    if dangling:
        signals.append({"type": "memory-structure-drift",
                        "edge": f"悬空 [[链接]] {len(dangling)} 个"
                                f"（{', '.join(sorted(dangling)[:5])}）",
                        "suggest": "memory-governance"})

    # ③ 计数锚点（MEMORY.md 头注）与实际条目数
    m = COUNT_RE.search(text)
    if m and int(m.group(1)) != len(entry_files):
        signals.append({"type": "memory-structure-drift",
                        "edge": f"计数锚点 {m.group(1)}≠实际散文件 {len(entry_files)}",
                        "suggest": "memory-governance"})

    # ④ 索引行钩子缺失（锚点=title+hook，钩子空则召回锚点减半）
    no_hook = [mm.group(1) for mm in IDX_LINE_RE.finditer(text) if not mm.group(3).strip()]
    if no_hook:
        signals.append({"type": "memory-structure-drift",
                        "edge": f"索引行钩子缺失 {len(no_hook)} 条"
                                f"（{', '.join(no_hook[:3])}）——召回锚点弱化",
                        "suggest": "memory-governance"})
    return signals


def main() -> int:
    quiet = "--quiet" in sys.argv
    signals = scan_memory_signals()
    if quiet:
        print(len(signals))
    else:
        print(json.dumps(signals, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
