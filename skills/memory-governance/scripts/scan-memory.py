#!/usr/bin/env python3
"""scan-memory.py — 平台 memory 层结构对账扫描（四项，全部机械可断言；语义判断不机器化）。

显式指定本仓或授权目录：
  python3 scan-memory.py --memory-root memory
  python3 scan-memory.py --memory-root memory --quiet

召回锚点由 MEMORY.md 索引行的
title+hook 与正文 frontmatter trigger 组成。本扫描器校验索引钩子，不把
frontmatter description 缺失当作召回错误。显式目标缺索引报告结构信号。

信号类型统一 memory-structure-drift（low 风险：结构对账类），suggest=memory-governance。
"""
from __future__ import annotations

import importlib.util
import json
import argparse
import re
import sys
from pathlib import Path

LINK_RE = re.compile(r"\[\[([a-z0-9][a-z0-9-]*)\]\]")
COUNT_RE = re.compile(r"<!--\s*计数：(\d+)\s*-->")
IDX_LINE_RE = re.compile(r"^- \[([^\]]+)\]\(([^)]+\.md)\)[ \t]+—[ \t]*(.*)$", re.M)


def _scan_index(idx: Path, *, require_index: bool = False) -> list[dict]:
    """Scan an explicitly supplied MEMORY.md without loading host configuration."""
    if idx.is_symlink():
        raise ValueError("MEMORY.md symlink is not followed in explicit-root mode")
    if not idx.is_file():
        if require_index:
            return [{"type": "memory-structure-drift", "edge": f"缺少记忆索引：{idx}",
                     "suggest": "memory-governance"}]
        return []
    mem = idx.parent
    text = idx.read_text(encoding="utf-8")
    entry_files = {p.stem: p for p in mem.glob("*.md")
                   if p.name != "MEMORY.md" and not p.is_symlink()}
    signals: list[dict] = []
    invalid_paths = []
    for match in (IDX_LINE_RE.finditer(text) if require_index else ()):
        target = Path(match.group(2))
        resolved = (mem / target).resolve()
        if target.is_absolute() or resolved.parent != mem.resolve() or (mem / target).is_symlink():
            invalid_paths.append(match.group(2))
    if invalid_paths:
        signals.append({"type": "memory-structure-drift",
                        "edge": f"索引指向超出本层正文范围：{', '.join(invalid_paths[:3])}",
                        "suggest": "memory-governance"})
    indexed = {Path(m.group(2)).stem for m in IDX_LINE_RE.finditer(text)}
    orphans, missing = sorted(indexed - set(entry_files)), sorted(set(entry_files) - indexed)
    if orphans or missing:
        parts = []
        if orphans: parts.append(f"孤儿索引行 {len(orphans)}（{', '.join(orphans[:3])}）")
        if missing: parts.append(f"漏索引文件 {len(missing)}（{', '.join(missing[:3])}）")
        signals.append({"type": "memory-structure-drift", "edge": "；".join(parts), "suggest": "memory-governance"})
    dangling = set()
    for p in mem.glob("*.md"):
        if p.is_symlink():
            continue
        dangling.update(name for name in LINK_RE.findall(p.read_text(encoding="utf-8")) if name not in entry_files)
    if dangling:
        signals.append({"type": "memory-structure-drift", "edge": f"悬空 [[链接]] {len(dangling)} 个（{', '.join(sorted(dangling)[:5])}）", "suggest": "memory-governance"})
    m = COUNT_RE.search(text)
    if m and int(m.group(1)) != len(entry_files):
        signals.append({"type": "memory-structure-drift", "edge": f"计数锚点 {m.group(1)}≠实际散文件 {len(entry_files)}", "suggest": "memory-governance"})
    no_hook = [mm.group(1) for mm in IDX_LINE_RE.finditer(text) if not mm.group(3).strip()]
    if no_hook:
        signals.append({"type": "memory-structure-drift", "edge": f"索引行钩子缺失 {len(no_hook)} 条（{', '.join(no_hook[:3])}）——召回锚点弱化", "suggest": "memory-governance"})
    return signals


def scan_memory_signals(memory_root: Path | None = None) -> list[dict]:
    """显式目标缺索引报信号；未提供目标时拒绝。"""
    if memory_root is not None:
        root = memory_root.expanduser().resolve()
        idx = root / "MEMORY.md" if root.is_dir() else memory_root.expanduser()
        return _scan_index(idx, require_index=True)
    raise ValueError("--memory-root is required")

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--memory-root", type=Path, required=True, help="fixture/project memory directory or MEMORY.md; avoids host lookup")
    args = parser.parse_args()
    signals = scan_memory_signals(args.memory_root)
    if args.quiet:
        print(len(signals))
    else:
        print(json.dumps(signals, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
