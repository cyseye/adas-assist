#!/usr/bin/env python3
"""weekly-eval.py — 周评估指标异步计算（cron 驱动；指标计算零模型，超线分析走后台模型）。

此前周评估三指标由主模型在会话内跑 jq 实时计算——采集已全脚本化，分析却占主模型
轮次（model-governance 裁决：采集数据分析禁实时进模型，先脚本落报告主控只读结论）。
本脚本把指标计算下沉为 cron 异步任务：按 7 天滚动窗口算三指标 + 阈值判定，产出
<repo>/.claude/.build/weekly-eval-report.md（≤10 行）；session-start 到期时只注入
报告结论，主控消化后自行 touch marker（脚本不 touch——主控未消费前下轮重算覆盖，
成本低且保证会话开局总能看到到期报告）。

指标口径与 `~/.claude/skills/_shared/evolution-discipline.md §周评估` 单源同改：
- 召回率   = match / knowledge-recall 总行数（排除 test- 前缀 session），参考线 >30%
- 打扰度   = reflex-check block / (block+silent+silent-verified)，参考线 <15%
- 澄清转化 = reflex-clarify resolved 事件 / block 次数（2026-09-14 管道修复：reflex-check 检测澄清+窗口内 ADR 沉淀落 resolved；原 corrections/候选池口径结构性恒 0），参考线 >20%
零结果必须打印分母（sample=n）：零信号≠通过，分母为 0 的指标判 no_data 而非达标。

共享契约：meta-regression.py 每次运行向 ~/.claude/.build/evolution-daily.log 追加
`regression_fail=N/13 cap_run cap_fail` 留痕行（单源语义见其 docstring），周评估/
finalizer 绿判据按当日该行 grep 消费。读者侧对账：本脚本 compute_metrics 扫日档近
7 天窗口，无 regression_fail 具名行即升 ⚠ meta-regression-gap（兜底周批整周忘跑）。

用法：weekly-eval.py [repo_root ...]（缺省= cwd 上溯第一个含 .claude 的项目）。
7 天节流由「到期才重算」自然实现：cron 每日跑，未到期静默 exit 0。

Intelligence Plane（2026-09-13 用户裁决升级）：报告含「后台分析段」——仅当存在
超线 ⚠ 项时调执行模型（--model sonnet 路由，不绑具体型号）生成归因+建议；无超线
零模型调用。分析段失败 fail-closed 跳过，脚本段不受影响。

--backfill <id>=<value>：机械回填 measured 原始值（P0-2）。契约：本参数只写
token-baseline.json 中指定项的 measured 字段；expect/state/回退判定一律留人工
（effect-governance 裁决），脚本零判定——登记归机器、裁决留人工。docstring、
evolution-discipline §效果验证协议、effect-governance SKILL.md 三处同步此契约。

ADR 证据绊线契约（campaign-20260916 簇1，与 finish_check.adr-evidence 同批）：本脚本的
ADR 治理扫描覆盖 decisions/adr/ 全目录（含 PENDING/草稿态文件，封「只扫 Accepted」绕行）；
核验输出指针清单非计数；正则核验=召回受限绊线，PASS 不得作 confidence 复核充分条件。

进化三档 cadence（数值单源 io-budgets.evolution_cadence，进化档位闭环裁决）：
- 周批周日锚：节流从 marker mtime 滚动窗口改为「上个周日」日期锚——cron 每日跑，
  未到新周日不重算（mtime 兜底 fail-open：marker 缺失/损坏按到期处理）。
- 日档落盘日志：未到期分支追加一行 <repo>/.claude/.build/evolution-daily.log
  （日期+PENDING 计数+超线有无+联审到期），零模型零注入，想看时随时查。
- 部门联审：joint-review.marker 双周锚（joint_review_window_days），与周批 marker
  分离互不干扰；任何一次联审执行（触发词手动或到期自动）后由主控跑 --joint-review
  touch 重置——周期消费即重置，防漂移堆积（用户裁决）。
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta
from collections import deque
from pathlib import Path

# 数值单源读取（P0-1）：io_budget 依赖 shared_state 双根定位，脚本可从任意 cwd 执行
from shared_state import asset_claude, io_budget

WINDOW_DAYS = 7
# 双根分裂修复（2026-09-27 T88 收口）：原相对路径常量被 `repo / 常量` 拼接，
# repo=HOME 时落入 ~/.claude/.claude 幻影根，与 session-start 读根分叉。
# 改锚资产根绝对路径（pathlib 语义：绝对成员吞掉左侧 repo，全消费点零改写自动收敛）
MARKER = asset_claude() / ".build" / "weekly-eval.marker"
REPORT = asset_claude() / ".build" / "weekly-eval-report.md"
DAILY_LOG = asset_claude() / ".build" / "evolution-daily.log"
JOINT_MARKER = asset_claude() / ".build" / "joint-review.marker"


def _within_window(ts: str, cutoff: datetime) -> bool:
    try:
        return datetime.strptime(ts, "%Y-%m-%d %H:%M:%S") >= cutoff
    except (ValueError, TypeError):
        return False  # 时间戳不合法的行不计入分母（脏行容错，宁缺勿污染）


def _week_anchor(dt: datetime) -> datetime.date:
    """本周锚点=本周日（周一为一周起点则取上周日）。周日锚定使周批消费日可预期。"""
    days_since_sunday = (dt.weekday() + 1) % 7  # Monday=0 → 周日=0，周六=6
    return (dt - timedelta(days=days_since_sunday)).date()


def _strategy_check(repo: Path) -> tuple[list[str], int, int, int, int] | None:
    """战略对账（蓝图 §四）：超线清单+四项分母。compute_metrics 与日档日志共用。
    阈值单源=signal-tiers.strategy_review；键缺失返回 None（fail-closed 不判定，
    与 weekly_eval_refs 同款——禁幽灵阈值继续发射，逆向审查 Med-6 修复）。"""
    asset = Path.home() / ".claude"
    try:
        tiers = json.loads((asset / "skills" / "_shared" / "signal-tiers.json").read_text(encoding="utf-8"))
        th = tiers.get("strategy_review") or {}
        th["skill_total"]  # 探针：键结构不完整同按缺失处理
    except Exception:
        print("[weekly-eval] strategy_review 键缺失，本轮战略对账不判定（fail-closed）", file=sys.stderr)
        return None
    n_meta = len([d for d in (asset / "skills").iterdir() if d.is_dir()]) if (asset / "skills").is_dir() else 0
    n_proj = len([d for d in (repo / ".claude" / "skills").iterdir() if d.is_dir()]) if (repo / ".claude" / "skills").is_dir() else 0
    n_meta_adr = len(list((asset / "decisions" / "adr" / "meta").glob("*.md")))
    # 2026-09-20 B组修复（T7 迁锚跟进）：计数锚从 PENDING.md（派生视图，session-review 整文件重写清手工段）迁 BACKLOG.md 存活项。
    # 口径=「## 待办（存活项）」段间截取的 bullet 数（防把已闭环验尸行计入）；session-start 仍读 PENDING 派生视图（注入口径有意分叉）。
    # pending 阈值量纲随锚迁移待重定标（历史 n=3 无超线数据，no_data 留 W2 裁决，禁静默承值 15）。
    backlog_path = asset / "decisions" / "postmortems" / "BACKLOG.md"
    btext = backlog_path.read_text(encoding="utf-8") if backlog_path.exists() else ""
    _m = re.search(r"^## 待办（存活项）\n(.*?)(?=^## )", btext, re.S | re.M)
    n_pending = len([ln for ln in (_m.group(1) if _m else "").splitlines() if ln.startswith("- ")])
    breaches = []
    if n_meta + n_proj > th["skill_total"]:
        breaches.append(f"skill 总数 {n_meta + n_proj}>{th['skill_total']}（元层 {n_meta}+项目仓 {n_proj}）")
    if n_meta > th["skill_meta"]:
        breaches.append(f"元层 skill {n_meta}>{th['skill_meta']}")
    if n_meta_adr > th["meta_adr"]:
        breaches.append(f"meta ADR {n_meta_adr}>{th['meta_adr']}")
    if n_pending > th["pending"]:
        breaches.append(f"BACKLOG待办 {n_pending}>{th['pending']} 行（量纲待重定标，见源码注释）")
    return breaches, n_meta, n_proj, n_meta_adr, n_pending


def _joint_due(repo: Path) -> tuple[bool, int]:
    """联审到期判定：joint-review.marker mtime 超 joint_review_window_days 即到期。
    配置不可读=功能未启用（fail-closed，禁代码兜底数值）。marker 缺失=从未审过→到期。"""
    cad = io_budget("evolution_cadence") or {}
    days = int(cad.get("joint_review_window_days") or 0)
    if days <= 0:
        return False, 0
    marker = repo / JOINT_MARKER
    if not marker.exists():
        return True, days
    age = datetime.now().timestamp() - marker.stat().st_mtime
    return age > days * 86400, days


def _websearch_quota_reset() -> tuple[str, str]:
    """channel-matrix-recheck 探测（议题5 落地，2026-09-19）。

    本仓无外部检索状态端点——无零配额探测面即返回 unknown（不硬造探测），
    由调用方走日期门+➖顺延。
    """
    return "unknown", "本仓无外部检索通道，无零配额探测面"



def _jsonl_lines(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    for ln in path.read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(ln))
        except json.JSONDecodeError:
            continue
    return out


def _kr_mod():
    """装载 knowledge-recall.py（文件名含连字符不可直接 import；该模块顶层 import
    shared_state，spec 加载不带上其目录，须手动补 sys.path——零模型纯复用其装载器）。"""
    import importlib.util
    import sys
    d = Path(__file__).parent
    if str(d) not in sys.path:
        sys.path.insert(0, str(d))
    spec = importlib.util.spec_from_file_location("knowledge_recall", d / "knowledge-recall.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _memory_hit_recon(repo: Path, cutoff: datetime) -> list[str]:
    """memory 命中聚合（淘汰依据读者面，只列不删）：sidecar memory-hits.json 为
    命中计数控（hits/last_hit），knowledge-recall 装载器枚举条目全集补 0 命中。
    Top10=权重最高；Bottom10=命中最低（含 0 命中）；淘汰候选=0 命中且 30 天未更新
    （口径：frontmatter modified 优先，缺失退化用文件 mtime 并标注——现状 memory 文件
    普遍无 modified frontmatter，纯 frontmatter 口径下该节恒空，退化口径保可用性）。
    样本纪律：hits 记录 <10 条判样本不足，禁编造排行。"""
    _ = repo, cutoff
    side = Path.home() / ".claude/.state/memory-hits.json"
    try:
        hits = json.loads(side.read_text(encoding="utf-8"))
    except Exception:
        hits = {}
    if not isinstance(hits, dict) or len(hits) < 10:
        return [f"- ➖ memory 命中聚合：样本不足（hits 记录 {len(hits) if isinstance(hits, dict) else 0} < 10 条），不列 Top/Bottom"]
    try:
        kr = _kr_mod()
        universe = {}
        for e in (kr._load_knowledge() + kr._load_memory_index(kr._user_memory())
                  + kr._load_project_memory()):
            universe.setdefault(e["path"], e.get("title") or Path(e["path"]).name)
    except Exception:
        universe = {}
    total = sum(int((v or {}).get("hits") or 0) for v in hits.values())
    ranked = sorted(hits.items(), key=lambda kv: -int((kv[1] or {}).get("hits") or 0))

    def _name(p: str) -> str:
        return f"{universe.get(p, Path(p).name)}"

    top = [f"{_name(p)}×{int((v or {}).get('hits') or 0)}" for p, v in ranked[:10]]
    # Bottom：sidecar 内命中最低的 + 全集中 0 命中的，合并按命中升序取 10
    zero = [p for p in universe if p not in hits]
    bottom_pool = [(p, int((v or {}).get("hits") or 0)) for p, v in ranked[-10:]] + [(p, 0) for p in zero]
    bottom = sorted(bottom_pool, key=lambda x: x[1])[:10]
    lines = [f"- memory 命中聚合：总命中 {total} 次 / 记录 {len(hits)} 条 / 全集 {len(universe) or f'{len(hits)}(装载失败,缺0命中面)'} 条",
             f"  - 命中 Top10：{'; '.join(top) if top else '无'}",
             f"  - 命中 Bottom10（含 0 命中）：{'; '.join(f'{_name(p)}×{n}' for p, n in bottom) if bottom else '无'}"]
    # 淘汰候选（仅列出，不自动删）：0 命中且 30 天未更新
    now = datetime.now()
    stale: list[str] = []
    # modified 读取闭包：kr 装载成功用 frontmatter 口径，失败则整节退化（无 fm 源=mtime 兜底）
    for p in zero[:500]:  # 上限防全集异常膨胀拖垮周评估
        try:
            mod = kr._frontmatter_fields(Path(p))[1] if universe else ""
            src = "fm"
            if not mod:
                mtime = datetime.fromtimestamp(Path(p).stat().st_mtime)
                mod, src = mtime.strftime("%Y-%m-%d"), "mtime"
            if (now - datetime.strptime(mod, "%Y-%m-%d")).days > 30:
                stale.append(f"{universe.get(p, Path(p).name)}[{src}:{mod}]")
        except Exception:  # noqa: BLE001 — 单条日期异常跳过，不污染候选清单
            continue
    lines.append(f"  - 淘汰候选（0 命中且 >30 天未更新，仅列出留人工裁决，不自动删）：{len(stale)} 条"
                 + (f"：{'; '.join(stale[:10])}" + ("…" if len(stale) > 10 else "") if stale else "（暂无）"))
    return lines





def _knowledge_consumption(repo: Path, cutoff: datetime) -> str:
    """K1 知识消费聚合列（纯聚合不判定）：流式统计近 7 天 knowledge-recall 的 distinct
    命中条目与 no_match 次数。条目死≠召回坏——聚合只供 effect-governance 周期闭环检查
    消费，不进 signal-tiers、不改三指标口径。项目仓侧为主，元层侧兜底（数据可能在任一落点）。"""
    for path in (repo / ".claude/.build/reflex-hooks.jsonl",
                 Path.home() / ".claude/.build/reflex-hooks.jsonl"):
        if not path.exists():
            continue
        titles: set = set()
        no_match = 0
        with path.open(encoding="utf-8") as fh:  # 流式逐行：文件 9k+ 行，禁整读
            for ln in fh:
                try:
                    e = json.loads(ln)
                except json.JSONDecodeError:
                    continue
                if e.get("hook") != "knowledge-recall" or not _within_window(e.get("ts", ""), cutoff):
                    continue
                if e.get("event") == "match":
                    titles.update(e.get("titles") or [])
                elif e.get("event") == "no_match":
                    no_match += 1
        if titles or no_match:
            return (f"- 知识消费聚合：distinct 命中 {len(titles)} 条 / no_match {no_match} 次"
                    f"（条目死≠召回坏，纯聚合不判定 → effect-governance 周期闭环检查）")
    return "- 知识消费聚合：无样本（n=0，两侧 reflex-hooks 均无 knowledge-recall）"



def _sys01_recon(repo: Path, cutoff: datetime, recent: list[dict]) -> list[str]:
    """sys-01 确认率对账（BACKLOG T8，2026-09-20 接线，只报不判）：分子=窗口内
    session-start proposal 事件数（adr-consistency KNOWLEDGE 缺条目提案，slugs
    埋点自 2026-09-20 起）；分母侧=KNOWLEDGE.md 窗口内 git 新增行按 slug 命中数。
    N=0 不判定（无数据不判定纪律）；slug 埋点前的旧 proposal 事件无 slugs，命中
    数单独声明口径，不冒充可对账。"""
    prop = [e for e in recent if e.get("hook") == "session-start" and e.get("event") == "proposal"]
    n = len(prop)
    slugs = sorted({s.strip() for e in prop for s in str(e.get("slugs") or "").split(",") if s.strip()})
    if n == 0:
        return ["- ➖ sys-01 确认率：无 proposal 事件（n=0），不判定"]
    hit = set()
    kg = Path.home() / ".claude" / "decisions" / "KNOWLEDGE.md"  # 同指针抽查块口径
    try:
        out = subprocess.run(
            ["git", "log", "--since", cutoff.strftime("%Y-%m-%d %H:%M"), "-p", "--",
             "decisions/KNOWLEDGE.md"],
            cwd=kg.parent.parent, capture_output=True, text=True, timeout=15)
        for ln in out.stdout.splitlines():
            if ln.startswith("+") and "adr/" in ln:
                for s in slugs:
                    if f"/{s}.md" in ln:
                        hit.add(s)
    except (OSError, subprocess.TimeoutExpired):
        hit = set()
        git_note = "（git 不可读，命中按 0 报）"
    else:
        git_note = ""
    m = len(hit)
    rate = f"{m}/{n} = {m / n:.0%}"
    slug_note = "" if slugs else "（slug 埋点 2026-09-20 起采集，本批事件无 slugs 不可对账）"
    return [f"- sys-01 确认率：分子 proposal {n}（window 内）/ KNOWLEDGE 新增按 slug 命中 {m}"
            f"（共 {len(slugs)} 个 slug）{slug_note}→ 确认率 {rate}{git_note}（N=0 不判定，本行只报不判）"]


def _security_recon(repo: Path, cutoff: datetime) -> list[str]:
    """安全治理对账（蓝图 security-governance-blueprint-20260920 §回顾与演练，T16 尾巴，只报不判）：
    ①G2 拦截统计：gate-audit.log 窗口内 no-verify-escape 行数——拦截走 stderr 即时反馈，
    无独立台账，审计行缺失时如实报「无独立台账」禁编造计数。
    ②G1 状态：g1-outbound-guard.py 存在性=「就绪待批（未接线）」，缺=设计件佚失 ⚠。"""
    _ = repo
    lines = []
    log = Path.home() / ".claude" / "skills" / "skill-evolution" / "registry" / "gate-audit.log"
    n = 0
    if log.exists():
        try:
            for ln in log.read_text(encoding="utf-8").splitlines():
                if "no-verify-escape" in ln and ln[:16] >= cutoff.strftime("%Y-%m-%d %H:%M"):
                    n += 1
        except OSError:
            n = 0
    lines.append(f"- G2 拦截统计：G2 拦截次数无独立台账（拦截走 stderr 即时反馈），逃生审计窗口内 {n} 次"
                 f"（gate-audit.log {'在' if log.exists() else '缺'}，只报不判）")
    g1 = Path.home() / ".claude" / "skills" / "skill-evolution" / "scripts" / "g1-outbound-guard.py"
    lines.append(f"- {'✅' if g1.exists() else '⚠'} G1 出网门："
                 + ("就绪待批（未接线）" if g1.exists() else "设计件佚失 ⚠（g1-outbound-guard.py 缺失）"))
    return lines


def _g4_recon(repo: Path, cutoff: datetime) -> list[str]:
    """G4 两对账口径（spawn model 留痕率 + 工具失败/重试率，2026-09-19 接线，只报不判）：
    ①model 留痕：registry invocations tool=Agent 行（同 spawn 趋势分母）——窗口总数/有
    model 字段数/留痕率 + model 值分布；只报数为「主模型禁入执行类」审计提供可见性，
    不做合规判定（sonnet=执行路由、opus/glm-*=主模型显式路由，语义归 model-governance）。
    ②失败/重试：registry tool-calls 行——success 字段仅部分行携带（hook 分批上线遗留），
    失败率只对有字段子集计算并如实报覆盖率；覆盖率 <20% 标注「口径覆盖不足，结论仅参考」。
    分母纪律：零行打印分母判 no_data，防零信号假通过。"""
    inv = [e for e in _jsonl_lines(_registry_invocations())
           if e.get("tool") == "Agent" and _within_window(e.get("ts", ""), cutoff)]
    lines = []
    if not inv:
        lines.append("- ➖ G4·model 留痕率：无样本（Agent 行 n=0），不判定")
    else:
        from collections import Counter as _C
        modeled = [e for e in inv if e.get("model")]
        dist = _C(e["model"] for e in modeled).most_common()
        lines.append(f"- G4·spawn model 留痕率 {len(modeled) / len(inv):.0%}"
                     f"（{len(modeled)}/{len(inv)}，Agent 行口径）；model 分布 {dist}"
                     "——只报数不判定，主模型禁入执行类合规归 model-governance 审计")
    tc = [e for e in _jsonl_lines(Path.home() / ".claude/skills/skill-evolution/registry/tool-calls.jsonl")
          if _within_window(e.get("ts", ""), cutoff)]
    if not tc:
        lines.append("- ➖ G4·失败/重试率：无样本（tool-calls 行 n=0），不判定")
    else:
        succ_rows = [e for e in tc if e.get("success") in ("ok", "fail")]
        fails = sum(1 for e in succ_rows if e["success"] == "fail")
        cov = len(succ_rows) / len(tc)
        note = "；⚠ 口径覆盖不足（<20%），结论仅参考" if cov < 0.2 else ""
        rate = f"失败率 {fails / len(succ_rows):.1%}（{fails}/{len(succ_rows)}）" if succ_rows else "失败率无样本"
        # 精确重复口径已删（2026-09-19 抽样证伪）：summary 采集截断 50 字符致 91.8% 为前缀
        # 碰撞、全输入比对 99.1% 不同、首调用 is_error=0 例——该指标测的是截断碰撞率，
        # 不是重试率。若将来重立，前置=采集 hook 对全输入做哈希。
        lines.append(f"- G4·工具失败/重试：窗口调用 {len(tc)}，success 字段覆盖 {cov:.0%}（{len(succ_rows)}），"
                     f"{rate}{note}"
                     "——覆盖不足段只报不判，覆盖率提升归采集侧 hook 处置")
    return lines


def _skill_zero_invocation_recon(repo: Path) -> list[str]:
    """skill-zero-invocation 对账（议题B 轮2 XB2，2026-09-19 接线，只报不判）：近 30 天
    invocations 各治理 skill 触发计数（tool/target 任一命中即算），对 skills/ 目录已登记
    清单中 0 触发者升 ⚠「skill 静默悬空」。触发计数可能低估（Skill 留痕 hook 覆盖有限），
    故只报不判——处置（删/留/触发词补挂）归 memory-governance/decision-lifecycle。
    落地宽限（议题G G4，2026-09-19）：创建 <14 天的 skill 排除出零触发清单（防新件
    如新登记 skill 尚未有自然触发即假 ⚠）；年龄取 git log 首次提交时间优先（mac
    birthtime/APF 携带不可靠），git 不可得回退 birthtime。自指注记：skill-evolution
    本身入口是脚本/hook 非 Skill 工具，计数结构性为零——排除出清单不做悬空判定。"""
    skills_home = Path.home() / ".claude" / "skills"
    grace = datetime.now() - timedelta(days=14)

    def _skill_birth_map() -> dict[str, datetime]:
        """git 首提时间批量表（2026-09-25 方向D C3 续探轮）：原逐 skill spawn
        一次 `git log -- <name>`（登记 skill 数=子进程数），收敛为单次
        `--name-only` 全量建表；git log 倒序输出，同名取首个命中=最旧时间戳，
        与原逐名 stamps[-1] 语义等价；git 不可得返回空表走 birthtime 回退。"""
        out: dict[str, datetime] = {}
        try:
            r = subprocess.run(
                ["git", "-C", str(skills_home), "log", "--diff-filter=A",
                 "--no-renames", "--format=%at", "--name-only"],
                capture_output=True, text=True, timeout=15)
            pending_ts: int | None = None
            for ln in r.stdout.splitlines():
                ln = ln.strip()
                if not ln:
                    # 实测格式为「时间戳行＋空行＋文件名行」，空行后文件名仍归
                    # 最近时间戳，故不重置 pending_ts（首版重置致全表空，已证伪）
                    continue
                if ln.isdigit():
                    pending_ts = int(ln)
                elif pending_ts is not None and "/" in ln:
                    # 仓根相对路径 `skills/<name>/...`；git log 倒序输出，同名反复
                    # 覆盖→循环结束留存最旧=首次提交（对齐旧版 stamps[-1] 语义）
                    parts = ln.split("/")
                    if parts[0] == "skills" and len(parts) >= 2:
                        out[parts[1]] = datetime.fromtimestamp(pending_ts)
        except Exception:
            return {}
        return out

    birth_map = _skill_birth_map()

    def _skill_age(name: str) -> datetime | None:
        """skill 创建时间：git 首次提交优先，回退 birthtime，均不可得返回 None（不豁免）。"""
        p = skills_home / name
        if name in birth_map:
            return birth_map[name]
        try:
            r = subprocess.run(
                ["git", "-C", str(skills_home), "log", "--diff-filter=A", "--format=%at",
                 "--", name],
                capture_output=True, text=True, timeout=5)
            stamps = [ln.strip() for ln in r.stdout.splitlines() if ln.strip()]
            if stamps:
                return datetime.fromtimestamp(int(stamps[-1]))
        except Exception:
            pass
        try:
            st = p.stat()
            bt = getattr(st, "st_birthtime", None)
            return datetime.fromtimestamp(bt if bt is not None else st.st_mtime)
        except OSError:
            return None

    registered = sorted(p.name for p in skills_home.iterdir()
                        if p.is_dir() and p.name not in ("_shared", "delegate"))
    fresh = {s for s in registered if (a := _skill_age(s)) and a >= grace}
    cutoff = datetime.now() - timedelta(days=30)
    counts: dict[str, int] = {}
    for e in _jsonl_lines(_registry_invocations()):
        if not _within_window(e.get("ts", ""), cutoff):
            continue
        for k in (e.get("tool"), e.get("target")):
            if k:
                counts[k] = counts.get(k, 0) + 1
    # T112（2026-09-28）：第二观测通道——直读 SKILL.md 的弱信号（collect.py Read-SKILL，
    # 口径注：collect.py:178 既有约定「≥1 strong 或 ≥2 weak 才算活跃」在此落地为：
    # 弱信号 ≥2 即不判零触发；弱信号 1 次记「疑似活跃」仍入零触发名单但带标注。
    weak: dict[str, int] = {}
    weak = {s: 0 for s in registered}
    for e in _jsonl_lines(_registry_toolcalls()):
        if not _within_window(e.get("ts", ""), cutoff):
            continue
        t = e.get("tool") or ""
        if t != "Read-SKILL":
            continue
        tgt = e.get("target") or e.get("skill") or ""
        for s in registered:
            if s and (s in tgt or s in str(e.get("input", ""))):
                weak[s] = weak.get(s, 0) + 1
    silent = [s for s in registered
              if not counts.get(s) and weak.get(s, 0) < 2
              and s != "skill-evolution" and s not in fresh]
    weak_once = [s for s in silent if weak.get(s, 0) == 1]
    if not registered:
        return ["- ➖ skill-zero-invocation：skills/ 目录不可读，本轮不判定（fail-closed）"]
    lines = [f"- skill-zero-invocation 分母：登记 {len(registered)} 个（skill-evolution 计数结构性为零——"
             f"入口是脚本/hook 非 Skill 工具，已排除判定；落地宽限 14 天豁免 {len(fresh)} 个："
             f"{','.join(sorted(fresh)) or '无'}），窗口 30 天留痕 "
             f"{sum(c for s, c in counts.items() if s in registered)} 次"]
    if silent:
        anno = [f"{s}(弱信号1次)" for s in weak_once] or silent
        lines.append(f"- ⚠ skill-zero-invocation：{len(silent)} 个零触发（skill 静默悬空，只报不判；"
                     f"弱信号≥2 已按活跃豁免，T112 通道）：{','.join(anno)} → memory-governance 处置")
    return lines


def _jsonl_lines_tailed(path: Path, maxlen: int) -> list[dict]:
    """只读尾部 maxlen 行再解析（deque 不整载内存）；损坏行跳过。"""
    if not path.exists():
        return []
    out = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for ln in deque(f, maxlen=maxlen):
            try:
                out.append(json.loads(ln))
            except json.JSONDecodeError:
                continue
    return out


def compute_metrics(repo: Path, cutoff: datetime) -> list[str]:
    """三指标计算+阈值判定，返回报告行（≤16 行）。参考线单源 io-budgets.weekly_eval_refs。"""
    refs = io_budget("weekly_eval_refs") or {}
    recall_floor = float(refs.get("recall_floor") or 0)
    annoy_ceil = float(refs.get("annoy_ceil") or 0)
    convert_floor = float(refs.get("convert_floor") or 0)
    if not (recall_floor and annoy_ceil and convert_floor):
        print("[weekly-eval] weekly_eval_refs 不可读，指标全判 no_data（fail-closed）", file=sys.stderr)
        return [f"# 周评估报告（{datetime.now().strftime('%Y-%m-%d')}，窗口 {WINDOW_DAYS} 天）", "",
                "- ➖ 参考线配置不可读，本轮不判定（fail-closed）"]
    # 读取侧窗口预过滤（2026-09-16 进化轮消耗轴）：reflex-hooks.jsonl 1.53MB/9929 行
    # 且 ≈310 行/日无界增长——全量 read_text 再过滤是线性增长税。jsonl 按时间近似有序，
    # 尾部 5 万行保底（7 天窗 ≈2200 行，5 万=23 天余量），行序异常不丢样。
    # T83 根因修（20260927）：写侧真值=资产根 $HOME/.claude/.build（hooks 绝对写），repo 相对路径
    # 系 cwd 漂移幽灵（.claude/.claude 双副本同族）——与 :285 memory 聚合双路径读口对齐。
    hooks = _jsonl_lines_tailed(Path.home() / ".claude/.build/reflex-hooks.jsonl", maxlen=50000) \
        if (Path.home() / ".claude/.build/reflex-hooks.jsonl").exists() \
        else _jsonl_lines_tailed(repo / ".claude/.build/reflex-hooks.jsonl", maxlen=50000)
    recent = [e for e in hooks if _within_window(e.get("ts", ""), cutoff)]

    # R7 臂（2026-09-29）分母净化联动：recall 链新增 machine_skip（机器/无 session prompt，
    # 记事件不召回）与 repeat_hit（cooled 改记）事件——均非召回判定，留分母则净化形同虚设。
    # 分母收敛到 match/no_match 两判定事件（不改阈值逻辑，只改分母构成）。
    recall_rows = [e for e in recent
                   if e.get("hook") == "knowledge-recall"
                   and e.get("event") in ("match", "no_match")
                   and not (e.get("session_id") or "").startswith("test-")]
    matches = sum(1 for e in recall_rows if e.get("event") == "match")
    recall = matches / len(recall_rows) if recall_rows else None

    # 口径迁移（T117 裁决 2026-09-27）：reflex-check 实际只产 exempt-skip，
    # 判定事件在 reflex-correction（light/block-heavy）——分母词表随实流迁移
    check_rows = [e for e in recent if e.get("hook") == "reflex-correction"
                  and e.get("event") in ("block-heavy", "light")]
    blocks = sum(1 for e in check_rows if e.get("event") == "block-heavy")
    annoy = blocks / len(check_rows) if check_rows else None

    # 澄清转化分子 = reflex-clarify resolved 事件（2026-09-14 管道修复：reflex-check 检测
    # 澄清且窗口内有 ADR 沉淀时落 resolved；旧 corrections mtime 口径因目录恒空恒 0 假 ⚠，
    # 更早的 evolution-pool 口径同假——两次同根漂移后口径收敛到遥测事件，链路自证）。
    clarified = sum(1 for e in recent
                    if e.get("hook") == "reflex-clarify" and e.get("event") == "resolved")
    clarify_blocks = sum(1 for e in recent
                         if e.get("hook") == "reflex-clarify" and e.get("event") == "block")
    convert = clarified / clarify_blocks if clarify_blocks else None

    def _judge(ok: bool, detail: str) -> str:
        return f"- {'✅' if ok else '⚠'} {detail}"

    lines = [f"# 周评估报告（{datetime.now().strftime('%Y-%m-%d')}，窗口 {WINDOW_DAYS} 天）", ""]
    if recall is None:
        # T83 分母感知（20260927 战役包B，泛化 :599 先例）：窗口上游有活动而事件流 n=0
        # =hook 链悬空（recall 断流 7 天无人发现根因），与真无样本必须可区分。
        if recent:
            lines.append(f"- ⚠ 召回率：事件流 n=0 但窗口上游有活动（tool-calls {len(recent)} 行）→ knowledge-recall hook 链疑悬空，按链断处置非无样本")
        else:
            lines.append(f"- ➖ 召回率：无样本（n=0，上游亦无活动），不判定")
    else:
        lines.append(_judge(recall > recall_floor,
                            f"召回率 {recall:.0%}（{matches}/{len(recall_rows)}），参考线 >{recall_floor:.0%}"))
    if annoy is None:
        lines.append(f"- ➖ 打扰度：无样本（n=0），不判定")
    else:
        lines.append(_judge(annoy < annoy_ceil,
                            f"block 打扰度 {annoy:.0%}（block-heavy {blocks}/判定 {len(check_rows)}，T117 口径），参考线 <{annoy_ceil:.0%}"))
    if convert is None:
        lines.append(f"- ➖ 澄清转化：无样本（reflex-clarify block=0），不判定")
    elif clarify_blocks < 5:
        # strat-01（kpi-audit 2026-09-17）：小样本判定噪声主导（0/2 曾因 resolved 写入 bug 假恒 0），
        # 与 evolution-discipline.md:126 各 hook ≥10 行样本门槛同 philosophy，取 5 为周窗下限
        lines.append(f"- ➖ 澄清转化：样本不足（n={clarify_blocks}<5，{clarified}/{clarify_blocks}），不判定")
    else:
        lines.append(_judge(convert > convert_floor,
                            f"澄清转化 {convert:.0%}（{clarified}/{clarify_blocks}，resolved 事件口径），参考线 >{convert_floor:.0%}"))
    # 沉淀计数独立于转化率：分母为 0 时主控仍需知道沉淀动态
    lines.append(f"- corrections 沉淀 {clarified} 条（窗口内）；异常指标由主控读结论后处置，本脚本不做任何写操作（除报告本身）")
    lines.append(_knowledge_consumption(repo, cutoff))
    lines.extend(_memory_hit_recon(repo, cutoff))  # memory 命中聚合（淘汰依据读者面，只列不删）
    lines.extend(_sys01_recon(repo, cutoff, recent))  # sys-01 确认率对账（T8，只报不判）
    lines.extend(_security_recon(repo, cutoff))  # 安全对账：G2 拦截统计+G1 状态（T16，只报不判）
    # spawn 趋势（token-baseline.json 的对账口径：registry Agent 行计数）
    spawns: dict[str, int] = {}
    for e in _jsonl_lines(_registry_invocations()):
        if e.get("tool") == "Agent" and e.get("target") and _within_window(e.get("ts", ""), cutoff):
            spawns[e["target"]] = spawns.get(e["target"], 0) + 1  # 回访 M1：按 ts 过滤窗口，此前是终身累计冒充周数据
    if spawns:
        top = max(spawns, key=spawns.get)
        lines.append(f"- spawn 趋势：窗口内 {sum(spawns.values())} 次，最重 {top}×{spawns[top]}（对账 token-baseline.json）")
        # self_evolution_round 预算复测面（io-budgets 同名单源；审计/对抗类=按目标名归类估算）
        cad = io_budget("self_evolution_round") or {}
        audit_names = [t for t in spawns
                       if any(p in t for p in ("pcf-", "review-", "devils", "audit-", "exec-json-fixer"))]
        audit_share = sum(spawns[t] for t in audit_names) / sum(spawns.values())
        raw = cad.get("audit_class_share_max")
        # 回访 M1：阈值兼收数值与百分号字符串（"40%"），否则⚠永不发射成装饰
        try:
            share_max = float(str(raw).rstrip("%")) / 100 if "%" in str(raw) else (float(raw) if raw is not None else None)
        except (ValueError, TypeError):
            share_max = None
        lines.append(f"- 消耗审计对照：窗口 spawn 总 {sum(spawns.values())}（单轮上限 {cad.get('max_spawns_per_round','未设')}）；"
                     f"审计/对抗类占比 {audit_share:.0%}（线 ≤{raw if raw is not None else '未设'}）"
                     + (" ⚠ 超线" if share_max is not None and audit_share > share_max else ""))
    lines.extend(_g4_recon(repo, cutoff))  # G4 对账：spawn model 留痕率 + 工具失败/重试率（只报不判）
    lines.extend(_skill_zero_invocation_recon(repo))  # skill 静默悬空对账（议题B 轮2，只报不判）
    lines.extend(_escalation_recon(repo, cutoff))  # model-tier 护栏对账：零数据源即登记缺口
    lines.extend(_mcp_recon(repo, cutoff))  # 检索预算读口（retrieval_budget 键——只报不判）
    # 指针可达性抽查（evo-campaign-20260916 采纳项 6，只报不判）：高频引用文件
    # 抽 4 个 grep 实存性，防「裁决指针悬空」（假清偿同型）——抽样式非全量，成本毫秒级。
    asset = Path.home() / ".claude"
    # T61-C8 补强（2026-09-26）：原仅 v.exists() 存在性，存在但空壳/换内容不报——
    # 加关键词抽验（in 存在即过；读失败按缺失计，不中断周报）
    probes = {
        "KNOWLEDGE": (asset / "decisions/KNOWLEDGE.md", "决策"),
        "BLUEPRINT": (asset / "BLUEPRINT.md", "adas-assist"),
        "signal-tiers": (asset / "skills/_shared/signal-tiers.json", "tier"),
        "io-budgets": (asset / "skills/_shared/io-budgets.json", "max_items"),
    }
    missing = []
    for k, (v, kw) in probes.items():
        try:
            if not v.exists() or kw not in v.read_text(encoding="utf-8", errors="replace"):
                missing.append(k)
        except OSError:
            missing.append(k)
    lines.append(f"- 指针可达性抽查：{len(probes) - len(missing)}/{len(probes)} 在位"
                 + (f"；缺失 {missing}（只报不判，周批消化）" if missing else ""))
    # 升 main 次数对账（批次二项 3 后半，只读不判定）：Agent 事件带 model 字段者计数。
    # 字段 2026-09-16 起才有——旧数据无该字段，行打印分母声明口径起始日，不判达标。
    inv = _jsonl_lines(_registry_invocations())
    agent_rows = [e for e in inv if e.get("tool") == "Agent"]
    modeled = [e for e in agent_rows if e.get("model")]
    if agent_rows:
        lines.append(f"- 升 main/显式路由对账：Agent {len(agent_rows)} 次，显式 model {len(modeled)} 次"
                     f"（字段自 2026-09-16 起采集，此前无据）")
    # 留痕存在性（KPI #2 扩面子指标，kpi-campaign 勘误 2026-09-17）：依赖主控自律
    # 写行的机械判据必先失效（model 86/533、战役 spent 恒 0 三例同构），缺失率只报
    # 不判，连续两周上行才提示模板回炉
    _entry_tools = [e for e in inv if e.get("tool") in ("evolve", "kpi-re")]
    _no_tier = sum(1 for e in _entry_tools if not (str(e.get("target", "")).startswith("S") or e.get("tier") or e.get("effort")))
    if _entry_tools:
        lines.append(f"- 留痕存在性：模式入口行 {len(_entry_tools)} 条，档位/effort 标识缺失 {_no_tier} 条"
                     f"；全量 model 缺失 {sum(1 for e in inv if not e.get('model'))}/{len(inv)}")
    # effort-trace 留痕计数（model-governance §5a 勘误配套，2026-09-19）：只报存在
    # 性计数不做分布回填判定（采集端 10 天仅 1 条，样本远不足）；<10 尾注拦截误回填。
    _n_trace = sum(1 for e in inv if e.get("tool") == "effort-trace")
    lines.append(f"- effort-trace n={_n_trace}"
                 + ("（样本不足，勿据此回填分布）" if _n_trace < 10 else ""))
    # baseline-gap 生产者（效果验证协议回填义务）：expect 非空且 measured 空的项计数
    try:
        base = json.loads(_baseline_path().read_text(encoding="utf-8"))
        pending = [o.get("id", "?") for o in base.get("optimizations", []) if o.get("expect") and not o.get("measured")]
        v2 = [a.get("id", "?") for a in base.get("v2_round", {}).get("actions", [])
              if a.get("state", "").startswith("done") and a.get("measured") is None and a.get("probe") is None]
        if pending or v2:
            lines.append(f"- ⚠ baseline-gap：measured 未回填 {len(pending) + len(v2)} 项（{','.join(pending + v2)}）→ effect-governance 处置")
    except Exception:
        pass
    # channel-matrix-recheck marker 消费型门（议题5 收口，2026-09-19）：channel-matrix
    # 四分诊在 WebSearch 配额耗尽期落地，成功臂未满配额复测——到期且未 touch
    # .channel-recheck-done 前每周提示，⚠ 触发（配额恢复列出五项复验面）并 touch
    # marker 后不再报。
    _recheck_marker = repo / ".claude/.build/.channel-recheck-done"
    if datetime.now().date() >= datetime(2026, 9, 30).date() and not _recheck_marker.exists():
        _qst, _why = _websearch_quota_reset()
        if _qst == "recovered":
            lines.append("- ⚠ channel-matrix-recheck：WebSearch 配额已恢复 → 五项复验面："
                         "①WebSearch vs fetch 三域成功率 ②四分诊条目1 满配额臂重测 "
                         "③检索通道故障态 ④伪文本门误杀率 → 复验后 touch "
                         ".claude/.build/.channel-recheck-done")
        else:
            lines.append(f"- ➖ channel-matrix-recheck：WebSearch 配额未确认恢复（{_why}），"
                         "顺延下周复测（一次性门，恢复即触发，不硬造探测）")
    # 战略对账行（蓝图 §四预警机制，实施 6）：超线即发 strategy-review-due 信号，
    # 主控按 signal-tiers mid 档批量确认；分母打印防零信号假通过；阈值缺失判 no_data。
    chk = _strategy_check(repo)
    if chk is None:
        lines.append("- ➖ 战略对账：strategy_review 阈值不可读，本轮不判定（fail-closed）")
    else:
        breaches, n_meta, n_proj, n_meta_adr, n_pending = chk
        lines.append(f"- {'⚠ strategy-review-due：' if breaches else '✅ 战略对账：'}分母 skill={n_meta}+{n_proj} metaADR={n_meta_adr} PENDING={n_pending}"
                     + (f" → 超线：{';'.join(breaches)}（主控治理处置）" if breaches else "（未超线）"))
    # 联审到期信号（部门交叉审查，evolution_cadence.joint_review_window_days 单源）：
    # 到期才进报告；执行后主控跑 --joint-review 重置锚（消费即重置，防漂移堆积）
    # V2-1 死信告警·日档面（2026-09-27 落地）。本行只盯 evolution-daily.log mtime>2d
    # （日档串联程静默死）。
    # 已知局限（原候选自记）：告警者与被告警者同宿主，兜底须靠用户读周报这一外通道。
    try:
        dl_mtime = (repo / DAILY_LOG).stat().st_mtime
        dl_stale_days = (datetime.now().timestamp() - dl_mtime) / 86400
    except OSError:
        dl_stale_days = None
    if dl_stale_days is not None and dl_stale_days > 2:
        lines.append(f"- ⚠ dead-letter：日档日志 {dl_stale_days:.0f} 天未更新（夜批链疑静默死）→ 查 launchd com.nan.adas-assist-evolution.err 与 daily-archive.py，修复前本报告其余日档口径全部存疑")
    joint_due, joint_days = _joint_due(repo)
    if joint_due:
        lines.append(f"- ⚠ joint-review-due：部门联审到期（>{joint_days} 天未审）→ 触发词「部门联审/交叉审查」执行，审后 --joint-review 重置锚")
    # 进化批待办（2026-09-27 职能部门进化完善批，ADR evolution-cadence-tiers 追加节4）：
    # 本轮报告存在超线 ⚠ 信号且 evolution-batch.marker 缺失/早于本周锚 → 提示主控消费
    # 周报时跑 /evolve all（L2，自动消化限 low/mid，High 落 PENDING）；主控消化后跑
    # --evolution-batch 重置锚（消费即重置，joint-review 同构）。与后台分析段分工：
    # 分析段=诊断，本行=消化动作，同一信号不双消费。
    batch_marker = asset_claude() / ".build" / "evolution-batch.marker"  # T88 同病收锚（2026-09-27）
    overline = any("⚠" in ln for ln in lines)
    batch_stale = True
    if batch_marker.exists():
        try:
            batch_stale = datetime.fromtimestamp(batch_marker.stat().st_mtime).date() < _week_anchor(datetime.now())
        except OSError:
            pass
    if overline and batch_stale:
        lines.append("- ⚠ evolution-batch-due：超线信号在册且本周期进化批未消化 → 主控消费周报时跑 `/evolve all`（L2；low 自动/mid 批量确认/High 落 PENDING），审后 --evolution-batch 重置锚")
    # 外参节律待办（同批追加节5）：last-external-action.marker mtime 超 7 天 → 外参扫描
    # 待办行；执行者=下次会话主控（/evolve 状态 或 /evolve 外参），执行后 touch marker。
    ext_marker = asset_claude() / ".build" / "last-external-action.marker"  # T88 同病收锚（2026-09-27）
    ext_age = None
    if ext_marker.exists():
        try:
            ext_age = (datetime.now().timestamp() - ext_marker.stat().st_mtime) / 86400
        except OSError:
            pass
    if ext_age is None or ext_age > 7:
        ext_note = "从未记录" if ext_age is None else f"{ext_age:.0f} 天未执行"
        lines.append(f"- ➖ external-scan-due：外参扫描待办（{ext_note}）→ 下次会话主控跑 `/evolve 外参`（内建 WebSearch 如可用，否则跳过），执行后 touch last-external-action.marker")
    # 观测行块（2026-09-14 三方向进化轮 low 档消化：全部只读，超线仅标注不判罚）
    pool = _jsonl_lines(repo / ".claude/.state/evolution-pool/evolution-records.jsonl")
    # 嵌套路径修复（2026-09-27 环节轮 R2）：schema 实测 status 嵌套于 evolution_action
    # （0/56 顶层），原顶层读法使待验证行恒 0——39 条积压对周报不可见；保留顶层回退兼容
    _pool_status = lambda e: (e.get("evolution_action") or {}).get("status") or e.get("status")
    pend_pool = [e.get("event_id", "?") for e in pool if _pool_status(e) == "pending_validation"]
    if pend_pool:
        # ⚠ 前缀（2026-09-27 正向F1）：无前缀行被异常行前置截断规则排到队尾，
        # 39 条积压对主控不可见——积压可见性优先级高于普通行
        lines.append(f"- ⚠ evolution-pool 待验证 {len(pend_pool)} 条（{','.join(pend_pool[:3])}）→ 统筹批次/联审议程消化")
    # 消化率对侧硬指标（T112 落地，2026-09-27）：积压可见≠消化可见——按周统计
    # status 流转至 validated/precipitated 的条数，与待验证行成对出现，防「单向流入」静默化
    _digest = [e for e in pool
               if _pool_status(e) in ("validated", "precipitated")
               and _within_window(str(e.get("timestamp", ""))[:19].replace("T", " "), cutoff)]
    lines.append(f"- {'⚠' if not _digest and pend_pool else '➖'} evolution-pool 按周消化 {_digest and len(_digest) or 0} 条"
                 f"（validated/precipitated，窗口 {WINDOW_DAYS}d）——消化为 0 且积压在册=闭环单向流入信号")
    lines.extend(_pool_backlog_age_lines())  # R7 臂：教训池积压 age 中位（只报不判）
    try:
        adj = json.loads((Path.home() / ".claude/.state/adjudicated-signals.json").read_text(encoding="utf-8"))
        obs = {k: v for k, v in adj.items() if v.get("verdict") == "观察"}
        if obs:
            keys = "; ".join(f"{k}（裁决 {v.get('date','?')}）" for k, v in list(obs.items())[:2])
            cur = f"当前 metaADR={chk[3]} BACKLOG待办={chk[4]}" if chk else "当前计数见 strategy 对账行"
            lines.append(f"- ⚠ 观察项复评：{keys} → {cur}，复评结论留人工")
    except Exception as _e:  # 留痕批：sidecar 被误删时观察项整节静默消失（B2-7）
        print(f"[weekly-eval] 观察项 sidecar 读取失败：{_e}", file=sys.stderr)
    inj = [e for e in recent if e.get("hook") == "session-start"]
    throttled = sum(1 for e in inj if e.get("event") == "pending-throttled")
    if inj:
        lines.append(f"- session-start 注入 {len(inj)} 次（节流命中 {throttled}）——digest 节流生效性对账行")
    daily_log = repo / DAILY_LOG
    if daily_log.exists():
        try:
            n_breach = len({ln[:10] for ln in daily_log.read_text(encoding="utf-8").splitlines()
                            if ln[:10] >= cutoff.strftime("%Y-%m-%d") and "breach=yes" in ln})  # 回访 L6：按日去重，同日双跑不高估
            if n_breach:
                lines.append(f"- ⚠ 日档连续超线 {n_breach} 天（窗口内）→ 明细 evolution-daily.log")
        except OSError:
            pass
    return lines


def _pool_backlog_age_lines() -> list[str]:
    """R7 臂（2026-09-29）新增行：evolution-pool 教训条目积压 age 中位数（只报不判）。
    依据：待验证 ~40 条 vs 周消化 ~1 条，水位无 deadline 压力——需要 age 分布才能判
    积压是「近期正常堆积」还是「陈年死库存」。条目日期取所在 `## YYYY-MM-DD` 节标题
    （行内无独立日期字段，节标题即批次日期），age=距今天数。fail-open 异常退化缺口行。"""
    try:
        import statistics
        ages: list[float] = []
        for f in sorted((Path.home() / ".claude/.state/evolution-pool").glob("lessons-*.md")):
            sec_date = ""
            for ln in f.read_text(encoding="utf-8", errors="replace").splitlines():
                if ln.startswith("## "):
                    m = re.search(r"(\d{4}-\d{2}-\d{2})", ln)
                    sec_date = m.group(1) if m else sec_date
                elif ln.strip().startswith("- ") and sec_date:
                    ages.append(max((datetime.now() - datetime.strptime(sec_date, "%Y-%m-%d")).days, 0))
        if not ages:
            return ["- ➖ evolution-pool 积压 age：lessons 条目 n=0 或无可解析节日期，不判定"]
        ages.sort()
        return [f"- ➖ evolution-pool 积压 age：条目 {len(ages)} 条，age 中位 {statistics.median(ages):.0f} 天"
                f"（p90 {ages[int(len(ages)*0.9)-1]:.0f}/最老 {ages[-1]:.0f}，只报不判）"]
    except Exception as e:  # noqa: BLE001 — fail-open
        return [f"- ➖ evolution-pool 积压 age：读数失败（fail-open，{type(e).__name__}）"]




def _mcp_recon(repo: Path, cutoff: datetime) -> list[str]:
    """检索预算读口（retrieval_budget 键读者接线）：
    tool-calls.jsonl 全通道口径（"tool": "mcp__ 前缀过滤+WebSearch/WebFetch 内建），
    统一计数只报不判——错误返回不计数（ddg VQD 8 连败实证）；kill=连续 90 天零调用。
    数值锚与观察期字段单源=io-budgets.json retrieval_budget。"""
    _ = repo
    root = Path.home() / ".claude"
    tc = root / "skills/skill-evolution/registry/tool-calls.jsonl"
    rows = [e for e in _jsonl_lines(tc)
            if _within_window(e.get("ts", ""), datetime.now() - timedelta(days=WINDOW_DAYS))
            and (str(e.get("tool", "")).startswith("mcp__")
                 or e.get("tool") in ("WebSearch", "WebFetch"))]
    err = sum(1 for e in rows if e.get("success") == "fail")
    try:
        rb = json.loads((root / "skills/_shared/io-budgets.json").read_text(encoding="utf-8")).get("retrieval_budget", {})
        qline = (f"quick 线 {rb.get('quick', {}).get('searches_max', '?')} 搜/{rb.get('quick', {}).get('fetches_max', '?')} 取、"
                 f"full 线 {rb.get('full', {}).get('searches_max', '?')} 搜/{rb.get('full', {}).get('fetches_max', '?')} 取（宿主显式）")
    except Exception:
        qline = "retrieval_budget 单源读失败（TIGHT 兜底：数值以 io-budgets 为准）"
    lines = [f"- 检索预算读口（retrieval_budget 全通道）：窗口调用 {len(rows)}（错返 {err} 不计数），"
             f"{qline}——只报不判，累计≥20 后定档"]
    if rows:
        from collections import Counter as _C
        top = _C(e["tool"] for e in rows).most_common(3)
        lines[-1] += f"；分布 {top}"
    return lines


def _norm_model_tier(raw) -> str:
    """T94 收敛（2026-09-28）：实现迁 shared_state.norm_model_tier 单源，
    本壳保留调用点兼容；原镜像副本删除（collect.py 同批切换）。"""
    from shared_state import norm_model_tier
    return norm_model_tier(raw)


def _escalation_recon(repo: Path, cutoff: datetime) -> list[str]:
    """升 main 次数 / 同题失败计数两项只读对账（model-tier 护栏对账项）。
    2026-09-20 读者重写：原「均无 model 档位字段」断言过时——invocations
    自 2026-09-16 起 model 字段实际在写（窗口覆盖 ~49%），effort-trace 事件即升档
    留痕（model-governance §5 预注册机制，collect.py:180 唯一写入点）。同题失败用
    「同 target 窗口内 success=fail 后重复调用」代理口径（无题/session id，粒度降
    一级如实标注）。分母=扫描记录数，防零信号假通过（零结果必须打印分母）。"""
    inv = [e for e in _jsonl_lines(_registry_invocations()) if _within_window(e.get("ts", ""), cutoff)]
    n_fv = sum(1 for e in _jsonl_lines(repo / ".claude/.state/finish-verdicts.jsonl")
               if _within_window(e.get("ts", ""), cutoff))
    n_model = sum(1 for e in inv if e.get("model"))
    n_trace = sum(1 for e in inv if e.get("tool") == "effort-trace")
    # 主模型路由：_norm_model_tier 归一化口径（T3b 2026-09-20，读者侧归一，采集侧不动）
    tier = {}
    for e in inv:
        t = _norm_model_tier(e.get("model"))
        tier[t] = tier.get(t, 0) + 1
    n_main = tier.get("main_only", 0) + tier.get("main_plus_exec", 0)
    n_unattr = tier.get("unattributed", 0)
    tier_str = "/".join(f"{k}={tier.get(k, 0)}" for k in
                        ("main_only", "main_plus_exec", "exec_only", "unattributed"))
    # 同题失败代理：按 target 聚合 success=fail 的调用，fail 后同 target 再现即「同题≥2」上界近似
    tgt_fail: dict = {}
    for e in inv:
        if e.get("success") == "fail":
            tgt_fail[e.get("target") or "-"] = tgt_fail.get(e.get("target") or "-", 0) + 1
    n_tgtfail = sum(1 for t, c in tgt_fail.items() if c >= 2)
    cov_pct = f"{n_model * 100 // len(inv)}%" if inv else "0%"
    return [
        f"- ➖ 升 main 次数：model 字段覆盖 {n_model}/{len(inv)}（{cov_pct}，未归一 {n_unattr}），主模型路由行 {n_main}（归一化口径 {tier_str}），effort-trace 升档留痕 {n_trace} 条——归一化约定已落（weekly-eval._norm_model_tier，写法发散由 model-governance §5 推荐写法控制）→ 采集覆盖不足只报不判",
        f"- ➖ 同题失败计数（代理口径）：success 字段覆盖 {sum(1 for e in inv if e.get('success'))}/{len(inv)}，同 target fail≥2 计 {n_tgtfail} 个——无题/session id，粒度降一级；finish-verdicts({n_fv}) 侧无按题失败字段维持原缺口 → 覆盖不足段只报不判",
    ]


def _registry_invocations() -> Path:
    return Path.home() / ".claude" / "skills" / "skill-evolution" / "registry" / "invocations.jsonl"


def _registry_toolcalls() -> Path:
    return Path.home() / ".claude" / "skills" / "skill-evolution" / "registry" / "tool-calls.jsonl"


def _baseline_path() -> Path:
    return Path.home() / ".claude" / "skills" / "skill-evolution" / "registry" / "token-baseline.json"


def backfill(pairs: list[str]) -> int:
    """--backfill 机械回填：只写 measured 原始值，expect/state/回退留人工（契约见 docstring）。"""
    base_path = _baseline_path()
    try:
        base = json.loads(base_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 — 基线缺失/损坏属硬失败：回填写错文件比不写更糟
        print(f"[weekly-eval] token-baseline.json 不可读，回填终止：{exc}", file=sys.stderr)
        return 1
    # 三类候选定位：优化项 optimizations / v2_round.actions / 兜底按 id 全扫（嵌套结构演进容错）
    nodes = base.get("optimizations", []) + base.get("v2_round", {}).get("actions", [])

    def _apply(obj, iid: str, raw) -> bool:
        if obj.get("id") == iid and obj.get("expect"):
            obj["measured"] = raw  # 原始值原样写：字符串/数字不转换，裁决归 effect-governance
            return True
        return False

    done = 0
    for pair in pairs:
        iid, sep, raw = pair.partition("=")
        if not sep:
            print(f"[weekly-eval] 回填格式错误（须 id=value）：{pair}", file=sys.stderr)
            return 1
        if any(_apply(n, iid, raw) for n in nodes):
            done += 1
        else:
            print(f"[weekly-eval] 未回填（无此 id 或该 id 无 expect）：{iid}", file=sys.stderr)
    base_path.write_text(json.dumps(base, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[weekly-eval] 回填完成：本次写入 {done} 项（expect/回退判定未动，留人工）")
    return 0


ANALYSIS_MARKER = Path.home() / ".claude" / ".build" / "weekly-eval-analysis.marker"


def _model_analysis(lines: list[str], force: bool = False) -> list[str]:
    """Intelligence Plane 后台分析段（2026-09-13 用户裁决升级）。

    只对超线 ⚠ 项触发模型调用（无超线零调用——防无效调用原则）；模型路由
    不绑定具体型号（--model sonnet 走本机配置的执行模型，Skill 解耦纪律）。
    fail-closed：调用失败/超时/空输出 → 返回空列表，脚本段照常落盘（§4b 语义）。
    二级节流（红队 H1/H2 修复）：分析段用全局 marker 7 天一次——strategy/baseline-gap
    等超线内容是全局单源数据，多仓报告内容相同，按仓调用即预算翻倍；且主控不进场时
    报告每日重算，无此 marker 同一超线每天烧一次模型。force=用户主动豁免（§3.7
    立即执行），旁路节流但不 touch（不吞下一周期）。
    """
    warns = [ln for ln in lines if ln.startswith("- ⚠")]
    if not warns:
        return []
    cfg = io_budget("weekly_report") or {}
    max_lines = int(cfg.get("analysis_max_lines") or 0)
    if max_lines <= 0:
        return []  # 预算未定义=功能未启用，不内置兜底
    if not force and ANALYSIS_MARKER.exists():
        age = datetime.now().timestamp() - ANALYSIS_MARKER.stat().st_mtime
        if age <= WINDOW_DAYS * 86400:
            return []  # 节流期内：报告只含脚本段（上期分析已被主控消费或可见于历史报告）
    # 输入/输出双侧限长：输入防 ⚠ 行携带超长 id 列表打爆 prompt，输出防模型单行
    # 长答爆报告 token（行数限了行长没限等于没限——暴力测试实证）；截断项声明
    # 泛化归因（红队 L6：残缺 id 会诱发模型幻觉 id 回流主控）
    warns = [w[:200] + ("…(截断，只做泛化归因不得复述 id)" if len(w) > 200 else "") for w in warns]
    # 现状锚（2026-09-14 报告实证：仅喂 ⚠ 行致建议与同报告脚本段事实自相矛盾）——
    # 把同报告非超线事实行一并作 grounding，禁建议与事实冲突
    facts = [ln for ln in lines if ln.startswith("- ") and not ln.startswith("- ⚠")][:6]
    prompt = (
        "以下是 adas-assist 周评估报告的超线项。逐条给一行归因+一行建议，总计不超过"
        f" {max_lines} 行，每行以 '- ' 开头且不超过 120 字，禁止复述原文，禁止输出其他内容：\n"
        + "\n".join(warns)
        + "\n\n[现状锚·同报告脚本段事实] 建议不得与上述事实矛盾；与事实冲突时以事实为准并显式标注：\n"
        + "\n".join(facts)
    )
    try:
        # CLI 路径不硬编码：PATH 找不到时探测 npm-global 常见落点（cron 环境 PATH 精简）
        import shutil
        cli = shutil.which("claude") or str(Path.home() / ".npm-global" / "bin" / "claude")
        # 模型档单源化（2026-09-28 T111：原硬编码 "sonnet" 违 model-switch-linkage §3.4
        # 禁绑型号纪律，model-call-audit 首跑实锤）——改读 io-budgets night_run.model
        # 类别别名（settings env 映射承接），读失败回落 env 缺省映射（同款 fail 语义）
        try:
            _tier = json.loads((Path.home() / ".claude/skills/_shared/io-budgets.json").read_text(encoding="utf-8"))["night_run"]["model"]
        except Exception:
            _tier = os.environ.get("CLAUDE_CODE_SUBAGENT_MODEL", "sonnet")
        # 思考轻度控制（§3.7）：短指令+行数/字数硬上限+单轮禁工具（--max-turns 1，
        # 红队 M4：-p 模式模型仍可能自行多轮工具调用），不追加深度推理语境
        r = subprocess.run(
            [cli, "-p", "--model", _tier, "--max-turns", "1", prompt],
            # 根因：headless claude -p 归因调用连续 3 次 180s 整段超时（log 实证），
            # 分析段是增益非刚需 → fail-fast 降 30s，超时走既定 fail-closed 跳过
            capture_output=True, text=True, timeout=30,
        )
        if r.returncode != 0 or not r.stdout.strip():
            print(f"[weekly-eval] 模型分析段失败（fail-closed 跳过）：{r.stderr[:120]}", file=sys.stderr)
            return []
        out = [ln[:120] for ln in (l.strip() for l in r.stdout.splitlines())
               if ln.startswith("- ")][:max_lines]
        if not out:
            return []  # 全过滤=无有效分析，连标题段也不落盘（暴力测试⑦实证：空标题污染报告）
        return ["", "## 后台分析（自动生成，供主控消化参考）"] + out
    except Exception as exc:  # noqa: BLE001 — 分析段是增益不是刚需
        print(f"[weekly-eval] 模型分析段异常（fail-closed 跳过）：{exc}", file=sys.stderr)
        return []


def _daily_log(repo: Path) -> None:
    """日档落盘日志（evolution_cadence.daily_log 启用才写）：一行/日，零模型零注入。
    未到期时 cron 每日留下心跳：日期+PENDING 计数+超线有无+联审到期，供随时回查。"""
    cad = io_budget("evolution_cadence") or {}
    if not cad.get("daily_log"):
        return
    chk = _strategy_check(repo)
    breaches, n_pending = ([], 0) if chk is None else (chk[0], chk[4])
    joint_due, _ = _joint_due(repo)
    log = repo / DAILY_LOG
    try:
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open("a", encoding="utf-8") as fh:
            breach_note = 'yes:' + ';'.join(breaches) if breaches else 'no'
            fh.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M')} pending={n_pending} "
                     f"breach={breach_note[:120]} "  # 只留摘要防单行超长，明细见当日周报
                     f"joint={'due' if joint_due else 'ok'}\n")
    except OSError:
        pass  # 日档是增益不是刚需，写失败不影响主流程


def main(argv: list[str]) -> int:
    backfill_pairs: list[str] = []
    repos: list[str] = []
    force = False
    joint_reset = False
    batch_reset = False
    i = 0
    while i < len(argv):
        if argv[i] == "--backfill":
            i += 1
            while i < len(argv) and "=" in argv[i]:  # repo 路径不含 =，含 = 即回填对
                backfill_pairs.append(argv[i])
                i += 1
        elif argv[i] == "--force":
            force = True  # 用户主动豁免（§3.7 立即执行）：旁路节流，不 touch 任何 marker
            i += 1
        elif argv[i] == "--joint-review":
            joint_reset = True  # 联审已执行（触发词手动或到期自动）→ touch 重置双周锚
            i += 1
        elif argv[i] == "--evolution-batch":
            batch_reset = True  # 进化批已消化（主控跑 /evolve all 后）→ touch 重置周锚（2026-09-27）
            i += 1
        else:
            repos.append(argv[i])
            i += 1
    if backfill_pairs:
        return backfill(backfill_pairs)  # 回填与报告生成互斥：回填是人工触发的写动作，cron 路径不带参
    repos = [Path(a).resolve() for a in repos]
    if not repos:
        # docstring 承诺的 cwd 上溯（逆向审查 Med-5：子目录直跑曾静默跳过）
        repo = Path.cwd().resolve()
        while not (repo / ".claude").is_dir() and repo != repo.parent:
            repo = repo.parent
        # T118 修复（2026-09-27）：cwd 在资产根内直跑时上溯命中 ~/.claude
        # （其 .claude/ 幻影子目录致判真）→ pool 等读空得假 0。资产根惯例 repo=home，
        # 使 repo/.claude 即 ~/.claude 资产根；项目仓不受影响。
        if repo == Path.home() / ".claude":
            repo = Path.home()
        repos = [repo]
    now = datetime.now()
    cutoff = now - timedelta(days=WINDOW_DAYS)
    joint_done = False
    for repo in repos:
        if not (repo / ".claude").is_dir():
            print(f"[weekly-eval] 跳过（非项目仓）：{repo}", file=sys.stderr)
            continue
        if joint_reset:
            joint = repo / JOINT_MARKER
            joint.parent.mkdir(parents=True, exist_ok=True)
            # 写入重置时间戳而非空 touch：marker 内容可追溯「何时消费过」（快审 M4）
            joint.write_text(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " joint-review consumed\n",
                             encoding="utf-8")
            print(f"[weekly-eval] 联审锚已重置：{joint}")
            joint_done = True
            continue
        if batch_reset:
            bm = asset_claude() / ".build" / "evolution-batch.marker"  # T88 同病收锚（2026-09-27）
            bm.parent.mkdir(parents=True, exist_ok=True)
            bm.write_text(datetime.now().strftime("%Y-%m-%d %H:%M:%S") + " evolution-batch consumed\n",
                          encoding="utf-8")
            print(f"[weekly-eval] 进化批锚已重置：{bm}")
            continue
        marker = repo / MARKER
        # 周批周日锚（evolution_cadence.weekly_anchor=sunday）：marker 日期早于本周日锚
        # 即到期；mtime 兜底 fail-open——marker 缺失/损坏按到期处理，信号链不断
        if not force and marker.exists():
            try:
                marker_day = datetime.fromtimestamp(marker.stat().st_mtime).date()
                if marker_day >= _week_anchor(now):
                    _daily_log(repo)  # 未到期：日档心跳一行后静默
                    continue
            except OSError:
                pass  # mtime 不可读 → 视为到期（fail-open）
        report = repo / REPORT
        report.parent.mkdir(parents=True, exist_ok=True)
        lines = compute_metrics(repo, cutoff)
        # 报告行数预算单源 io-budgets.weekly_report.max_lines；fail-closed=不写报告，
        # session-start 因报告缺失自然走「跑脚本生成」提醒，不内置行数常量
        wr_cfg = io_budget("weekly_report") or {}
        max_lines = int(wr_cfg.get("max_lines") or 0)
        if max_lines <= 0:
            print("[weekly-eval] io-budgets.weekly_report 不可读，跳过报告写入（fail-closed）", file=sys.stderr)
            _daily_log(repo)  # 回访 L6：配置故障周日档心跳不断链
            continue
        # 截断前异常优先重排（N1 截断吞警修复）：⚠/➖ 异常行 stable 前置，正常读数行排后
        # ——异常行永远落在 max_lines 线内，被截的只剩无信息损失的正常行。
        # 标题两行（# 周评估报告+空行）保持最前，段内相对顺序不变（stable 分区）。
        head, body = lines[:2], lines[2:]
        lines = head + [ln for ln in body if "⚠" in ln or "➖" in ln] \
            + [ln for ln in body if "⚠" not in ln and "➖" not in ln]
        # 分析段输入=截断后行（红队 M5：被 max_lines 截掉的 ⚠ 不存在报告中，
        # 分析它会产生幽灵超线项误导主控）；分析段不计入 max_lines（io-budgets note 明示）
        trimmed = lines[:max_lines]
        analysis = _model_analysis(trimmed, force)
        report.write_text("\n".join(trimmed + analysis) + "\n", encoding="utf-8")
        _daily_log(repo)  # 到期周也留心跳（快审 M2：超线周恰是最需要日档连续性的一周）
        if analysis:
            # 分析段成功产出才落节流纪元（C1 修复：marker 原先只读不写，节流承诺落空
            # ——超线常态下每天 cron 各烧一次模型调用）；失败/空产出不 touch，下期重试
            ANALYSIS_MARKER.parent.mkdir(parents=True, exist_ok=True)
            ANALYSIS_MARKER.touch()
            # 次数计量（模型治理审计建议）：一行/次复用既有 jsonl 消费链；token 量不采
            # （§3.7 已双层节流+仅超线触发，为量建采集违反不为假设建机制）
            try:
                # 遥测随报告 repo 落盘（与 reflex-hooks 其他事件同文件，周评估窗口口径一致）
                with (repo / ".claude/.build/reflex-hooks.jsonl").open("a", encoding="utf-8") as fh:
                    fh.write(json.dumps({"ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "hook": "model-analysis",
                                         "event": "ok", "out_lines": len([l for l in analysis if l.startswith("- ")])},
                                        ensure_ascii=False) + "\n")
            except OSError:
                pass  # 遥测失败不影响报告主流程
        print(f"[weekly-eval] 报告已产出：{report}")
    if joint_reset and not joint_done:
        print("[weekly-eval] --joint-review 未重置任何仓（无非项目仓落点）", file=sys.stderr)
        return 1  # 调用方必须感知重置未生效（逆向审查 Med-5）
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
