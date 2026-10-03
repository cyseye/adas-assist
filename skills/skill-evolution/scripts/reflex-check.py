#!/usr/bin/env python3
"""reflex-check.py — Stop 钩子：收尾三检查（代码改动无验证 + 澄清未沉淀 + 纠正信号反复），合并一次 block。

技能自动触发反射层：收尾验证（finish-check）/ decision-record 等收尾能力此前只靠用户喊触发词。
本脚本在会话每轮停止时做三个检查，任一命中则合并 reason 拦一次（合并而非独立
hook：Claude Code 对同事件多 hook block 会逐一生效，独立脚本导致连环拦多次）：
  检查1 代码收尾：工作区有代码类改动且该批未提醒过 → 提议主控做交付前检查（decision-verify quick 档）
  检查2 澄清沉淀：transcript 用过 AskUserQuestion 且本会话未提醒过 → 按 CLAUDE.md
  「记录澄清内容」补录。沉淀去向多样（KNOWLEDGE/PRD/TECH），故不做文件级「已沉淀」
  检测——只盯 KNOWLEDGE mtime 会漏豁免沉淀到 PRD 的场景，价值判断交主控。
  检查3 三档纠偏判定：同类纠正措辞 1 次轻（仅计数）/ 2 次中（观察提醒沉淀）/
  3 次或显式拒绝重（提醒提炼 Lesson + Evolution Record 落盘本地候选池）——螺旋
  闭环纠偏节点落地（0017），治「知道≠做到」：召回注入了但主控仍重犯。
防打扰：会话级去重（各检查独立 hash/标记）+ 检查1 跨会话窗口去重（同批次 TTL 内多会话只提醒一次）+ 宿主连续 block 保护 + 状态文件 disabled:true 一键关。
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# 共享状态读写唯一通道：写者分区——本脚本只写 stop-state（disabled/sessions/
# global_hashes），session-start 只写 start-state；flock 兜底多 session 同写者并发。
# 本脚本全部读写都是运行时数据（.build/.state/git status），一律项目根（cwd 上溯）。
from shared_state import (asset_claude, atomic_write, data_claude, flock_ctx,
                          jsonl_tail, load_partition)

ASSET = asset_claude()  # 元层资产根（2026-09-21 心跳轮⑪：git 根回落用，见 _changed_code_entries）


REPO = data_claude().parent
STATE_STOP = REPO / ".claude" / ".build" / "reflex-stop-state.json"  # **/.build/ 已 gitignore
# 跨会话窗口去重 TTL：同工作区多会话并发 Stop 时，同一批次 TTL 内只提醒一次
# （会话级去重按 session_id 隔离，多会话各自 block 同一批改动——周评估实证
# 56% block 为跨会话重复，是打扰度超标主源）。6h 覆盖同日并发窗口，隔天新会话仍提醒
GLOBAL_TTL = 6 * 3600
# 收尾验证标记（finish-check 完成/等效验证声明后 append；本脚本只读消费，单向依赖）
VERDICTS = REPO / ".claude" / ".state" / "finish-verdicts.jsonl"  # 运行时状态域（.build 会被按中间产物清理，实证丢失）


def _batch_verified(digest: str) -> bool:
    """该批次是否已有收尾验证标记（quick/standard/full 检查完成或 real-run 等效验证）。"""
    try:
        for item in jsonl_tail(VERDICTS, 50):
            # 坏尾半行（追加进程崩溃残留）由 jsonl_tail 跳过，此处不会再遇解析失败
            if isinstance(item, dict) and digest[:8] in str(item.get("batch", "")):
                return True
    except Exception:
        return False
    return False
# 只对代码类改动提醒：文档/笔记改动不涉运行行为，无需交付前验证门。
# 含 .json/.html/.css 等 web 栈配置类：魔鬼测试实证本仓 .json 改动（package.json/
# tsconfig 类）曾被整套漏检——配置文件同样影响运行行为
CODE_SUFFIXES = {".java", ".ts", ".tsx", ".js", ".jsx", ".xml", ".sql", ".py", ".yaml",
                 ".yml", ".vue", ".json", ".html", ".css", ".scss", ".less", ".sh",
                 ".cjs", ".mjs"}
# .claude/ 元层域豁免（周评估实证打扰度 19.7%>15% 线，skill/hook 治理会话是 block
# 主源之一，用户 2026-08-28 裁决）：元层改动有独立验证纪律（py_compile/干跑走查/
# git diff 核验+周评估），收尾检查门对其是重复打扰；业务代码（还原产物 .tsx 等）不受影响
EXEMPT_PREFIXES = (".claude/",)


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _append_log(entry: dict) -> None:
    """运行数据采集：block 与 silent（去重生效）都记，打扰度分母=有触发条件的停止。
    写侧先过 rotate_jsonl（T116：双写者同闸，阈值单源 io-budgets.evolution_cadence
    .reflex_hooks_rotate_*；单改 knowledge-recall 侧会漏本写者）。"""
    try:
        from shared_state import rotate_jsonl
        rotate_jsonl(REPO / ".claude" / ".build" / "reflex-hooks.jsonl", "reflex_hooks")
        path = REPO / ".claude" / ".build" / "reflex-hooks.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:  # noqa: BLE001 — 日志失败不影响 hook 主流程
        pass


def _changed_code_entries() -> list[str]:
    """git status 中代码类改动行（rename 取新路径）；无 git/无改动返回空。
    git 根独立解析（2026-09-21 心跳轮⑪活体实证）：REPO 在资产仓 cwd 下解析为
    家目录（REPO/.claude 数据路径语义正确），但 git -C 家目录 rc=128 → 检查1
    在元层仓从未触发、reflex-check 恒零落行——元层 git 操作根须回落资产仓本身。
    资产仓内全部改动属元层域：按 2026-08-28 用户豁免裁决全量豁免收尾门，代码类
    留 exempt-skip 审计痕（替代原「git 失败静默零行」——非设计豁免是断链）。"""
    out = None
    asset_git = False
    for root in (REPO, ASSET):
        try:
            r = subprocess.run(
                ["git", "-C", str(root), "status", "--porcelain"],
                capture_output=True, text=True, timeout=10,
            )
        except Exception:
            continue
        if r.returncode == 0:
            out = r.stdout
            asset_git = root == ASSET and root != REPO
            break
    if out is None:
        return []
    entries: list[str] = []
    for ln in out.splitlines():
        path = ln[3:].strip().split("->")[-1].strip().strip('"')
        if path.startswith(EXEMPT_PREFIXES):
            # 豁免留审计痕：零打扰但可回溯，周评估消费——≥2 次真实漏检再议收窄豁免
            _append_log({"ts": _now(), "hook": "reflex-check",
                         "event": "exempt-skip", "path": path})
            continue
        if asset_git:
            # 资产仓=元层域全量豁免（同上裁决）；仅代码类留痕防 .md 全量噪声
            if Path(path).suffix.lower() in CODE_SUFFIXES:
                _append_log({"ts": _now(), "hook": "reflex-check",
                             "event": "exempt-skip", "path": path})
            continue
        if Path(path).suffix.lower() in CODE_SUFFIXES:
            # 保留前导 XY 状态列（与 finish-check batch 口径一致）：strip 会把
            # 仅工作区改动行（X=空格）的 batch 算错，导致该类批次提醒永不命中
            entries.append(ln.rstrip())
    return entries


def _check_code(entry: dict, global_hashes: dict) -> tuple[str, str] | None:
    """检查1：代码类改动无收尾验证。返回 (reason, digest) 或 None；去重标记写入 entry 与 global_hashes。

    digest 一并返回供调用方锁内复查：锁外判定基于可能陈旧的状态快照，重叠窗口
    判定须在锁内对最新真值二次确认。

    hash 只算改动集合（不含内容）：提交后 status 清空静默；新一批改动新 hash 重新提醒；
    同文件内容再变 hash 不变。去重两层：
    - 会话级（code_hashes）：每会话首批未验证改动提醒一次；
    - 跨会话窗口（global_hashes 带时间戳）：同批次 TTL 内已被其他会话提醒过则静默，
      多会话并发同一工作区时只打扰一次（按 session_id 隔离的会话级去重是设计盲区，
      周评估实证 56% block 为跨会话重复）。
    验证标记联动：finish-check（或主控等效验证声明）完成后会向 VERDICTS append
    {batch, method}；命中同 batch → 该批已收尾，静默不提醒（消除路径闭环；验证声明由主控直接写入 VERDICTS）。
    """
    changed = _changed_code_entries()
    if not changed:
        return None
    digest = hashlib.sha256("\n".join(sorted(changed)).encode()).hexdigest()[:16]
    if _batch_verified(digest):
        _append_log({"ts": _now(), "hook": "reflex-check", "event": "silent-verified",
                     "hash": digest[:8]})
        return None
    hashes = entry.setdefault("code_hashes", [])
    if digest in hashes:
        _append_log({"ts": _now(), "hook": "reflex-check", "event": "silent",
                     "changed_files": len(changed), "hash": digest[:8]})
        return None
    last_ts = global_hashes.get(digest)
    if last_ts is not None and time.time() - last_ts < GLOBAL_TTL:
        _append_log({"ts": _now(), "hook": "reflex-check", "event": "silent",
                     "changed_files": len(changed), "hash": digest[:8]})
        return None
    hashes.append(digest)
    del hashes[:-50]
    global_hashes[digest] = time.time()
    _append_log({"ts": _now(), "hook": "reflex-check", "event": "block",
                 "changed_files": len(changed), "hash": digest[:8]})
    return (f"工作区有 {len(changed)} 处代码类改动（批次 {digest[:8]}）尚无收尾验证记录，"
            "是否做交付前检查（decision-verify quick 档或主控等效验证声明）？不需要则直接结束即可，本会话本批不会重复提醒。",
            digest)


def _check_clarify(session_id: str, entry: dict, transcript_path: str | None) -> str | None:
    """检查2：澄清未沉淀提醒。行级子串检测而非 JSON 解析——transcript 的工具调用
    嵌在 message.content[] 内（顶层无 type=tool_use 字段），假设嵌套格式的解析会漏检。
    """
    if not transcript_path:
        return None
    digest = hashlib.sha256(f"{session_id}:{Path(transcript_path).name}".encode()).hexdigest()[:16]
    hashes = entry.setdefault("clarify_hashes", [])
    if digest in hashes:
        # 回访 M2：resolved 只在「block 之后有新 ADR」时补发一次——同刻全局 ADR 活跃
        # 会把转化率虚高到恒 100%（假达标比假 ⚠ 更隐蔽）。clarify_ts 由 block 分支落盘。
        block_ts = entry.get("clarify_ts")
        # clarify_ts 是 "%Y-%m-%d %H:%M:%S" 字符串，float() 直接转换必抛 ValueError
        # （2026-09-17 实证：两个 block 会话均因此 resolved 永不落盘，转化率假恒 0）
        if block_ts and not entry.get("clarify_resolved"):
            try:
                since = datetime.strptime(block_ts, "%Y-%m-%d %H:%M:%S").timestamp()
            except ValueError:
                since = None
            if _recent_adr_exists(since=since):
                entry["clarify_resolved"] = True
                _append_log({"ts": _now(), "hook": "reflex-clarify", "event": "resolved",
                             "transcript": Path(transcript_path).name})
        _append_log({"ts": _now(), "hook": "reflex-clarify", "event": "silent",
                     "transcript": Path(transcript_path).name})
        return None
    asked = False
    try:
        with open(transcript_path, encoding="utf-8") as fh:  # 流式逐行，不整文件载入
            for line in fh:
                if "AskUserQuestion" in line and "tool_use" in line:
                    asked = True
                    break
    except Exception as _e:  # 留痕批：永久读空将使反例检测空转无痕（B2-6）
        print(f"[reflex-check] transcript 读取失败，跳过：{_e}", file=sys.stderr)
        return None
    if not asked:
        return None
    hashes.append(digest)
    del hashes[:-50]
    entry["clarify_ts"] = _now()  # 回访 M2：记录 block 时刻，后续 Stop 检「此后新增 ADR」才发 resolved
    _append_log({"ts": _now(), "hook": "reflex-clarify", "event": "block",
                 "transcript": Path(transcript_path).name})
    return ("本会话使用过 AskUserQuestion 做需求澄清。若澄清结论尚未记录到合适文档"
            "（可触发 decision-record 沉淀，或直接更新对应 PRD/TECH），请按 CLAUDE.md"
            "「记录澄清内容」规则补录；已记录或属无需沉淀的小确认则直接结束即可，本会话不会重复提醒。")


def _recent_adr_exists(days: int = 7, since: float | None = None) -> bool:
    """是否有新建/变更 ADR（元层 meta/data + 当前项目仓 decisions/adr）。
    since 给定时只认该时刻之后的 ADR（回访 M2：保证 resolved 与澄清有因果序）；否则按 days 窗口。"""
    import time
    cutoff = since if since is not None else time.time() - days * 86400
    roots = [Path(__file__).resolve().parents[3] / "decisions" / "adr",  # 元层 asset 根
             REPO / ".claude" / "decisions" / "adr"]
    for root in roots:
        if not root.is_dir():
            continue
        for f in root.rglob("*.md"):
            try:
                if f.stat().st_mtime > cutoff:
                    return True
            except OSError:
                continue
    return False


# 纠正信号词典：用户否定/修正类措辞，7 词均经本仓真实触发实证（reflex-hooks.jsonl
# 首次运行全命中）。三档量化：1 次轻（仅计数）、2 次中（观察提醒）、3 次重（提炼）
# 单次纠正属正常交互，逐次提醒打扰爆炸——只有达档才升级动作
_CORRECTION_MARKERS = ("不要", "别再", "次次重来", "太傻", "冗余", "清理下", "精简")
# 显式拒绝词：撤销/重生成类动作，单独命中即判重度（等价 diff>30% 档的强信号代理）
_REJECT_MARKERS = ("重新生成", "撤销", "重写")
# 否定祈使排除（2026-09-24 实证误报）：「不准停止」「不要停」是催促继续，不是纠正
# ——否定词（不要/不准/别）直接接停止类动词时整行不计纠正信号，防语义反转误判
_NEG_IMPERATIVE_RE = re.compile(r"(不要|不准|别再?|不得)(停止|停下|停下?来|停|动|中断|结束|退出)")
# 训练轨候选池：本地落盘不入库（.state 已 gitignore），仅积累待离线处理
EVOLUTION_POOL = REPO / ".claude" / ".state" / "evolution-pool"


def _append_evolution_record(counts: dict[str, int], rejected: bool) -> None:
    """重度纠偏时落盘 Evolution Record（0017 schema 骨架版）。

    候选池只落盘不训练；context 已收窄为 source+context_summary（2026-08-19 删
    恒 null 假字段）——source 标来源，context_summary 由主控消化信号时对照
    transcript 回填一句话；skill_updated=false——改 skill
    须用户确认，由主控沉淀后回填。event_id 取 counts 字典的确定性 hash，同组合
    不会因多次 Stop 重复落盘。
    """
    try:
        record = {
            "event_id": "evt_" + hashlib.sha256(
                json.dumps(counts, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:12],
            "timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
            "context": {"source": "session", "context_summary": None},
            "hooks_signal": {"diff_ratio": None, "turns": sum(counts.values()),
                             "explicit_reject": rejected,
                             "edit_type": "correction_marker"},
            "evolution_action": {"level": "heavy_correction", "lesson": None,
                                 "next_skill_version": None, "status": "pending_validation"},
            "data_routing": {"skill_updated": False, "training_dataset": "DPO"},
        }
        path = EVOLUTION_POOL / "evolution-records.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        # 写侧幂等（T72 修复，2026-09-28）：docstring 契约即「同组合同 id 不重复
        # 落盘」，实测 56 行/18 唯一 id 系检查缺失回归——append 前同 id 拦截（历史重复行
        # 留存不洗，append-only 台账纪律）
        if path.exists():
            with path.open(encoding="utf-8") as fh:
                for ln in fh:
                    try:
                        if json.loads(ln).get("event_id") == record["event_id"]:
                            return
                    except json.JSONDecodeError:
                        continue
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:  # noqa: BLE001 — 候选池落盘失败不影响 hook 主流程
        pass


def _correction_recurrence(markers: list[str]) -> int:
    """纠正回写闭环检查（零模型，纯机械）：统计 corrections 单源候选池中已有多少条
    同主题条目（记录表行 `| Cxx |` 内含任一主题词）。已有条目=该纠正此前已沉淀过
    却仍复发（跨会话实证：探索力度类纠正 4 次复发）——提示主控确认是否回写单源画像。
    文件不存在/读取失败返回 0，不影响主流程。"""
    total = 0
    cdir = REPO / ".claude" / ".state" / "corrections"
    try:
        for f in cdir.glob("*.md"):
            try:
                text = f.read_text(encoding="utf-8")
            except Exception:
                continue
            for ln in text.splitlines():
                s = ln.strip()
                if s.startswith("| C") and any(m in s for m in markers):
                    total += 1
    except Exception:  # noqa: BLE001 — 闭环检查失败不阻断 hook
        return 0
    return total


def _loop_closure_note(markers: list[str]) -> str:
    """复发升级文案：corrections 池已有同主题条目（第二次+）→ 追加回写闭环提醒。"""
    n = _correction_recurrence(markers)
    if n <= 0:
        return ""
    return (f"⚠闭环检查：该纠正主题在 corrections 落盘物中已有 {n} 条既有条目"
            f"（本次为第 {n + 1} 次复发）——请确认是否已回写单源画像（memory/registry/条款），"
            "未回写即视为未闭环。")


def _check_correction(entry: dict, transcript_path: str | None) -> str | None:
    """检查3：三档量化纠偏判定（螺旋闭环纠偏节点，0017 落地）。

    轻=1 次（仅计数记 silent 日志，Skill 不变）；中=2 次（观察提醒沉淀建议）；
    重=3 次或显式拒绝（提醒提炼 Lesson + Evolution Record 落盘候选池）。
    行级子串检测沿用 _check_clarify 哲学（不假设 transcript 嵌套格式）；
    同类提醒一次后去重（reminded 列表），避免逐轮重复打扰。
    """
    if not transcript_path:
        return None
    # transcript 全量重扫（append-only），本轮计数覆盖写——累加会把用户仅说 1 次
    # 的纠正在第 2 轮 Stop 重复计入达 2 次而提前误触发（构造场景实测暴露）
    counts: dict[str, int] = {}
    rejected = False
    reject_src = ""
    try:
        with open(transcript_path, encoding="utf-8") as fh:  # 流式逐行
            for line in fh:
                if '"role":"user"' not in line and '"role": "user"' not in line:
                    continue
                # 只认用户真实表达：content 为数组的是工具结果回传（含脚本输出/
                # 命令描述），"Stop hook feedback" 是反射层自身注入——两者被计入
                # 会形成自激循环（hook 文案含词典词 → 下轮计数 +1 → 更易触发）
                if '"content":[' in line or "Stop hook feedback" in line:
                    continue
                # 否定祈使排除：「不准停止/不要停」= 催促继续，语义与纠正相反
                if _NEG_IMPERATIVE_RE.search(line):
                    continue
                # sys-02 降噪（2026-09-25 运行时对标批）：剥代码围栏与引用行后再匹配——
                # 用户粘贴代码/引用他人话术里的词典词非用户本意（实测「不要」215 次
                # 命中撑大分母，light 档 338/350 全被噪音淹没）。行解析失败回退原文，
                # 与「不假设嵌套格式」哲学一致
                text = line
                try:
                    obj = json.loads(line)
                    msg = obj.get("message") or obj
                    c = msg.get("content")
                    if isinstance(c, str):
                        text = c
                except Exception:
                    pass
                text = _strip_code_fences(text)
                text = "\n".join(ln for ln in text.splitlines()
                                 if not ln.lstrip().startswith(">"))
                # 引号段剥离（v2 批，pcf-crit2 复核）：主控转述/受审资产文案里的
                # 「」/弯引号包裹段非用户本意。防吞真纠偏双守卫：句首纠偏动词
                # （别/勿/禁/不要…）或句尾指令（清理下/改掉…）在场时不剥
                if not re.search(r"^[^「”\"']{0,6}(别|勿|禁|不要|停止)", text) \
                        and not re.search(r"[，,]\s*(清理下|改掉|重做|收敛下)\s*$", text):
                    # T58 勘误（2026-09-26）：原第三分支与第二分支逐字节重复，删；
                    # ASCII 直引号有意不剥（会误伤代码/JSON 字面量），口径非缺陷
                    text = re.sub(r"「[^」]*」|“[^”]*”", "", text)
                for m in _CORRECTION_MARKERS:
                    if m in text:
                        counts[m] = counts.get(m, 0) + 1
                rej = [r for r in _REJECT_MARKERS if r in text]
                if rej:
                    rejected = True
                    reject_src = reject_src or rej[0]
    except Exception as _e:  # 留痕批（B2-6 同形）
        print(f"[reflex-check] transcript 读取失败，跳过：{_e}", file=sys.stderr)
        return None
    entry["correction_counts"] = counts
    reminded = entry.setdefault("corrected", [])
    heavy = [m for m, c in counts.items() if c >= 3 and m not in reminded]
    mid = [m for m, c in counts.items() if c >= 2 and m not in reminded]
    # 显式拒绝单独触发重度（等价 diff>30% 档）；独立去重标记——rejected 无 marker
    # 载体，若复用 reminded 会在每次 Stop 重复 block-heavy
    reject_reminded = entry.setdefault("reject_reminded", False)
    if heavy or (rejected and not reject_reminded):
        # 重度：3 次同类 或 显式拒绝——触发经验提炼流程。
        # marked 兜底：显式拒绝但计数 <2 时 heavy/mid 均空 → 曾输出空括号信号
        # 「重度纠偏信号（）」（2026-09-12 实证），主控无从对照提取 lesson——
        # 回退按计数降序列前 3 个 marker，全空才用「显式拒绝」占位
        marked = heavy or mid or sorted(counts, key=counts.get, reverse=True)[:3]
        if not marked:
            marked = ["显式拒绝"]
        if rejected:
            entry["reject_reminded"] = True
        reminded.extend(marked)
        del reminded[:-20]
        _append_evolution_record(counts, rejected)
        _append_log({"ts": _now(), "hook": "reflex-correction", "event": "block-heavy",
                     "session_id": session_id,  # T116 收集补链（2026-09-27）：无 sid 不可归属，抽验无从做起
                     "markers": marked, "rejected": rejected, "reject_src": reject_src,
                     "counts": {m: counts.get(m, 0) for m in marked}})
        loop_note = _loop_closure_note(marked)
        # sys-02：reject 触发时标注触发源——主控可区分「真重度」与「单词误触」
        # （实测 block-heavy 10 次中 6 次仅由单个 reject 词触发且文案无来源可辨）
        src_note = (f"触发源：显式拒绝词〈{reject_src}〉。" if rejected else "")
        return (f"重度纠偏信号（{'、'.join(marked)}）。{src_note}——触发经验提炼：对照 transcript 提取"
                "lesson 后沉淀（skill 条款级→EVOLUTION.md；机制/架构级→decision-record 留 ADR），"
                "Evolution Record 已落盘 .claude/.state/evolution-pool/（本地候选池不入库，"
                "内容字段待主控补写）；已沉淀则直接结束即可，同类不再重复提醒。" + loop_note)
    if mid:
        # 中度：同类 2 次——进观察，提醒沉淀建议（一周内 >3 次的升级判定由重复触发自然覆盖）
        reminded.extend(mid)
        del reminded[:-20]
        _append_log({"ts": _now(), "hook": "reflex-correction", "event": "block",
                     "markers": mid, "counts": {m: counts[m] for m in mid}})
        loop_note = _loop_closure_note(mid)
        return (f"同类纠正信号已反复出现（{'、'.join(mid)}）——该偏好/要求已多次表达，"
                "建议当场沉淀：长期偏好→memory、行为纪律→CLAUDE.md、skill 相关纠正→（缓存提示：MEMORY/CLAUDE.md 属 system 域，中途写入致提示缓存全量失效——多条纠正合并一次写入；纯文档类大批沉淀可挪收尾）"
                ".claude/.state/corrections/<skill>.md（模板 ~/.claude/skills/_shared/templates/corrections-template.md），"
                "避免下次重犯；已沉淀则直接结束即可，同类不再重复提醒。" + loop_note)
    if counts:
        # 轻：单次纠正——Skill 不变，仅计数留痕（成功率统计分母/观察池积累）
        _append_log({"ts": _now(), "hook": "reflex-correction", "event": "light",
                     "counts": counts})
    return None


# ---------- 检查4：输出机械检（C 类后置条款零模型扫描，独立提醒档，不 block 不计数） ----------
# 只做误报风险最低的 5 项机械扫描；句长/括号密度/语气类不可机械判，明确不做。
# 扫描对象：assistant 最后一条文本输出（同 _check_clarify 的行级流式哲学，但
# assistant 文本在 content[].text 内，须 JSON 解析提取——解析失败的行跳过留痕）。
_OUTPUT_BLACKLIST = ("赋能", "值得注意的是", "综上所述", "深度探讨")
_OUTPUT_BLACKLIST_RE = re.compile(r"不仅仅是[\s\S]{0,30}?更是")  # 关联句式单独正则
_OUTPUT_STATUS_SYMBOLS = ("✅", "⚠️")
# 「性/度/化」词尾抽象词检测白名单：词尾本身是既有技术词/日常词一部分的不算
# （先收全排除表再定正则——正则只报白名单外的命中）
_ABSTRACT_WHITELIST = {
    # X性
    "属性", "性能", "特性", "可用性", "可靠性", "兼容性", "稳定性", "准确性",
    "完整性", "一致性", "安全性", "灵活性", "伸缩性", "可扩展性", "可维护性",
    "唯一性", "相关性", "时效性", "周期性", "线性", "非线性", "幂等性",
    # X度
    "精度", "维度", "角度", "程度", "密度", "高度", "温度", "湿度", "长度",
    "宽度", "厚度", "速度", "幅度", "调度", "跨度", "粒度", "强度", "难度",
    "并发度", "重复度", "关联度", "覆盖度", "命中度", "偏差度", "离散度",
    "维度表", "容错度",
    # X化
    "优化", "自动化", "标准化", "结构化", "规范化", "序列化", "参数化",
    "可视化", "数字化", "模块化", "组件化", "格式化", "简化", "分类", "转化",
    "变化", "转化率", "退化", "孵化", "消化", "量化", "老化",
    # 单字组合常见词
    "个性", "女性", "男性", "人性", "文化",
}
_ABSTRACT_RE = re.compile(r"[一-龥]{1,4}(?:性|度|化)")
# 白名单先行遮蔽（长词优先）：直接对正则命中做整串白名单比对会因正则向前吞 1-4 字
# 产生错位子串（实证：「性能优化」命中「能优化」、「通过性能」命中「通过性」），
# 先把白名单词整体遮蔽再扫，重叠词（性能+优化）两侧都不再出命中
_ABSTRACT_WHITELIST_SORTED = sorted(_ABSTRACT_WHITELIST, key=len, reverse=True)


def _mask_whitelist(text: str) -> str:
    for w in _ABSTRACT_WHITELIST_SORTED:
        text = text.replace(w, "□" * len(w))
    return text


def _strip_code_fences(text: str) -> str:
    """剔除 ``` 围栏代码块：代码内容（如 ✅ 常用于测试断言/示例）不属输出风格问题。"""
    return re.sub(r"```[\s\S]*?```", "", text)


def _extract_last_assistant_text(transcript_path: str) -> str:
    """取 transcript 中最后一条 assistant 文本输出（content[] 内 type=text 块拼接）。
    行 JSON 解析失败跳过（与 _check_clarify 同哲学：不假设格式，坏行不致命）。"""
    text = ""
    try:
        with open(transcript_path, encoding="utf-8") as fh:
            for line in fh:
                if '"role":"assistant"' not in line and '"role": "assistant"' not in line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                msg = obj.get("message") or obj
                content = msg.get("content")
                if not isinstance(content, list):
                    continue
                chunks = [b.get("text", "") for b in content
                          if isinstance(b, dict) and b.get("type") == "text"]
                joined = "\n".join(c for c in chunks if c)
                if joined.strip():
                    text = joined
    except Exception as _e:  # 留痕批：读失败零输出，不影响主流程
        print(f"[reflex-check] assistant 文本提取失败，跳过：{_e}", file=sys.stderr)
        return ""
    return text


def _check_output_mechanics(entry: dict, transcript_path: str | None) -> str | None:
    """检查4：输出机械检——零模型扫描 assistant 最后一条文本，命中才一句话提醒。
    独立提醒档：不进 block reasons、不占三档计数；每会话只提醒一次（防打扰，
    本机打扰度线 15%）；无命中零输出。"""
    if not transcript_path:
        return None
    text = _extract_last_assistant_text(transcript_path)
    if not text:
        return None
    text = _strip_code_fences(text)
    hits: list[str] = []
    # ① 黑名单高频词（5 个硬词：4 子串 + 1 句式）
    bl = [w for w in _OUTPUT_BLACKLIST if w in text]
    if _OUTPUT_BLACKLIST_RE.search(text):
        bl.append("不仅仅是…更是")
    if bl:
        hits.append("黑名单词（" + "、".join(bl) + "）")
    # ② ✅⚠️ 状态符号
    syms = [s for s in _OUTPUT_STATUS_SYMBOLS if s in text]
    if syms:
        hits.append("状态符号（" + "、".join(syms) + "）")
    # ③ 「性/度/化」抽象词尾（白名单排除）
    abstract = sorted({m for m in _ABSTRACT_RE.findall(_mask_whitelist(text))
                       if m.strip("□") and m not in _ABSTRACT_WHITELIST})
    if abstract:
        hits.append("抽象词尾（" + "、".join(abstract[:5]) + "）")
    # ④ 单段超 7 行
    if any(p.count("\n") + 1 > 7 for p in re.split(r"\n\s*\n", text)):
        hits.append("单段超7行")
    # ⑤ 嵌套列表 >2 层（前导空格 4+ 即第 3 层起）
    for ln in text.splitlines():
        m = re.match(r"^( +)(?:[-*+]|\d+\.)\s", ln)
        if m and len(m.group(1)) >= 4:
            hits.append("嵌套列表超2层")
            break
    if not hits:
        return None
    if entry.get("output_mechanics_reminded"):
        _append_log({"ts": _now(), "hook": "reflex-output", "event": "silent",
                     "hits": hits})
        return None
    entry["output_mechanics_reminded"] = True
    _append_log({"ts": _now(), "hook": "reflex-output", "event": "remind",
                 "hits": hits})
    return ("输出机械检命中：" + "；".join(hits) +
            "。建议按输出协议重写后再交付（本会话仅此一次提醒，不拦截）。")


def main() -> int:
    # hook 不能阻断主流程：任何异常 stderr 可见 + exit 0，绝不抛给会话
    try:
        payload: dict = {}
        try:
            raw = sys.stdin.read()
            if raw.strip():
                payload = json.loads(raw)
        except Exception:
            payload = {}
        session_id = str(payload.get("session_id") or "nosession")
        transcript_path = payload.get("transcript_path") or None

        # 旧单文件状态惰性迁移已退役（2026-08-31：legacy reflex-state.json 已迁完删除）
        state = load_partition("stop")
        if state.get("disabled"):
            return 0

        raw_entry = (state.get("sessions") or {}).get(session_id)
        # 兼容旧状态格式（v1 为 hash 列表）→ 迁移为双列表结构
        if isinstance(raw_entry, list):
            raw_entry = {"code_hashes": raw_entry, "clarify_hashes": []}
        entry = raw_entry or {"code_hashes": [], "clarify_hashes": []}
        global_hashes: dict = state.get("global_hashes") or {}  # 旧 state 无此 key 兼容
        gh_before = set(global_hashes)  # 本运行新增的去重标记：锁内合并进最新真值

        reasons: list[str] = []
        code_digest: str | None = None
        r = _check_code(entry, global_hashes)
        if r:
            code_digest = r[1]
            reasons.append(f"【代码收尾】{r[0]}")
        r = _check_clarify(session_id, entry, transcript_path)
        if r:
            reasons.append(f"【澄清沉淀】{r}")
        r = _check_correction(entry, transcript_path)
        if r:
            reasons.append(f"【纠正沉淀】{r}")
        # 检查4 输出机械检：独立提醒档——不进 block reasons、不计数，命中才
        # 一句话 stdout 提示（Stop hook exit 0 stdout 进 transcript 展示），无命中零输出
        mech_note = _check_output_mechanics(entry, transcript_path)

        # block 与静默都持久化：去重标记不落盘则下轮 Stop 重复提醒
        # 锁内对最新真值读-改-写：锁外快照可能陈旧（多 session 并发 Stop），
        # 直接整写会把并发者刚写入的 sessions/global_hashes 覆盖丢更新
        gh_added = {d: global_hashes[d] for d in global_hashes if d not in gh_before}
        try:
            with flock_ctx("reflex-stop"):
                fresh = load_partition("stop")
                if fresh.get("disabled"):
                    return 0  # 锁内二次检查：用户刚置的 disabled 不能被覆写
                fsessions: dict = fresh.get("sessions") or {}
                fsessions[session_id] = entry  # entry 会话作用域，覆盖自身条目不涉他会话
                if len(fsessions) > 20:  # 只留最近 20 个会话，防状态文件膨胀
                    fsessions = dict(list(fsessions.items())[-20:])
                fgh: dict = fresh.get("global_hashes") or {}
                # 跨会话去重复查（重叠窗口兜底）：锁外判定基于可能陈旧快照——并发 Stop
                # 重叠时他 session 刚 block 过同批次（多 session 同工作区批次相同），
                # fresh 中已有且 TTL 内则本会话静默，防同批次双 block
                if (code_digest is not None and code_digest in fgh
                        and time.time() - fgh[code_digest] < GLOBAL_TTL):
                    reasons = [x for x in reasons if not x.startswith("【代码收尾】")]
                    _append_log({"ts": _now(), "hook": "reflex-check",
                                 "event": "silent-overlap", "hash": code_digest[:8]})
                # setdefault 而非 update：重叠窗口内保留他 session 的首写时间戳——
                # update 会刷新 TTL 起点，把跨会话去重窗口无限延长（本该到期重提醒）
                for d, ts in gh_added.items():
                    fgh.setdefault(d, ts)
                # TTL 修剪与截断在锁内执行：两会话各自剪掉对方刚写 hash 的竞态
                now_ts = time.time()
                fgh = {d: ts for d, ts in fgh.items() if now_ts - ts < GLOBAL_TTL}
                if len(fgh) > 50:
                    fgh = dict(sorted(fgh.items(), key=lambda kv: kv[1])[-50:])
                fresh["disabled"] = False
                fresh["sessions"] = fsessions
                fresh["global_hashes"] = fgh
                atomic_write(STATE_STOP, json.dumps(fresh, ensure_ascii=False))
        except TimeoutError:
            print("[reflex-check] stop-state 锁超时，跳过状态写", file=sys.stderr)
        if reasons:
            print(json.dumps({
                "decision": "block",
                "reason": "反射层提醒（reflex-check）：" + "；".join(reasons),
            }, ensure_ascii=False))
        if mech_note:
            print("反射层提醒（reflex-check）：" + mech_note)
    except Exception as exc:  # noqa: BLE001 — hook 容错：stderr 可见，不阻断会话
        print(f"[reflex-check] 失败: {exc}", file=sys.stderr)
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
