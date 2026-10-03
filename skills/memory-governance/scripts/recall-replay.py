#!/usr/bin/env python3
"""recall-replay.py — memory 治理召回回放：治理前后同口径对比，验证召回不衰减。

数据源事实（2026-09-11 勘察）：reflex-hooks.jsonl 的 knowledge-recall 行只记
titles + prompt_len，不存 user_input 原文；invocations.jsonl 无 user_input 字段。
故探针 = 近 30 天非 test- 会话 match 行的 titles 拼接文本——titles 是当时真实
prompt 实际命中的条目标题，作为历史核心命中词证据集回放，与"原始 prompt 回放"
对锚点覆盖度的检验力等价（R0/R1 同口径，公平对比）。

匹配逻辑 import knowledge-recall 的 _tokens/_load_memory_index（文件名带连字符
须 importlib 加载）——防重写口径漂移。口径为 memory-only（不对 KNOWLEDGE 源跑）：
治理验证只关心 memory 层召回能力，隔离 KNOWLEDGE 条目挤占 top3 的干扰。

用法：
  python3 recall-replay.py r0   # 治理前基线，落 .build/memory-replay-r0.json
  python3 recall-replay.py r1   # 治理后复测，与 r0 对比输出 delta
"""
from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

KR_PATH = (Path.home() / ".claude" / "skills" / "skill-evolution"
           / "scripts" / "knowledge-recall.py")
# knowledge-recall 顶部 from shared_state import ...，须先让其目录可解析
sys.path.insert(0, str(KR_PATH.parent))


def _load_kr():
    """importlib 加载带连字符文件名的 knowledge-recall（模块级无写盘副作用，安全）。"""
    spec = importlib.util.spec_from_file_location("knowledge_recall", KR_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _probes(repo: Path) -> list[str]:
    """探针集：近 30 天非 test- 会话 knowledge-recall match 行 titles 拼接。"""
    log = repo / ".claude" / ".build" / "reflex-hooks.jsonl"
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
    tag = sys.argv[1] if len(sys.argv) > 1 else "r0"
    kr = _load_kr()
    repo = kr.REPO
    entries = kr._load_memory_index(kr._user_memory())
    probes = _probes(repo)
    result = replay(kr, probes, entries, knowledge=kr._load_knowledge())
    # 证据集：历史 titles ∩ 当前 memory 条目 = 曾被真实 prompt 召回的条目（治理保护名单）
    titles_hist: set[str] = set()
    log = repo / ".claude" / ".build" / "reflex-hooks.jsonl"
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

    out = repo / ".claude" / ".build" / f"memory-replay-{tag}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[{tag}] 探针 {result['probes']} 条 / memory 命中 {result['probes_hit']}"
          f"（率 {result['hit_rate']}）；条目 {result['entries_total']} 个；"
          f"证据集（历史命中过的 memory 条目）{len(evidence)} 个 → {out}")

    if tag != "r0":
        base_path = out.parent / "memory-replay-r0.json"
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
