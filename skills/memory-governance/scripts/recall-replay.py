#!/usr/bin/env python3
"""recall-replay.py — memory 治理召回回放：治理前后同口径对比，验证召回不衰减。

数据源事实（2026-09-11 勘察）：reflex-hooks.jsonl 的 knowledge-recall 行只记
titles + prompt_len，不存 user_input 原文；invocations.jsonl 无 user_input 字段。
故探针 = 近 30 天非 test- 会话 match 行的 titles 拼接文本——titles 是当时真实
prompt 实际命中的条目标题，作为历史核心命中词证据集回放，与"原始 prompt 回放"
对锚点覆盖度的检验力等价（R0/R1 同口径，公平对比）。

匹配逻辑复用本目录 recall_core.py 的 _tokens/_load_memory_index——防重写口径漂移。口径为 memory-only（不对 KNOWLEDGE 源跑）：
治理验证只关心 memory 层召回能力，隔离 KNOWLEDGE 条目挤占 top3 的干扰。

用法：
  python3 recall-replay.py r0 --memory-root memory --data-root .   # 治理前基线，落 .build/memory-replay-r0.json
  python3 recall-replay.py r1 --memory-root memory --data-root .   # 治理后复测，与 r0 对比输出 delta
"""
from __future__ import annotations

import importlib.util
import argparse
import re
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

def _load_kr(memory_root: Path | None = None):
    """Load the local pure parser; memory_root is retained for existing callers."""
    source = Path(__file__).resolve().with_name("recall_core.py")
    spec = importlib.util.spec_from_file_location("recall_core", source)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _probes(repo: Path, log_path: Path | None = None) -> list[str]:
    """探针集：近 30 天非 test- 会话 knowledge-recall match 行 titles 拼接。"""
    log = log_path or (repo / ".adas-assist" / ".build" / "reflex-hooks.jsonl")
    if not log.exists():
        return []
    cutoff = datetime.now() - timedelta(days=30)
    probes: list[str] = []
    for ln in log.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(ln)
        except json.JSONDecodeError:
            continue
        if row.get("hook") != "knowledge-recall" or row.get("event") != "match":
            continue
        if str(row.get("session_id", "")).startswith("test-"):
            continue
        try:
            if datetime.strptime(str(row.get("ts")), "%Y-%m-%d %H:%M:%S") < cutoff:
                continue
        except ValueError:
            continue
        titles = row.get("titles") or []
        if titles:
            probes.append(" ".join(str(t) for t in titles))
    return probes


def _validate_index_paths(index: Path, root: Path) -> None:
    """Reject index links whose entry or symlink resolves outside explicit memory root."""
    if index.is_symlink():
        raise ValueError("MEMORY.md symlink is not followed in explicit-root mode")
    if not index.is_file():
        return
    boundary = root.resolve()
    for line in index.read_text(encoding="utf-8").splitlines():
        match = re.match(r"- \[([^]]+)\]\(([^)]+)\)", line)
        if match:
            target = (index.parent / match.group(2).strip()).resolve()
            if target != boundary and boundary not in target.parents:
                raise ValueError(f"memory index entry escapes --memory-root: {match.group(2)}")


def _ensure_within_root(path: Path, root: Path, label: str) -> Path:
    """Resolve an explicit-mode read/write target and reject symlink escapes."""
    boundary = root.resolve()
    resolved = path.resolve()
    if resolved != boundary and boundary not in resolved.parents:
        raise ValueError(f"{label} escapes --data-root")
    return resolved


def replay(kr, probes: list[str], entries: list[dict], knowledge: list[dict] | None = None) -> dict:
    """逐探针跑 memory-only 匹配（与 hook 同分同门槛：score=2*|en∩|+2*|zh∩|，≥2 命中）。

    2026-09-29 域分流口径（ADR memory-consolidation-replay-audit-20260929）：
    传入 knowledge 条目时，探针先判域——可命中 KNOWLEDGE 的归 K 域（生产合池由
    KNOWLEDGE 正主接住，不计入 memory 责任域）；memory 域命中率 = memory 域探针
    中被 memory 锚点命中的比例，即 memory 层真实召回质量。
    """
    hit_cnt = 0
    entry_hits: dict[str, int] = {}
    k_domain = m_domain = 0
    m_hit = 0
    for p in probes:
        p_en, p_zh = kr._tokens(p)
        if not p_en and not p_zh:
            continue
        hit_any = False
        for e in entries:
            e_en, e_zh = kr._tokens(e["anchor"])
            if 2 * len(p_en & e_en) + 2 * len(p_zh & e_zh) >= 4:  # 同生产门槛4分（io-governance 2026-09-14；F3 勘误：原 2 系松口径高估）
                hit_any = True
                entry_hits[e["title"]] = entry_hits.get(e["title"], 0) + 1
        in_k = False
        if knowledge and not hit_any:
            in_k = any(
                2 * len(p_en & kr._tokens(k["anchor"])[0]) + 2 * len(p_zh & kr._tokens(k["anchor"])[1]) >= 4
                for k in knowledge)
        if in_k:
            k_domain += 1  # K 域：生产合池由 KNOWLEDGE 正主接住，不计 memory 责任域
        else:
            m_domain += 1  # memory 域（含两域都接不住的真缺口面）
            m_hit += hit_any
            hit_cnt += hit_any
    out = {"probes": len(probes), "probes_hit": hit_cnt,
           "hit_rate": round(hit_cnt / len(probes), 4) if probes else None,
           "entry_hit_dist": entry_hits}
    if knowledge:
        out["domain_split"] = {"memory_domain": m_domain, "memory_hit": m_hit,
                               "k_domain": k_domain,
                               "memory_domain_rate": round(m_hit / m_domain, 4) if m_domain else None}
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("tag", nargs="?", default="r0")
    parser.add_argument("--memory-root", type=Path, required=True, help="fixture/project memory directory or MEMORY.md; avoids host lookup")
    parser.add_argument("--data-root", type=Path, required=True, help="explicit probe/output root (fixture mode only)")
    args = parser.parse_args()
    tag = args.tag
    if args.memory_root is not None and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", tag):
        parser.error("fixture tag must be a single identifier using letters, digits, '_' or '-'")
    kr = _load_kr(args.memory_root)
    if args.memory_root is not None:
        if args.data_root is None:
            parser.error("--data-root is required with --memory-root (use a disposable fixture directory)")
        repo = args.data_root.expanduser().resolve()
        probe_path = _ensure_within_root(
            repo / ".adas-assist" / ".build" / "reflex-hooks.jsonl", repo, "probe log")
        supplied_root = args.memory_root.expanduser()
        root = supplied_root.resolve()
        memory_index = root / "MEMORY.md" if root.is_dir() else supplied_root
        _validate_index_paths(memory_index, memory_index.parent)
        entries = kr._load_memory_index(memory_index)
    probes = _probes(repo, probe_path)
    result = replay(kr, probes, entries, knowledge=[])
    # 证据集：历史 titles ∩ 当前 memory 条目 = 曾被真实 prompt 召回的条目（治理保护名单）
    titles_hist: set[str] = set()
    log = probe_path or (repo / ".adas-assist" / ".build" / "reflex-hooks.jsonl")
    if log.exists():
        cutoff = datetime.now() - timedelta(days=30)
        for ln in log.read_text(encoding="utf-8").splitlines():
            try:
                row = json.loads(ln)
            except json.JSONDecodeError:
                continue
            if (row.get("hook") == "knowledge-recall" and row.get("event") == "match"
                    and not str(row.get("session_id", "")).startswith("test-")):
                try:
                    if datetime.strptime(str(row.get("ts")), "%Y-%m-%d %H:%M:%S") < cutoff:
                        continue
                except ValueError:
                    continue
                titles_hist.update(str(t) for t in row.get("titles") or [])
    cur_titles = {e["title"] for e in entries}
    evidence = sorted(titles_hist & cur_titles)
    result["evidence_titles"] = evidence
    result["entries_total"] = len(entries)

    out = repo / ".adas-assist" / ".build" / f"memory-replay-{tag}.json"
    base_path = out.parent / "memory-replay-r0.json"
    if probe_path is not None:
        out = _ensure_within_root(out, repo, "report output")
        base_path = _ensure_within_root(base_path, repo, "baseline report")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[{tag}] 探针 {result['probes']} 条 / memory 命中 {result['probes_hit']}"
          f"（率 {result['hit_rate']}）；条目 {result['entries_total']} 个；"
          f"证据集（历史命中过的 memory 条目）{len(evidence)} 个 → {out}")

    if tag != "r0":
        if base_path.exists():
            base = json.loads(base_path.read_text(encoding="utf-8"))
            print(f"[delta vs r0] 命中率 {base['hit_rate']} → {result['hit_rate']}；"
                  f"证据集 {len(base['evidence_titles'])} → {len(evidence)}；"
                  f"条目 {base['entries_total']} → {result['entries_total']}")
            lost = [t for t in base["evidence_titles"] if t not in cur_titles]
            if lost:
                print(f"[警告] 证据集条目消失 {len(lost)} 个：{', '.join(lost[:10])}"
                      f"{' …' if len(lost) > 10 else ''}（须核对承接条目锚点已覆盖其关键词）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
