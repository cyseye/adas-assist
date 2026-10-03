#!/usr/bin/env python3
"""session-review.py — Stop 钩子：会话结束时扫描多类信号，写 PENDING 建议清单。

自发现引擎（半自动：自动扫信号产建议清单，触发 skill 仍需用户确认）。
扫三类信号源：
  (1) verify-report.json：读 verification.status/must_fix_count/unresolved（修 schema bug：
      原读顶层 status/must_fix/handoff，真实嵌套在 verification.* 下，handoff 产物不存在，
      三元全 False 永远扫不到信号 → PENDING 从不生成。此为修复根因。）
  (2) report.evolution.json：verdict 非持平(下降/提升)→ 评估→改进断环补 follow-up
      （evaluated-but-never-evolved：评估产出无 follow-up 的断环在此补）
  (3) skill-evolution/registry/invocations.jsonl 全局调用日志 × skill 进化/验证/冷窗留痕：
      零调用+无 EVOLUTION+无 verify+目录 30 天冷窗→死 skill；低频/高频无 EVOLUTION→待评估
      （per-skill registry 退役：collect 全局单轨才是真值，覆盖度判定以它为唯一数据源）
  (4) decision-verify/data/red-blue-dataset.jsonl：条目产物失联/基线超期未刷新
      → 建议 decision-verify 重验或确认清理（只标记不删行，删条目属高风险须用户确认）
  (5) ADR 库治理族：数量超限（全局>24/单域>18）+ 30 天层级累进复核（晋升/维持/归档
      三选，非直接清理）+ frontmatter/KNOWLEDGE 单源索引/死链一致性 + 经验汇总到期（>90 天且
      meta 域新增≥3）→ 建议 decision-record
  (6) 校准族（2026-08-24 接入：已采数据此前无消费方，分级判定不在进化闭环内）：
      finish-verdicts 档位分布 / collect 全局调用日志触发语料 / reflex-hooks
      召回质量 → 事实汇报级信号，建议 skill-evolution 评估校准（升降档/补词
      结论留用户裁决，本脚本不做机器结论）
  （原 (7) 工具密集会话信号已退役 2026-08-31，用户批准：阈值 400 实证 12/12 条
      同质无区分度，且 gate-rules 明确执行编排型不接入 → 无真消化路径）
  (8) 地图计数族（2026-09-03 接入）：README/KNOWLEDGE 尾注声明计数 vs 目录实测——窄版
      白名单锚点（固定句式 + HTML 计数注释，日期锚快照句不对账），低风险机械回填

PENDING 按信号类型建议触发对应单 skill（不全链 agentos-loop），下次会话主控提示用户确认。
约束：Stop hook 只能跑命令不能调 skill，故只产建议清单，执行需用户确认
（守 skill-evolution「不自动改 skill」克制哲学——自发现自动，自改进半自动）。
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
import os

# 剪枝遍历（2026-09-25 提升轮 R5 实测补丁）：PROJ=home 全盘时 repo.rglob 走 24 万
# 目录项 22s+（Stop hook 实测瓶颈 99% 在此）。剪枝跳过大体积/无关子树后 0.5s，
# 命中与全树真实信号零差（.Trash 垃圾命中顺带排除）。只用于大根扫描，勿替代
# 小目录（ASSET/skills 级）下的 rglob 语义。
_SCAN_SKIP = {
    "Library", ".Trash", ".git", "node_modules", ".venv", "venv", "target",
    "dist", "__pycache__", "DerivedData", ".npm", ".cache", ".cargo",
    ".colima", "colima", ".docker", "docker", "go", "pkg",
}


def _pruned_rglob(root: Path, name: str) -> list[str]:
    hits: list[str] = []

    def walk(d: str) -> None:
        try:
            entries = list(os.scandir(d))
        except (PermissionError, FileNotFoundError, NotADirectoryError):
            return
        for e in entries:
            try:
                if e.is_dir(follow_symlinks=False):
                    if e.name not in _SCAN_SKIP:
                        walk(e.path)
                elif e.name == name:
                    hits.append(e.path)
            except OSError:
                continue

    walk(str(root))
    return hits

# memory 层结构对账（memory-governance skill，跨目录 importlib 加载）：异常时置 None 防主扫描链炸
try:
    import importlib.util as _ilu
    _spec = _ilu.spec_from_file_location(
        "scan_memory",
        Path.home() / ".claude" / "skills" / "memory-governance" / "scripts" / "scan-memory.py")
    scan_memory = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(scan_memory)
except Exception:
    scan_memory = None

# compact 逐字引用观察信号（T-B2 2026-09-29，跨目录 importlib 加载同 scan_memory
# 形态）：词表单源 CLAUDE.md Compact instructions 逐字保留车道；fail-open 缺失降级
# 为 None 主扫描链不炸
try:
    _spec_cps = _ilu.spec_from_file_location(
        "check_compact_survival",
        Path(__file__).resolve().parent / "check-compact-survival.py")
    check_compact_survival = _ilu.module_from_spec(_spec_cps)
    _spec_cps.loader.exec_module(check_compact_survival)
except Exception:
    check_compact_survival = None

# 共享状态读写唯一通道：PENDING 写入走 flock+原子写，防多 session 并发 Stop 互覆
from shared_state import asset_claude, atomic_write, count_jsonl_lines, data_claude, flock_ctx

# 双根（迁移 ~/.claude 后）：ASSET=~/.claude 单源资产（11 元层 skill/_shared/
# decisions/agents/README）；PROJ=项目根（32 harness skill/standards/运行时数据）。
# 扫描器保持 repo/".claude" 惯例——资产侧传 home（home/.claude 即资产根）可零改写复用；
# 跨仓件（verify 报告/覆盖度/超线/触发语料/git 留痕桥接）双根并扫合并。
ASSET = asset_claude()
ASSET_REPO = ASSET.parent  # home：使 ASSET_REPO/".claude" == ~/.claude，复用扫描器惯例
PROJ = data_claude().parent
PENDING = ASSET / "decisions" / "postmortems" / "PENDING.md"
# 裁决感知 sidecar（魔鬼天团 2026-09-13 裁决：整文件重写会覆盖主控已裁决信号，
# 复发率 22% 成闭环拖累；sidecar 为唯一裁决单源，PENDING 仅派生展示。
# fail-loud：sidecar 损坏时跳过重写并报错，禁止降级为全量重报制造假闭环）
ADJUDICATED = ASSET / ".state" / "adjudicated-signals.json"
# ADR 双域目录（dual-domain-taxonomy 2026-09-03：元层工程 meta + 数据业务共性 data，
# 数据领域细分由 frontmatter domain + KNOWLEDGE tag 承载；data 暂空不建目录，
# pathlib glob 对缺失目录返回空迭代器天然兼容，计数/扫描按双域遍历）
_ADR_DOMAINS = ("meta", "data")
# 治理阈值：单源=skills/_shared/signal-tiers.json §adr_governance（T77 收编 2026-09-27，
# 条款源 adr-archive-layer-reinstate-20260925）；读取失败回退同值不降级（不静默改口径）
# 信号线非冻结线——超限触发治理复核，不为凑上限强行归档
def _load_adr_limits():
    try:
        tiers = json.loads((ASSET / "skills" / "_shared" / "signal-tiers.json").read_text(encoding="utf-8"))
        return int(tiers["adr_governance"]["limit_global"]), int(tiers["adr_governance"]["limit_per_domain"])
    except Exception as _e:
        print(f"[session-review] signal-tiers 读取失败，回退缺省阈值：{_e}", file=sys.stderr)
        return 24, 18

_ADR_LIMIT_GLOBAL, _ADR_LIMIT_PER_DOMAIN = _load_adr_limits()


def _is_pass_status(status) -> bool:
    """通过类 status：pass / pass_with_flags / pass_with_minor（含 MINOR 的通过态，非缺陷）。

    fixable / critical / fail 等非通过。None 视为无 status（仅由 must_fix 判定）。
    用前缀匹配兼容未来 pass* 变体——避免重蹈覆辙：曾因硬编码 {None,'pass','PASS'}
    把 design/decision-verify 的 pass_with_flags 通过态误报为 decision-improve 缺陷信号
    （同根于 pass+unresolved 误报的复发，见 postmortem 0002）。
    """
    if status is None:
        return True
    if not isinstance(status, str):
        return False
    return status.lower().startswith("pass")


def scan_verify_reports(repo: Path) -> list[dict]:
    """扫所有 verify-report.json，按真实 schema 提取信号。

    schema（核对 decision-consensus/verify-report.json + 模板）：status/must_fix_count
    嵌套在 verification.* 下，顶层无 status/must_fix/handoff。原实现读顶层导致
    三元全 False 永远扫不到信号——此为修复。
    """
    signals: list[dict] = []
    for vr in map(Path, _pruned_rglob(repo, "verify-report.json")):
        try:
            data = json.loads(vr.read_text(encoding="utf-8"))
        except Exception:
            continue
        # 跳过模板占位（templates 下无 verification 实质内容）。
        # isinstance 防御：verification 若被写成数组（魔鬼测试实证），`or {}` 只挡
        # None 挡不住真值列表，直接 .get 会 AttributeError 且 main 无兜底会崩 hook
        ver = data.get("verification")
        if not isinstance(ver, dict):
            ver = {}
        status = ver.get("status") or data.get("status")
        must_fix = ver.get("must_fix_count")
        if must_fix is None:
            must_fix = data.get("must_fix_count") or data.get("must_fix") or 0
        unresolved = data.get("unresolved") or ver.get("unresolved") or []
        fix_rate = (data.get("defect_rates") or {}).get("fix_rate")
        # 已 PCF 裁决接受且无 must_fix → 已闭环，不再当信号。
        # 否则用户已决定不修的项会被反复误报（accept_with_flags 后仍因 status≠pass 被报）。
        pcf = (data.get("pcf_decision") or ver.get("pcf_decision") or "").lower()
        if pcf.startswith("accept") and not must_fix:
            continue
        # 已通过且无必修项 → 非缺陷，跳过。此时 unresolved 是开放项（待业务确认/待联动外部规范），
        # 不属缺陷信号。（修：原 `or len(unresolved)` 把 pass+must_fix=0 的开放项误报为缺陷噪音，
        # 如 verify status=pass+unresolved=3 被反复建议 decision-improve。）
        if _is_pass_status(status) and not must_fix:
            continue
        # 信号判定：非 pass、有 must_fix、fix_rate 偏低（unresolved 随缺陷出现，不单独触发）
        is_signal = (
            (not _is_pass_status(status) and status is not None)
            or must_fix
            or (isinstance(fix_rate, (int, float)) and fix_rate < 0.7)
        )
        if is_signal:
            signals.append({
                "type": "verify",
                "report": str(vr.parent.relative_to(repo)),
                "status": status,
                "must_fix": must_fix,
                "unresolved": len(unresolved),
                "fix_rate": fix_rate,
                "suggest": "decision-improve",
            })
    return signals


def scan_evolution_reports(repo: Path) -> list[dict]:
    """扫 report.evolution.json，verdict 非持平→评估→改进断环补 follow-up。"""
    signals: list[dict] = []
    for er in map(Path, _pruned_rglob(repo, "report.evolution.json")):
        # 防御：report.evolution.json 是中间产物，结论沉淀 EVOLUTION.md 后应已清。
        # 若残留且已被处理（EVOLUTION.md mtime ≥ report mtime = 结论在 report 之后
        # 更新、已含本次）→ 跳过，避免 verdict≠持平 反复误报。用 mtime 而非"有无
        # EVOLUTION.md"——旧 EVOLUTION.md + 新未处理 report 共存时，仅看存在性会
        # 误跳过断环信号（report 新产出、尚未沉淀进 EVOLUTION）。
        skill_dir = er.parent.parent  # .build 的父 = skill 目录
        evolution_md = skill_dir / "EVOLUTION.md"
        if evolution_md.exists() and evolution_md.stat().st_mtime >= er.stat().st_mtime:
            continue
        try:
            data = json.loads(er.read_text(encoding="utf-8"))
        except Exception:
            continue
        verdict = data.get("verdict") or data.get("result") or ""
        if verdict and verdict != "持平":
            signals.append({
                "type": "evolution",
                "report": str(er.parent.relative_to(repo)),
                "verdict": verdict,
                "suggest": "skill-evolution",
            })
    return signals


def scan_skill_coverage(skills_dir: Path, registry: Path) -> list[dict]:
    """覆盖度检测：全局 collect 调用日志（唯一真值）× skill 进化/验证留痕。

    per-skill registry 已退役（collect 只写全局单轨，仅 7/42 有手工补录），
    旧口径下 31/42 skill 永不进死/冷/热判定——本函数改读全局日志，
    Skill 工具调用按 target 归集（Agent 调用 target 是 agent 名，不计入）。
    迁移后 skills_dir 按仓传入（资产仓/项目仓各扫各的），registry 恒为资产仓
    全局单轨（collect 随 skill-evolution 迁移，两仓 skill 的调用计数同源）。
    """
    signals: list[dict] = []
    if not skills_dir.is_dir():
        return signals
    exec_by_skill: dict[str, int] = {}
    weak_by_skill: dict[str, int] = {}
    n_strong = n_weak = 0
    for r in _iter_jsonl(registry):
        t, tg = r.get("tool"), r.get("target")
        if t == "Skill" and isinstance(tg, str):
            exec_by_skill[tg] = exec_by_skill.get(tg, 0) + 1
            n_strong += 1
        elif t == "Read-SKILL" and isinstance(tg, str):
            weak_by_skill[tg] = weak_by_skill.get(tg, 0) + 1
            n_weak += 1
    # 弱信号加权（魔鬼天团 2026-09-13 终裁）：Read≠执行（引用/评审也读），
    # 单次直读不计入；≥2 次独立直读才折算 1 次执行——治 91% 漏记不引入误活跃
    for name, w in weak_by_skill.items():
        if w >= 2:
            exec_by_skill[name] = exec_by_skill.get(name, 0) + w // 2
    print(f"[session-review] coverage 分母守门：Skill 强信号 {n_strong} / Read-SKILL 弱信号 {n_weak}"
          f"（零强信号且零弱信号 = 采集链失效，非真实零调用）")
    now = time.time()
    for skill_dir in sorted(skills_dir.iterdir()):
        if not skill_dir.is_dir():
            continue
        name = skill_dir.name
        has_evolution = (skill_dir / "EVOLUTION.md").exists()
        has_verify = any(skill_dir.rglob("verify-report.json"))
        exec_count = exec_by_skill.get(name, 0)
        # 死 skill 四重条件：零调用 + 无进化 + 无验证 + 目录冷窗。
        # dev 链等 skill 由主控按 SKILL.md 自演（不经 Skill 工具），零调用≠死；
        # 30 天无任何文件改动才是维护停滞信号（对齐 ADR 治理 30 天层级累进节奏）
        DIR_COLD_WINDOW = 30 * 86400
        last_touch = max((p.stat().st_mtime for p in skill_dir.rglob("*")
                          if p.is_file() and not p.name.endswith(".jsonl")),
                         default=0)
        is_cold_dir = (now - last_touch) > DIR_COLD_WINDOW
        if exec_count == 0 and not has_evolution and not has_verify and is_cold_dir:
            signals.append({
                "type": "dead-skill",
                "skill": name,
                "exec": 0,
                "suggest": "主控评估处置（decision-lifecycle）",
            })
        elif exec_count >= 3 and not has_evolution:
            signals.append({
                "type": "stale-eval",
                "skill": name,
                "exec": exec_count,
                "suggest": "skill-evolution",
            })
        # 冷 skill：低频使用无进化无验证 → lifecycle 处置评估（删/合并/保留）；
        # 信号消除路径 = lifecycle 处置后写 EVOLUTION（has_evolution 变真即不再报）
        elif 0 < exec_count <= 4 and not has_evolution and not has_verify:
            signals.append({
                "type": "cold-skill",
                "skill": name,
                "exec": exec_count,
                "suggest": "主控评估处置（decision-lifecycle）",
            })
        # 热 skill：高频使用且从未进化 → 评估是否需拆分（有 EVOLUTION 不报，已评估过）
        if exec_count >= 30 and not has_evolution:
            signals.append({
                "type": "hot-skill",
                "skill": name,
                "exec": exec_count,
                "suggest": "主控评估处置（decision-lifecycle）",
            })
    return signals


# 垃圾/报告产物特征（与根 .gitignore「项目特定产物」区同源——改此处须同步查 gitignore）
# tracked-junk 判垃圾用；untracked-report 判「报告类未 ignore」用（报告 json 按原则属本地）
_JUNK_SUBSTR = ("__pycache__/", ".pyc", "browser-profile/", "before-publish-", ".tmp")
_REPORT_NAMES = ("verify-report.json", "finish-check-report.json")


def scan_skill_git_changes(git_root: Path, claude_dir: Path) -> list[dict]:
    """手动进化留痕桥接：skills/ 有 git 改动但对应 skill 的 EVOLUTION.md
    未同步更新 → 建议 decision-record 沉淀。

    实证缺口：用户驱动的手动改 skill（不经 skill-evolution 跑分）无
    report.evolution.json 产物，采集链对此类进化零感知——改动只在 git diff 里
    躺着，下次扫描无信号（ADR skill-bypass-collection-gaps 断点②）。git 工作区改动为真值；
    沉淀同步基准 = _skill_sync_floor（EVOLUTION.md / skill-local ADR / 元层 adr
    多通道取最新）>= 改动文件 mtime 视为已沉淀。边界：仅扫未提交改动（已 commit
    的进化以 commit message 为真值，不回溯——避免扫描窗口无限扩大）。
    迁移后双仓各调一次：git_root=git 仓库根，claude_dir=该仓内 .claude 等价目录
    （资产仓 claude_dir 即仓库根自身，pathspec 前缀自适应）。
    """
    signals: list[dict] = []
    floor_cache: dict[str, float | None] = {}
    rel_claude = claude_dir.relative_to(git_root)
    pathspec = "skills/" if str(rel_claude) == "." else f"{rel_claude}/skills/"
    off = 0 if str(rel_claude) == "." else 1
    try:
        out = subprocess.run(
            ["git", "-C", str(git_root), "status", "--porcelain", "--untracked-files=all",
             "--", pathspec],
            capture_output=True, text=True, timeout=15,
        ).stdout.splitlines()
    except Exception:
        return signals
    skills_dir = claude_dir / "skills"
    # skill -> 是否存在晚于其 EVOLUTION.md 的改动文件
    dirty: dict[str, bool] = {}
    for ln in out:
        path = ln[3:].strip().strip('"')
        parts = path.split("/")
        # 形如 [.claude/]skills/{skill}/...；skill 根下直接文件（无归属）跳过
        if len(parts) < off + 2:
            continue
        # 只认 skill 逻辑定义文件：.env 配置调优与 registry/ 运行时留痕非进化改动，
        # 报「建议 record」属语义错配（自检实证：alibabacloud-sls-query/.env 被误报）
        if path.endswith(".env") or "/registry/" in path:
            continue
        skill = parts[off + 1]
        # _shared 是公共层非 skill，进化走 ADR 通道（无 EVOLUTION.md 是设计常态）
        if skill == "_shared":
            continue
        f = git_root / path
        try:
            mtime = f.stat().st_mtime
        except OSError:
            continue
        if skill not in floor_cache:
            floor_cache[skill] = _skill_sync_floor(skills_dir, skill, claude_dir)
        floor = floor_cache[skill]
        synced = floor is not None and floor >= mtime
        # 改动文件本身属于沉淀通道（EVOLUTION.md/skill-local ADR）时 synced 恒真（正在沉淀，不报）
        dirty[skill] = dirty.get(skill, False) or not synced
    for skill, unsynced in sorted(dirty.items()):
        # 编排类 skill（self_evolve=false）进化走 ADR/KNOWLEDGE 通道，EVOLUTION.md
        # 非必需——缺文件/未同步曾是误报源（自检实证：finish-check 等 3 skill 报
        # unsynced，实际已由 ADR 承载），2026-08-31 起由 _skill_sync_floor 的
        # skill-local ADR + 元层 adr 通道承接消除
        # 无 EVOLUTION.md = 从未接入进化沉淀（执行工具型 skill 由 ADR 裁决不接引擎，
        # 如 ast-grep）——无沉淀义务，报属误报；有 EVOLUTION.md 说明接入过，保守仍报。
        # 原 self_evolve=false 豁免已由 _skill_sync_floor 的 ADR 通道承接（2026-08-31），
        # metrics 链退役后不再单读该声明
        if unsynced and _has_evo_track(skills_dir, skill):
            signals.append({"type": "skill-changed-unsynced", "skill": skill,
                            "suggest": "decision-record"})
    return signals


def _skill_sync_floor(skills_dir: Path, skill: str, claude_dir: Path) -> float | None:
    """该 skill 的「沉淀同步基准」最新 mtime：EVOLUTION.md ∪ skill-local
    decisions/*.md ∪ 元层 adr 正文提及该 skill 的 ADR。

    进化沉淀通道不止 EVOLUTION.md（自检实证 2026-08-31：figma-to-code 的进化
    沉淀在 skill-local decisions/ ADR、finish-check 由元层 adr/ 承载——单认
    EVOLUTION.md 会让已沉淀的进化永远报 unsynced，信号无法自动消除）。adr
    正文匹配 skill 目录名即算承载，宽松方向的误判=漏报一条建议，代价可接受。
    无任何通道 → None（视为从未沉淀）。claude_dir=.claude 等价目录（元层 adr
    随 decisions 迁资产仓）。
    """
    paths = [skills_dir / skill / "EVOLUTION.md"]
    paths.extend((skills_dir / skill / "decisions").glob("*.md"))
    adr_dir = claude_dir / "decisions" / "adr"
    if adr_dir.is_dir():
        for adr in sorted(adr_dir.rglob("*.md")):
            try:
                if skill in adr.read_text(encoding="utf-8", errors="ignore"):
                    paths.append(adr)
            except OSError:
                continue
    mtimes = [p.stat().st_mtime for p in paths if p.is_file()]
    return max(mtimes) if mtimes else None


def _has_evo_track(skills_dir: Path, skill: str) -> bool:
    """skill 是否接入进化沉淀链路（EVOLUTION.md 存在；metrics 链已退役）。"""
    return (skills_dir / skill / "EVOLUTION.md").is_file()


def scan_adr_governance(repo: Path) -> list[dict]:
    """ADR 库治理信号：活跃区 ADR 数超限 → 建议 decision-record 治理（压缩/归档/分组）。

    治理规则定义在 decision-record SKILL.md「ADR 库治理」，阈值常量与
    阈值口径=adr/meta 直属件数（archive/ 不计），条款源 adr-archive-layer-reinstate-20260925（局部取代 dual-domain-taxonomy Decision 4）（2026-09-03 双域制定版 24/18，
    历史演进 6→8→11→13 见 archive 阈值修订链）；本信号只做超限兜底提醒，
    具体治理动作归 skill 执行。活跃区按双域物理分目录，计数遍历域子目录
    （data 暂空不建目录，glob 空迭代兼容）。
    """
    adr_dir = repo / ".claude" / "decisions" / "adr"
    if not adr_dir.is_dir():
        return []
    active = [f for domain in _ADR_DOMAINS for f in (adr_dir / domain).glob("*.md")]
    signals = []
    if len(active) > _ADR_LIMIT_GLOBAL:
        signals.append({"type": "adr-governance-overdue", "count": len(active),
                        "limit": _ADR_LIMIT_GLOBAL, "suggest": "decision-record"})
    for domain in _ADR_DOMAINS:
        dom_dir = adr_dir / domain
        if not dom_dir.is_dir():
            continue
        per_domain = list(dom_dir.glob("*.md"))
        if len(per_domain) > _ADR_LIMIT_PER_DOMAIN:
            signals.append({"type": "adr-governance-overdue", "count": len(per_domain),
                            "domain": domain, "limit": _ADR_LIMIT_PER_DOMAIN,
                            "suggest": "decision-record"})
    # 阈值随载荷走（limit 字段），渲染不硬编码——09-03 治理批曾出现渲染文案停留旧阈值 11 的口径失配
    return signals


_SKILL_FILE_LINE_LIMIT = 400


def scan_oversize_files(skills_dir: Path, display_root: Path) -> list[dict]:
    """skill 资产体积信号：md 文件超行动线 → 触发拆分/瘦身评估（可判不动）。

    阈值权威定义在 standards/skill-design.md「资产三分法与大小阈值」，
    与 worker-instructions 整读禁令同源。扫描面 = 各 skill 的 SKILL.md 与
    references/agents/templates 下的 .md；EVOLUTION.md 不在扫描面（有独立
    压缩规则，见 cleanup-rules.md）。信号只做超线兜底提醒，处置分级见
    skill-design.md，具体动作经用户确认。迁移后按仓传 skills_dir，
    display_root 仅用于信号里的相对路径展示。
    """
    if not skills_dir.is_dir():
        return []
    signals: list[dict] = []
    for skill_dir in sorted(skills_dir.iterdir()):
        if not skill_dir.is_dir():
            continue
        targets = [skill_dir / "SKILL.md"]
        for sub in ("references", "agents", "templates"):
            sub_dir = skill_dir / sub
            if sub_dir.is_dir():
                targets.extend(sub_dir.rglob("*.md"))
        for f in targets:
            if not f.is_file():
                continue
            try:
                with f.open(encoding="utf-8", errors="replace") as fh:
                    n_lines = sum(1 for _ in fh)
            except OSError:
                continue
            if n_lines > _SKILL_FILE_LINE_LIMIT:
                signals.append({"type": "skill-file-oversize",
                                "path": str(f.relative_to(display_root)),
                                "lines": n_lines, "limit": _SKILL_FILE_LINE_LIMIT,
                                "suggest": "skill-evolution"})
    return signals


def _load_active_adrs(repo: Path) -> list[tuple[str, Path]]:
    """活跃 ADR 清单：双域 glob，返回 (slug, 路径)（data 域缺失返回空）。
    项目仓形态兼容：无 meta/data 子目录时 fallback 平铺 adr/*.md（B2 拆分后项目侧单域）。"""
    adr_dir = repo / ".claude" / "decisions" / "adr"
    items: list[tuple[str, Path]] = []
    if not any((adr_dir / d).is_dir() for d in _ADR_DOMAINS):
        return [(f.stem, f) for f in adr_dir.glob("*.md")]
    for domain in _ADR_DOMAINS:
        for f in (adr_dir / domain).glob("*.md"):
            items.append((f.stem, f))
    return items


def _frontmatter_date(path: Path) -> datetime | None:
    """读 ADR frontmatter 的 date 字段；缺失/畸形返回 None。"""
    try:
        for line in path.read_text(encoding="utf-8").splitlines()[:15]:
            if line.startswith("date:"):
                return datetime.strptime(line.split(":", 1)[1].strip()[:10], "%Y-%m-%d")
    except Exception:
        return None
    return None


def _frontmatter_fields(path: Path, fields: tuple[str, ...]) -> dict[str, str]:
    """读 ADR frontmatter 指定字段（仅扫头部 20 行）；缺失字段值为空串。"""
    result = {k: "" for k in fields}
    try:
        for line in path.read_text(encoding="utf-8").splitlines()[:20]:
            for k in fields:
                if line.startswith(f"{k}:"):
                    result[k] = line.split(":", 1)[1].strip()
                    break
    except Exception:
        pass
    return result


def scan_adr_progression_review(repo: Path) -> list[dict]:
    """ADR 层级累进复核：活跃 ADR >30 天无变更 → 低风险仅汇报复核建议。

    语义=层级累进判断（非直接清理）：①结论稳定且通用→晋升 L3 永久规则（条款化进
    CLAUDE.md/standards）②仍有效→维持 L2 ③过时/被取代→归档。阈值 30 与三选项
    定义同 KNOWLEDGE.md §管理规约。
    时效以文件 mtime 为代理：写盘即算活跃，不依赖提交时点（git log 只反映最后
    commit，未提交的修订会漏判）。局限：touch/批量迁移会重置 mtime
    （dual-domain-taxonomy 迁移曾致全库 30 天静默，属预期）；date frontmatter 是
    决策日非最后修订日——mtime 是可用性最好的近似。
    """
    signals: list[dict] = []
    now = datetime.now()
    for adr_id, path in _load_active_adrs(repo):
        try:
            last = datetime.fromtimestamp(path.stat().st_mtime)
        except OSError:
            continue
        days = (now - last).days
        if days > 30:
            signals.append({"type": "adr-progression-review", "id": adr_id,
                            "days": days, "suggest": "decision-record"})
    return signals


def scan_adr_consistency(repo: Path) -> list[dict]:
    """ADR 一致性校验：KNOWLEDGE 单源索引 ↔ 文件双向对账、frontmatter status/supersedes
    双向、链接死链。问题清单机械回填类，低风险自动消化。

    dual-domain-taxonomy 后 adr-index 已废，对账真值改为「活跃域文件 id 集 ↔
    KNOWLEDGE adr 行 id 集」单源双向；decisions-tiered-versioning 后无 archive 层，
    废弃 ADR 物理删除（历史靠 git），无归档对账面。
    """
    adr_dir = repo / ".claude" / "decisions" / "adr"
    issues: list[str] = []
    # ① KNOWLEDGE 单源对账：adr 行 ↔ 实际文件
    try:
        kt = (repo / ".claude" / "decisions" / "KNOWLEDGE.md").read_text(encoding="utf-8")
    except Exception:
        kt = ""
    # 兼容双形态：仓级 adr/<domain>/slug.md 与项目级平铺 adr/slug.md（B2 拆分后项目单域）
    k_ids = {m.group(1) for m in re.finditer(r"\]\(adr/(?:[a-z]+/)?([^)/]+)\.md\)", kt)}
    active = _load_active_adrs(repo)
    active_ids = {i for i, _ in active}
    orphan = sorted(k_ids - active_ids)
    missing = sorted(active_ids - k_ids)
    if orphan:
        issues.append(f"KNOWLEDGE 孤儿条目 {','.join(orphan)}")
    if missing:
        issues.append(f"KNOWLEDGE 缺条目 {','.join(missing)}")
    # ② frontmatter status 枚举、supersedes 双向
    meta: dict[str, dict] = {}
    for adr_id, path in active:
        fm = _frontmatter_fields(path, ("status", "supersedes", "superseded_by"))
        if not (fm["status"] in ("Proposed", "Deprecated", "Superseded") or fm["status"].startswith("Accepted")):
            issues.append(f"{adr_id} status 取值异常: {fm['status']}")
        meta[adr_id] = {"supersedes": {x.strip().strip('"') for x in fm["supersedes"].strip("[]").split(",") if x.strip()},
                        "superseded_by": {x.strip().strip('"') for x in fm["superseded_by"].strip("[]").split(",") if x.strip()}}
    for adr_id, m in meta.items():
        for target in m["supersedes"]:
            if target in meta and adr_id not in meta[target]["superseded_by"]:
                issues.append(f"{adr_id} supersedes {target} 但 {target} 未回写 superseded_by")
    # ③ 链接死链：adr/ 前缀按 adr/ 解析；../ 相对与域内相对（postmortems/ 等）
    # 同按 KNOWLEDGE 所在 decisions 目录解析（pathlib exists 解析 ..）。
    # ../ 支持是补盲区：曾因正则不含 ../，data-domain 节 15 条 ../../skills 双层
    # 前缀错链零检出（真死链漏网），dry-run 红轮实证后收进检测面
    dec_dir = adr_dir.parent
    for m in re.finditer(r"\]\(((?:\.\./)*(?:adr/)?[a-zA-Z0-9_./-]+\.md)\)", kt):
        link = m.group(1)
        if link.startswith("adr/"):
            base, rel = adr_dir, link[len("adr/"):]
        else:
            base, rel = dec_dir, link
        if not (base / rel).exists():
            issues.append(f"死链 {link}")
    if not issues:
        return []
    return [{"type": "adr-consistency", "issues": issues, "suggest": "decision-record"}]


def scan_experience_summary(repo: Path) -> list[dict]:
    """经验汇总到期：距上次「经验汇总」文档 >90 天 且 其后 meta 域新增 ADR ≥3 份
    → 高风险信号（产物为 experience/ 本地汇总文档，须用户确认）。汇总文档历史落点
    含 adr/meta/（曾以 ADR 形态存在）与 experience/（本地文档）双目录，均参与定位。
    无历史汇总记录视为到期（首次汇总由存量数量判定）。
    """
    dec = repo / ".claude" / "decisions"
    scan_dirs = [dr for dr in (dec / "adr" / "meta", dec / "experience") if dr.is_dir()]
    if not scan_dirs:
        return []
    last_summary: datetime | None = None
    for dr in scan_dirs:
        for f in dr.glob("*.md"):
            if "经验汇总" not in f.stem and "experience-summary" not in f.stem:
                continue
            dt = _frontmatter_date(f)
            if dt and (last_summary is None or dt > last_summary):
                last_summary = dt
    today = datetime.now()
    days = (today - last_summary).days if last_summary else None
    if days is not None and days <= 90:
        return []
    adr_dir = dec / "adr" / "meta"
    newer = (sum(1 for f in adr_dir.glob("*.md")
                 if (dt := _frontmatter_date(f)) and (last_summary is None or dt > last_summary))
             if adr_dir.is_dir() else 0)
    if newer < 3:
        return []
    return [{"type": "experience-summary-due", "days": days, "count": newer,
             "suggest": "decision-record"}]


def scan_corrections_lifecycle(repo: Path) -> list[dict]:
    """corrections 状态机断链修复读者端（T127①③，2026-09-28）。

    写者/转移执行者登记：new=主控（reflex-correction 提醒驱动）手写；new→merged=主控
    条款落地轮转移（状态加 @日期）。本扫描只做机械核对、提示注入，不代写不代转移
    （T126 PCF 裁决上限）。三类信号：
    - correction-merge-due：new 行超龄（14 天）未转移——条款生效与否由主控确认，
      生效则当轮转 merged@日期，未生效则条款回退转 stale@日期。
    - correction-merged-cleanable：merged@日期 超 30 天（验证 ≥2 轮纪律上限）——
      教训已由条款承载，候选删除（删行须主控确认，非机械删）。
    - correction-stale-cleanable：stale@日期 超 30 天——清理轮删除候选。
    状态形态判据=模板 T127②（merged@YYYY-MM-DD）；无日期的 new 行不报（防噪音，
    形态漂移由模板纪律约束，不在此执法）。
    """
    signals: list[dict] = []
    cdir = repo / ".claude" / ".state" / "corrections"
    if not cdir.is_dir():
        return signals
    today = datetime.now().date()
    for f in sorted(cdir.glob("*.md")):
        try:
            text = f.read_text(encoding="utf-8")
        except OSError:
            continue
        skill = f.stem
        for ln in text.splitlines():
            s = ln.strip()
            if not s.startswith("| C"):
                continue
            cells = [c.strip() for c in s.strip("|").split("|")]
            if len(cells) < 6:
                continue  # 形态漂移行留给模板纪律，机械面不猜列
            cid, status = cells[0], cells[-1]
            m = re.search(r"(\d{4}-\d{2}-\d{2})", ln)
            if status == "new":
                if m:
                    try:
                        age = (today - datetime.strptime(m.group(1), "%Y-%m-%d").date()).days
                    except ValueError:
                        continue
                    if age > 14:
                        signals.append({"type": "correction-merge-due", "skill": skill,
                                        "id": cid, "days": age, "suggest": "主控登记（info-collection）"})
            else:
                m2 = re.match(r"(merged|stale)@(\d{4}-\d{2}-\d{2})$", status)
                if not m2:
                    continue  # 无 @日期 的旧形态行不报（迁移期容忍，模板已定版）
                try:
                    dt = datetime.strptime(m2.group(2), "%Y-%m-%d").date()
                except ValueError:
                    continue
                if (today - dt).days > 30:
                    signals.append({"type": f"correction-{m2.group(1)}-cleanable",
                                    "skill": skill, "id": cid, "days": (today - dt).days,
                                    "suggest": "主控登记（info-collection）"})
    return signals


def scan_repo_hygiene(repo: Path) -> list[dict]:
    """仓库卫生信号：非重要文件混入版本记录的自动检测（用户痛点「每次都要我提醒」的
    自进化版——垃圾入库曾积 321 个无人发现）。

    tracked-junk：已跟踪文件匹配垃圾特征 → 建议 rm --cached（gitignore 不影响
    已跟踪文件，规则在文件仍入库——这是垃圾曾积压的根因）。
    untracked-report：未跟踪文件匹配报告特征 → 建议 ignore 扩充（报告结论已入
    对应 .md，json 属过程）。两类均只读分析，走低风险自动消化。
    """
    signals: list[dict] = []
    try:
        tracked = subprocess.run(
            ["git", "-C", str(repo), "ls-files"],
            capture_output=True, text=True, timeout=15,
        ).stdout.splitlines()
    except Exception:
        return signals
    junk = [f for f in tracked if any(s in f for s in _JUNK_SUBSTR)]
    if junk:
        signals.append({"type": "tracked-junk", "count": len(junk),
                        "sample": junk[:3], "suggest": "gitignore-maintenance"})
    try:
        # --untracked-files=all：porcelain 默认把全 untracked 目录折叠成目录名，
        # 目录内的报告文件名不可见会漏检（验证实证：tmp-hyg/verify-report.json 漏报）
        status = subprocess.run(
            ["git", "-C", str(repo), "status", "--porcelain", "--untracked-files=all"],
            capture_output=True, text=True, timeout=15,
        ).stdout.splitlines()
    except Exception:
        return signals
    # ?? 开头 = 未跟踪；报告类未 ignore 才会出现在此（已 ignore 的不会冒出）
    reports = [ln[3:].strip() for ln in status
               if ln.startswith("??") and any(r in ln for r in _REPORT_NAMES)]
    if reports:
        signals.append({"type": "untracked-report", "count": len(reports),
                        "sample": reports[:3], "suggest": "gitignore-maintenance"})
    return signals


def scan_dataset_expiration(repo: Path) -> list[dict]:
    """红蓝数据集时效信号：条目产物失联 / 基线超期未刷新检测。

    两类信号：dataset-orphan = 条目产物路径不存在（产物删除/迁移）→ 更新条目
    或确认删除；dataset-stale = last_verified 超 90 天且产物其后仍被改动
    （产物在变、基线未刷新）→ 重跑 verify 刷新基线。产物未动的老条目不报——
    静态产物配旧基线不构成回归风险，报了就是噪音（同 pass+unresolved 误报
    教训：只报真变化）。只标记不删行：删条目属高风险自修改，须用户确认。
    """
    signals: list[dict] = []
    ds = (repo / ".claude" / "skills" / "decision-verify" / "data"
          / "red-blue-dataset.jsonl")
    if not ds.exists():
        return signals
    today = datetime.now().date()
    for ln in ds.read_text(encoding="utf-8").splitlines():
        if not ln.strip():
            continue
        try:
            entry = json.loads(ln)
        except Exception:
            continue  # 坏行留给人工修，不崩 hook
        eid = entry.get("id", "?")
        chain = entry.get("task_chain")
        # isinstance 防御：task_chain 畸形为列表时 `or {}` 穿透，.get 直接崩
        out = chain.get("final_output_path", "") if isinstance(chain, dict) else ""
        if not isinstance(out, str) or not out:
            continue
        f = repo / out
        if not f.exists():
            signals.append({"type": "dataset-orphan", "id": eid, "path": out,
                            "suggest": "decision-verify"})
            continue
        try:
            lv = datetime.strptime(str(entry.get("last_verified", "")),
                                   "%Y-%m-%d").date()
        except ValueError:
            continue
        days = (today - lv).days
        # 产物 mtime 晚于基线验证日 = 基线未覆盖其后的改动，此时超期才有回归风险
        if days > 90 and datetime.fromtimestamp(f.stat().st_mtime).date() > lv:
            signals.append({"type": "dataset-stale", "id": eid, "days": days,
                            "path": out, "suggest": "decision-verify"})
    return signals


# 共享状态文件路径特征：识别「指向这些文件的变量」再查其上的裸写调用。
# shared_state.py 是唯一合法裸写模块（helper 内部实现），扫描时排除。
_SHARED_PATH_HINT = r"(?:PENDING|reflex-(?:start-|stop-)?state)"


_PERSISTENT_ASSETS = ("evolution-daily.log", "pending-history.jsonl",
                       "weekly-eval.marker", "joint-review.marker",
                       "reflex-pending.marker", "weekly-eval-report.md")


def scan_persistent_assets(repo: Path) -> list[dict]:
    """白名单持久资产消失检测（campaign-20260916 归口件读者端）。

    双宿主登记的读者：写者=cleanup-builds.py（白名单保护+台账），读者=本扫描。
    两态判据（首扫实测 5 误报修正：joint-review.marker 从未创建被当消失）：
    缺失 + cleanup-ledger 有该名删除记录 = asset-vanished（高置信事故）；
    缺失 + 无台账记录 = asset-missing（观察行——可能从未创建，marker 锚按需生成）。
    mtime 回跳检测需基线存储暂缺（契约见 evolution-discipline §归口）。
    """
    repo_build = repo / ".claude" / ".build"
    if not repo_build.is_dir():
        return []
    # 资产根与仓根的持久资产集不同（登记两处同改：evolution-discipline §归口白名单）：
    # 资产根(~/.claude/.build)=反射锚+台账；仓根 .claude/.build=周期日志/历史/周报。
    if repo == Path.home():
        watch = ("reflex-pending.marker", "cleanup-ledger.jsonl")
    else:
        watch = _PERSISTENT_ASSETS
    deleted: set[str] = set()
    for ledger_path in (Path.home() / ".claude" / ".build" / "cleanup-ledger.jsonl",
                        repo_build / "cleanup-ledger.jsonl"):
        try:
            for ln in ledger_path.read_text(encoding="utf-8").splitlines():
                try:
                    entry = json.loads(ln)
                except (ValueError, TypeError):
                    continue
                deleted.add(Path(str(entry.get("path", ""))).name)
        except OSError:
            continue
    signals = []
    for name in watch:
        if (repo_build / name).exists():
            continue
        if name in deleted:
            signals.append({"type": "asset-vanished", "path": str(repo_build / name),
                            "skill": "skill-evolution", "suggest": "skill-evolution",
                            "asset": name,
                            "detail": f"白名单资产 {name} 有台账删除记录却已不在（契约见 evolution-discipline §归口）"})
        else:
            signals.append({"type": "asset-missing", "path": str(repo_build / name),
                            "skill": "skill-evolution", "suggest": "skill-evolution",
                            "asset": name,
                            "detail": f"白名单资产 {name} 不存在且无删除台账（可能从未创建，观察行非事故）"})
    return signals


def scan_shared_state_violations(repo: Path) -> list[dict]:
    """扫 hook 脚本对共享状态文件的裸写（write_text/unlink/覆盖式 open）。

    为什么检测网放 Stop 自扫而非改动时 gate：hook 脚本是自动化进程，无人工
    code review 时点——「能发现+修复」哲学向运行时域的延伸。启发式正则非 AST，
    只产信号不 gate；精确复核用 ast-grep 的 no-shared-state-bare-write 规则。
    """
    scripts_dir = repo / ".claude" / "skills" / "skill-evolution" / "scripts"
    if not scripts_dir.is_dir():
        return []
    violations: list[str] = []
    for py in sorted(scripts_dir.glob("*.py")):
        if py.name == "shared_state.py":
            continue
        try:
            lines = py.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        guard_vars: set[str] = set()
        for ln in lines:
            m = re.match(r"^\s*([A-Za-z_]\w*)\s*=\s*[^\n]*?" + _SHARED_PATH_HINT, ln)
            if m:
                guard_vars.add(m.group(1))
            # 变量名即共享路径名的写法（如 PENDING = get_pending_path()，RHS 无特征）：
            # 只收精确名，不收 state_path——knowledge-recall 的 /tmp 会话状态同用该名
            m2 = re.match(r"^\s*(PENDING|STATE_START|STATE_STOP)\s*=", ln)
            if m2:
                guard_vars.add(m2.group(1))
        for i, ln in enumerate(lines, 1):
            stripped = ln.strip()
            if stripped.startswith("#"):
                continue
            m = re.search(r"\b([A-Za-z_]\w*)\.(write_text|unlink)\(", ln)
            if m and m.group(1) in guard_vars:
                violations.append(f"{py.name}:{i}")
                continue
            # 覆盖式 open("w") 同属裸写；追加式 open("a") 不在禁列（O_APPEND 单写原子）
            if re.search(r"open\([^)]*['\"]w['\"]", ln) and re.search(_SHARED_PATH_HINT, ln):
                violations.append(f"{py.name}:{i}")
    if not violations:
        return []
    return [{
        "type": "shared-state-violation",
        "files": violations,
        "suggest": "skill-evolution",
    }]


def _iter_jsonl(path: Path) -> list[dict]:
    """容错读 jsonl 为 dict 行列表：文件缺失/坏行（并发写截断）跳过不崩。"""
    if not path.exists():
        return []
    rows: list[dict] = []
    for ln in path.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(ln)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def scan_calibration_tier_quality(repo: Path) -> list[dict]:
    """档位校准信号：finish-verdicts method 分布事实汇报，不做升降档结论。

    verdicts 既有唯一消费方是 reflex-check 消重复提醒，method 分布无消费方——
    finish-check 档位推断规则是否贴合真实使用无从校准（note 为自由文本无结构化
    判据，机器预设「该升/降档」会臆造）。只报分布+疑点，结论留用户/skill-evolution。
    样本 <5 条不触发（噪音抑制）。
    """
    rows = [r for r in _iter_jsonl(repo / ".claude" / ".state" / "finish-verdicts.jsonl")
            if isinstance(r.get("method"), str)]
    if len(rows) < 5:
        return []
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["method"]] = counts.get(r["method"], 0) + 1
    notes = []
    if counts.get("full", 0) == 0:
        notes.append("full 零使用（档位规则或适用场景待复核）")
    if counts.get("real-run", 0) * 2 > len(rows):
        notes.append("real-run 占比过半（等效验证判据执行待复核）")
    sig: dict = {"type": "calibration-tier-quality", "suggest": "skill-evolution",
                 "total": len(rows),
                 "dist": ", ".join(f"{k}×{counts[k]}" for k in sorted(counts))}
    if notes:
        sig["notes"] = "；".join(notes)
    return [sig]


# 泛词 bigram：与 knowledge-recall STOP_BIGRAMS 同哲学（功能词无区分度），但独立维护
# ——两处语义不同（召回精度 vs 触发词统计），跨 hook import 形成隐性耦合
_TRIGGER_STOP_BIGRAMS = {
    "一下", "这个", "那个", "什么", "怎么", "可以", "需要", "进行", "使用", "一个",
    "没有", "我们", "然后", "如果", "但是", "还有", "现在", "可能", "应该", "或者",
    "帮我", "看看", "处理", "相关", "问题", "分析",
}


def scan_calibration_skill_triggers(skills_dir: Path, registry: Path) -> list[dict]:
    """触发语料校准信号：collect 全局调用日志此前无消费方（collect.py 自述）。

    高频 skill 的 user_input 高频 bigram（≥3 次）不在其 SKILL.md description 中
    → 触发语料与声明话术脱节，建议补词（消化分级见 evolution-discipline 信号表）。
    只统计 Skill 工具调用（Agent 调用 target 是 agent 名，无对应 SKILL.md）。
    迁移后按仓传 skills_dir，registry 恒为资产仓全局单轨（两仓同源计数）。
    """
    rows = [r for r in _iter_jsonl(registry)
            if r.get("tool") == "Skill" and isinstance(r.get("target"), str)]
    by_skill: dict[str, list[dict]] = {}
    for r in rows:
        by_skill.setdefault(r["target"], []).append(r)
    signals: list[dict] = []
    for skill, recs in sorted(by_skill.items()):
        if len(recs) < 10:
            continue  # 样本门槛：低频 skill 的高频词无统计意义
        skill_md = skills_dir / skill / "SKILL.md"
        if not skill_md.exists():
            continue
        desc = ""
        try:
            for ln in skill_md.read_text(encoding="utf-8").splitlines()[:15]:
                if ln.startswith("description:"):
                    desc = ln.split(":", 1)[1]
                    break
        except OSError:
            continue
        # bigram 计数（同 knowledge-recall 中文双字切分，非 TF-IDF——与体系纯文本哲学一致）
        freq: dict[str, int] = {}
        for r in recs:
            text = r.get("user_input") or ""
            for span in re.findall(r"[一-鿿]{2,}", text):
                for i in range(len(span) - 1):
                    bg = span[i:i + 2]
                    if bg not in _TRIGGER_STOP_BIGRAMS:
                        freq[bg] = freq.get(bg, 0) + 1
        missing = [w for w, c in sorted(freq.items(), key=lambda x: -x[1])
                   if c >= 3 and w not in desc][:4]
        fail_cnt = sum(1 for r in recs if r.get("success") == "fail")
        sig: dict = {"type": "calibration-skill-triggers", "suggest": "skill-evolution",
                     "skill": skill, "calls": len(recs)}
        if missing:
            sig["missing_words"] = missing
        if fail_cnt >= 3:
            sig["fail_cnt"] = fail_cnt
        # 无缺词且无高频失败 = 无校准点，不产信号（只报有事实依据的建议）
        if "missing_words" in sig or "fail_cnt" in sig:
            signals.append(sig)
    return signals


def scan_calibration_recall_quality(repo: Path) -> list[dict]:
    """召回质量校准信号：reflex-hooks 运行日志的消费闭环（脚本注释承诺的效果评估）。

    口径同 evolution-discipline.md §运行数据参考线：召回率=match/knowledge-recall
    总行数（>30%）；打扰度=block/(block+silent+silent-verified)，只计
    hook=="reflex-check"（<15%）。排除 test- 前缀 session（测试 session 规范）。
    只看近 7 天（2026-08-25 用户裁决）：日志只增不减，
    全量口径会让历史密集期（如 2026-08-16~20 skill 进化周）把打扰度永久拉高，
    信号失去时效性——近 7 天实测 14.2% 已达标。
    """
    cutoff = datetime.now() - timedelta(days=7)
    rows = []
    for r in _iter_jsonl(repo / ".claude" / ".build" / "reflex-hooks.jsonl"):
        if str(r.get("session_id", "")).startswith("test-"):
            continue
        try:
            when = datetime.strptime(str(r.get("ts")), "%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue  # 无效时间戳的行不参与，宁可漏不可错
        if when >= cutoff:
            rows.append(r)
    recall_rows = [r for r in rows if r.get("hook") == "knowledge-recall"]
    reflex_rows = [r for r in rows if r.get("hook") == "reflex-check"]
    if len(recall_rows) < 10 or len(reflex_rows) < 10:
        return []
    match_cnt = sum(1 for r in recall_rows if r.get("event") == "match")
    recall_rate = match_cnt / len(recall_rows)
    ev = [str(r.get("event")) for r in reflex_rows]
    denom = ev.count("block") + ev.count("silent") + ev.count("silent-verified")
    disturb_rate = ev.count("block") / denom if denom else 0.0
    notes = []
    if recall_rate <= 0.30:
        notes.append(f"召回率 {recall_rate:.0%}≤30% 参考线（召回词/门槛待校准）")
    if denom and disturb_rate >= 0.15:
        notes.append(f"打扰度 {disturb_rate:.0%}≥15% 参考线（触发条件待收紧）")
    if not notes:
        return []  # 达标不打扰：仅越参考线才产信号
    return [{"type": "calibration-recall-quality", "suggest": "skill-evolution",
             "recall": f"{recall_rate:.0%}({match_cnt}/{len(recall_rows)})",
             "disturb": f"{disturb_rate:.0%}({ev.count('block')}/{denom})",
             "notes": "；".join(notes)}]


def main() -> int:
    # scan_tool_heavy_sessions 已退役（2026-08-31 用户批准）：阈值 400 实证 12/12 条
    # 信号同质无区分度，gate-rules §1 明确执行编排型不接入 → 无真消化路径，7 天窗口
    # 过期即再生。恢复方式：git revert 本段注释对应的删除提交。
    # hook 容错：与其余三脚本同契约——任何扫描异常 stderr 可见 + exit 0，
    # 不抛给会话（此前 main 无兜底，单文件畸形即崩 Stop hook，魔鬼测试实证）
    # --dry-run：打印信号不写 PENDING——重构/调试时验证扫描面，不污染派生视图
    dry_run = "--dry-run" in sys.argv
    try:
        return _main(dry_run=dry_run)
    except Exception as exc:  # noqa: BLE001
        print(f"[session-review] 失败: {exc}", file=sys.stderr)
        return 0


def scan_map_counts(asset: Path, proj: Path) -> list[dict]:
    """地图计数对账：README/KNOWLEDGE 尾注声明计数 vs 目录实测（窄版白名单锚点）。

    只对账机器可解析锚点：README 固定句式计数 + KNOWLEDGE 尾注 HTML 计数注释
    （dual-domain-taxonomy：adr-index 已废，锚点迁 KNOWLEDGE）；日期锚快照句
    不对账，避免快照语义误报。已删名残留 grep（机制 B）经三视角对抗推衍泛词
    精度≈0，明确不做。
    suggest 值 `sync-map-counts` 是直消标签（分组头展示用），非 skill 路由名。
    迁移后跨仓计数：asset=资产 .claude 目录本身；proj=项目 .claude 等价目录
    （调用方传 PROJ/".claude"）。skills 对账仅 asset 仓（README 锚点只声明
    agentos 单仓，项目仓 qualitative，2026-09-19 W2 口径定版）；
    agents/adr/README/KNOWLEDGE 在资产仓；standards 在项目仓。
    """
    signals = []
    def _count_skills(claude: Path) -> int:
        skills_dir = claude / "skills"
        return (len([d for d in skills_dir.iterdir() if d.is_dir() and d.name != "_shared"])
                if skills_dir.is_dir() else -1)
    def _count_shared(claude: Path) -> int:
        shared_dir = claude / "skills" / "_shared"
        return (sum(1 for p in shared_dir.rglob("*")
                    if p.is_file() and "__pycache__" not in p.parts)
                if shared_dir.is_dir() else -1)  # 2026-09-21 心跳轮⑪ _shared 锚
    n_skills = _count_skills(asset)
    agents_dir = asset / "agents"
    n_agents = len(list(agents_dir.glob("*.md"))) if agents_dir.is_dir() else -1
    adr_dir = asset / "decisions" / "adr"
    n_adr = {d: len(list((adr_dir / d).glob("*.md")))
             for d in _ADR_DOMAINS} if adr_dir.is_dir() else {}

    readme = asset / "README.md"
    if readme.is_file():
        # 2026-09-30 全局维护轮：锚点扩容八类（装备库全景对账，根治「全局视角维护弱」
        # =检测面窄）——新增 scripts/standards/commands/MCP/launchd 五锚，实测口径
        # 与 README 装备库表一致（standards=asset 仓实存目录，非 PROJ 漂移语义）
        n_scripts = len(list((asset / "scripts").glob("*.py"))) + len(list((asset / "scripts").glob("*.sh"))) if (asset / "scripts").is_dir() else -1
        n_standards = len(list((asset / "standards").glob("*.md"))) + len(list((asset / "standards" / "common").glob("*.md"))) if (asset / "standards").is_dir() else -1
        n_commands = len([f for f in (asset / "commands").glob("*.md")]) if (asset / "commands").is_dir() else -1
        try:
            cj = json.loads((asset.parent / ".claude.json").read_text(encoding="utf-8")) if (asset.parent / ".claude.json").is_file() else {}
            n_mcp = len(cj.get("mcpServers", {}))
        except Exception:
            n_mcp = -1
        n_launchd = len(list(Path.home().joinpath("Library/LaunchAgents").glob("com.agentos.*.plist"))) if Path.home().joinpath("Library/LaunchAgents").is_dir() else -1
        text = readme.read_text(encoding="utf-8")
        for pat, actual, label in (
                (r"skills (\d+) 个 skill 目录", n_skills, "skills"),
                (r"agents/ (\d+) 个", n_agents, "agents"),
                # 2026-09-21 心跳轮⑪：补 _shared 文件数锚（README:35 声明值），
                # 实测=skills/_shared 递归文件数（不含 __pycache__）
                (r"_shared/ (\d+) 文件", _count_shared(asset), "_shared"),
                (r"scripts/ (\d+) 个", n_scripts, "scripts"),
                (r"standards/ (\d+) 个", n_standards, "standards"),
                (r"commands/ (\d+) 个", n_commands, "commands"),
                (r"MCP (\d+) 个", n_mcp, "MCP"),
                (r"launchd (\d+) 个", n_launchd, "launchd")):
            # standards 边已随 W2 口径定版删除（standards 物理在项目仓且 PROJ 随 cwd
            # 漂移——元层 cwd 下 proj==asset 致 9≠37 假阳性，2026-09-19 实证）
            for m in re.findall(pat, text):
                if int(m) != actual:
                    signals.append({"type": "map-count-drift",
                                    "edge": f"README {label} 声明 {m}≠实测 {actual}",
                                    "suggest": "sync-map-counts"})
        # 复合计数边已随 W2 口径定版删除（README 不再声明「N = agentos A + harness H」
        # 和式；项目仓 skill 数 qualitative 化，见 AGENTOS-MAP §六兜底声明）
    # KNOWLEDGE 尾注计数锚点（dual-domain-taxonomy：adr-index 已废，锚点迁此；
    # decisions-tiered-versioning：archive 域取消，锚点两数化）
    kt_path = asset / "decisions" / "KNOWLEDGE.md"
    if kt_path.is_file():
        m = re.search(r"<!-- 计数：meta (\d+) / data (\d+)",
                      kt_path.read_text(encoding="utf-8"))
        if m:
            actual = (n_adr.get("meta"), n_adr.get("data"))
            declared = (int(m[1]), int(m[2]))
            if actual != declared:
                signals.append({"type": "map-count-drift",
                                "edge": f"KNOWLEDGE 注释 {declared}≠实测 {actual}",
                                "suggest": "sync-map-counts"})
    return signals


def scan_finish_coverage(registry: Path, repo: Path) -> list[dict]:
    """收尾覆盖信号（2026-09-30 参与闭环 v2 §D2 消解待定项）。

    用户裁决「不要存在待定项」：hook 阻断式硬门（Stop 必过 finish-check）否决——
    死循环风险+每会话 token 税+一刀切违档位化。对症最小解=本信号：纯台账 grep
    事后审计，只报警不拦路。
    判据：24h 窗内 registry 会话活动 ≥20 行（短会话豁免，对齐 recall 免分母
    门槛 8→20 同族口径）且当日无 finish-verdicts 行且 BACKLOG 尾行日期≠今日
    → finish-no-closeout 信号，建议下次会话补总账行或走 finish-check。
    """
    signals: list[dict] = []
    win = time.time() - 24 * 3600
    today = datetime.now().strftime("%Y-%m-%d")
    n_active = 0
    try:
        for ln in open(registry, encoding="utf-8"):
            try:
                d = json.loads(ln)
            except ValueError:
                continue
            try:
                if datetime.strptime(d.get("ts", ""), "%Y-%m-%d %H:%M:%S").timestamp() >= win:
                    n_active += 1
            except ValueError:
                continue
    except OSError:
        return signals
    if n_active < 20:
        return signals
    fvd = repo / ".state" / "finish-verdicts.jsonl"
    try:
        has_finish = any(today in ln for ln in open(fvd, encoding="utf-8"))
    except OSError:
        has_finish = False
    backlog = repo / "decisions" / "postmortems" / "BACKLOG.md"
    try:
        tail_lines = [ln for ln in open(backlog, encoding="utf-8") if ln.strip()]
        m = re.search(r"2026-\d{2}-\d{2}", tail_lines[-1]) if tail_lines else None
        tail_date = m.group(0) if m else ""
    except OSError:
        tail_date = ""
    if not has_finish and tail_date != today:
        signals.append({
            "type": "finish-no-closeout",
            "edge": (f"24h 活动行 {n_active} 条但今日既无 finish-verdicts 行也无 BACKLOG "
                     "当日轮末行——收尾门未覆盖（补总账行或主控等效收尾声明）"),
            "suggest": "主控收尾自检（finish-check）",
        })
    return signals


def _main(dry_run: bool = False) -> int:
    # 双仓扫描矩阵：资产仓（home/.claude）与项目仓各按归属扫描；跨仓件并扫合并。
    # registry 恒为资产仓全局单轨（collect 随 skill-evolution 迁移）。
    registry = ASSET / "skills" / "skill-evolution" / "registry" / "invocations.jsonl"
    proj_skills = PROJ / ".claude" / "skills"
    signals = (
        # verify/evolution 报告：资产仓 rglob 基点收窄到 skills（防扫整个 home）
        scan_verify_reports(ASSET / "skills") + scan_verify_reports(PROJ)
        + scan_evolution_reports(ASSET / "skills") + scan_evolution_reports(PROJ)
        + scan_skill_coverage(ASSET / "skills", registry)
        + scan_skill_coverage(proj_skills, registry)
        + scan_skill_git_changes(ASSET, ASSET)
        + scan_skill_git_changes(PROJ, PROJ / ".claude")
        # ADR 族/经验汇总/数据集/裸写自扫：资产仓为主（跨项目决策随迁）；
        # 项目仓 decisions（B2 拆分后项目侧独立索引+ADR）同套治理对项目真值扫
        + scan_adr_governance(ASSET_REPO) + scan_adr_progression_review(ASSET_REPO)
        + scan_adr_consistency(ASSET_REPO) + scan_experience_summary(ASSET_REPO)
        + (scan_adr_governance(PROJ) + scan_adr_progression_review(PROJ)
           + scan_adr_consistency(PROJ) + scan_experience_summary(PROJ)
           if (PROJ / ".claude" / "decisions" / "adr").is_dir() else [])
        # 仓库卫生：两仓各自对 git 真值检测
        + scan_repo_hygiene(PROJ) + scan_repo_hygiene(ASSET)
        # 归口件读者端：白名单持久资产消失检测（campaign-20260916）
        + scan_persistent_assets(PROJ) + scan_persistent_assets(ASSET_REPO)
        + scan_dataset_expiration(ASSET_REPO)
        + scan_corrections_lifecycle(ASSET_REPO)
        + scan_shared_state_violations(ASSET_REPO)
        # 校准族：verdicts/reflex 日志是项目运行时；触发语料跨仓并扫（registry 同源）
        + scan_calibration_tier_quality(PROJ)
        + scan_calibration_skill_triggers(ASSET / "skills", registry)
        + scan_calibration_skill_triggers(proj_skills, registry)
        + scan_calibration_recall_quality(PROJ)
        + scan_map_counts(ASSET, PROJ / ".claude")
        + scan_finish_coverage(registry, ASSET)
        + scan_oversize_files(ASSET / "skills", ASSET)
        + scan_oversize_files(proj_skills, PROJ)
        # memory 层结构对账（平台 projects/<slug>/memory/，治理 skill 接线）
        + (scan_memory.scan_memory_signals() if scan_memory else [])
        # compact 逐字引用观察信号（T-B2）：fail-open，读取失败返回 [] 不阻断
        + (check_compact_survival.compact_survival_signals(ASSET)
           if check_compact_survival else []))
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # 裁决感知过滤：sidecar 记录主控已裁决信号（key=type|域+标识，禁行号防漂移）。
    # 解析失败 fail-loud（跳过重写），防 sidecar 损坏时静默退化为全量重报。
    def _signal_key(s: dict) -> str:
        ident = (s.get("skill") or s.get("report") or s.get("id")
                 or s.get("path") or s.get("edge") or "")
        dom = f"adr/{s['domain']}/" if s.get("domain") else ""
        return f"{s['type']}|{dom}{ident}"

    # 发射侧按 key 去重（2026-09-19 N3 修复）：PROJ=home 时双根扫描对同一信号各发
    # 一条完全同 key 的行，PENDING 派生视图不合并即同 key 双行=KPI#1 水位虚高
    # （历史实测 5 行实 3 distinct）。同 key 保首条，PENDING 是"待处理信号"视图。
    _seen: set = set()
    _deduped = []
    for _s in signals:
        _k = _signal_key(_s)
        if _k not in _seen:
            _seen.add(_k)
            _deduped.append(_s)
    signals = _deduped

    adjudicated: dict = {}
    if ADJUDICATED.exists():
        try:
            adjudicated = json.loads(ADJUDICATED.read_text(encoding="utf-8"))
            if not isinstance(adjudicated, dict):
                raise ValueError("sidecar 顶层须为 object")
        except (OSError, ValueError) as exc:
            print(f"[session-review] 裁决 sidecar 不可解析（{exc}），跳过本次 PENDING 重写"
                  "（fail-loud：宁可不写也不全量重报已裁决信号）", file=sys.stderr)
            return 1
    n_total = len(signals)
    if adjudicated:
        signals = [s for s in signals if _signal_key(s) not in adjudicated]
    if n_total:
        print(f"[session-review] 裁决过滤分母：总 {n_total} / 已裁决跳过 {n_total - len(signals)} / 重报 {len(signals)}")
    by_skill: dict[str, list[dict]] = {}
    # 按建议触发的 skill 分组（按需路由，非全链）
    if signals:
        for s in signals:
            by_skill.setdefault(s["suggest"], []).append(s)
    lines = [
        "# 待处理信号（Stop hook 自发现扫描）",
        "",
        f"> 由 session-review.py 于 {ts} 扫描生成。下次会话主控启动时读取并提示用户。",
        "> 自发现自动 + 消化分级：低风险（评估/回填/只读核验）主控自动消化仅汇报，高风险（改 skill/修代码）需用户确认。",
        "> 分级标准：`~/.claude/skills/_shared/evolution-discipline.md §信号消化分级`。",
        "> 信号消除后（已处理/已修复/verify 重跑 pass）下次扫描自动清空本文件。",
        "",
        "## 按建议 skill 分组（按需触发，非全链）",
        "",
    ]
    for skill, items in by_skill.items():
        lines.append(f"### → `{skill}`（{len(items)} 项）")
        lines.append("")
        for s in items:
            if s["type"] == "verify":
                lines.append(f"- verify `{s['report']}`: status={s['status']}, must_fix={s['must_fix']}, unresolved={s['unresolved']}, fix_rate={s['fix_rate']}")
            elif s["type"] == "evolution":
                lines.append(f"- evolution `{s['report']}`: verdict={s['verdict']}")
            elif s["type"] == "dead-skill":
                lines.append(f"- dead-skill `{s['skill']}`: 零调用+无进化+无验证+目录冷窗超 30 天")
            elif s["type"] == "stale-eval":
                lines.append(f"- stale-eval `{s['skill']}`: 执行{s['exec']}次无 EVOLUTION.md")
            elif s["type"] == "cold-skill":
                lines.append(f"- cold-skill `{s['skill']}`: 低频使用{s['exec']}次无进化无验证（lifecycle 评估删/合并/保留）")
            elif s["type"] == "hot-skill":
                lines.append(f"- hot-skill `{s['skill']}`: 高频使用{s['exec']}次从未进化（评估是否需拆分）")
            elif s["type"] == "tracked-junk":
                lines.append(f"- tracked-junk `repo`: {s['count']} 个垃圾文件已被版本记录（如 {', '.join(s['sample'][:2])}）——gitignore 不影响已跟踪文件，需 git rm --cached + 补 ignore")
            elif s["type"] == "untracked-report":
                lines.append(f"- untracked-report `repo`: {s['count']} 个报告类未 ignore（如 {', '.join(s['sample'][:2])}）——报告结论已入 .md，json 属过程，评估补 gitignore")
            elif s["type"] == "skill-changed-unsynced":
                lines.append(f"- skill-changed-unsynced `{s['skill']}`: skill 有 git 改动但 EVOLUTION.md 未同步更新（手动进化未沉淀，建议 decision-record 留 ADR）")
            elif s["type"] == "adr-governance-overdue":
                if "domain" in s:
                    lines.append(f"- adr-governance-overdue `adr/{s['domain']}/`: 单域活跃 ADR {s['count']} 份超 {s['limit']} 份上限（建议 decision-record 库治理：压缩/归档/分组复核）")
                else:
                    lines.append(f"- adr-governance-overdue `adr/`: 活跃 ADR {s['count']} 份超 {s['limit']} 份上限（建议 decision-record 库治理：压缩/归档/分组复核）")
            elif s["type"] == "adr-progression-review":
                lines.append(f"- adr-progression-review `{s['id']}`: 距今 {s['days']} 天无变更（>30 天）——层级累进复核三选：①结论稳定且通用→晋升 L3 永久规则（条款化进 CLAUDE.md/standards）②仍有效→维持 ③过时/被取代→归档（非直接清理）")
            elif s["type"] == "adr-consistency":
                lines.append(f"- adr-consistency `adr/`: {'；'.join(s['issues'][:5])}——按 KNOWLEDGE 单源对账机械回填/修复")
            elif s["type"] == "experience-summary-due":
                act = ("本机无汇总历史（本地数据不随 git 分发）——确认为主开发机后产出；克隆机可忽略"
                       if not s["days"] else "产出「经验汇总」文档落 decisions/experience/（本地，非 ADR）")
                lines.append(f"- experience-summary-due: 距上次经验汇总 {s['days'] if s['days'] else '∞'} 天且新增 {s['count']} 份——{act}")
            elif s["type"] == "dataset-stale":
                lines.append(f"- dataset-stale `{s['id']}`: 基线超 {s['days']} 天未刷新且产物其后有改动（{s['path']}）——重跑 decision-verify 刷新 last_verified 或确认后删条目")
            elif s["type"] == "dataset-orphan":
                lines.append(f"- dataset-orphan `{s['id']}`: 产物路径不存在（{s['path']}）——迁移则更新条目路径，产物已删则确认后清理")
            elif s["type"] == "shared-state-violation":
                lines.append(f"- shared-state-violation `scripts/`: {', '.join(s['files'][:5])}——共享状态文件裸写，改经 shared_state helper（flock+原子写）")
            elif s["type"] == "asset-vanished":
                lines.append(f"- asset-vanished `{s['asset']}`: {s['detail']}——核对 cleanup-ledger.jsonl 找删除者，修复后重建资产")
            elif s["type"] == "asset-missing":
                lines.append(f"- asset-missing `{s['asset']}`: {s['detail']}——观察行：确认是否需要创建，勿当删除事故处置")
            elif s["type"] == "correction-merge-due":
                lines.append(f"- correction-merge-due `{s['skill']}#{s['id']}`: new 已 {s['days']} 天未转移——条款生效则当轮转 merged@日期，未生效转 stale@日期（转移执行者=主控，本信号仅提示不代写，见 corrections 模板登记）")
            elif s["type"] == "correction-merged-cleanable":
                lines.append(f"- correction-merged-cleanable `{s['skill']}#{s['id']}`: merged 已 {s['days']} 天——教训已由条款承载，验证≥2轮后候选删行（删须主控确认）")
            elif s["type"] == "correction-stale-cleanable":
                lines.append(f"- correction-stale-cleanable `{s['skill']}#{s['id']}`: stale 已 {s['days']} 天——清理轮删除候选（删须主控确认）")
            elif s["type"] == "calibration-tier-quality":
                note = f"——{s['notes']}" if "notes" in s else ""
                lines.append(f"- calibration-tier-quality `finish-check`: 档位分布（{s['total']} 条）{s['dist']}{note}——事实汇报，升降档由用户对照 SKILL.md「梯度选择」规则裁决")
            elif s["type"] == "calibration-skill-triggers":
                parts = [f"调用 {s['calls']} 次"]
                if "missing_words" in s:
                    parts.append(f"高频词 {','.join(s['missing_words'])} 未在 description")
                if "fail_cnt" in s:
                    parts.append(f"失败 {s['fail_cnt']} 次")
                lines.append(f"- calibration-skill-triggers `{s['skill']}`: {'；'.join(parts)}——建议 description 补词/评估（改 description 须确认）")
            elif s["type"] == "calibration-recall-quality":
                lines.append(f"- calibration-recall-quality `reflex`: 召回率 {s['recall']}，打扰度 {s['disturb']}——{s['notes']}")
            elif s["type"] == "skill-file-oversize":
                lines.append(f"- skill-file-oversize `{s['path']}`: {s['lines']} 行超 {s['limit']} 行行动线——触发拆分/瘦身评估（处置分级主控自判）")
            elif s["type"] == "map-count-drift":
                lines.append(f"- map-count-drift: {s['edge']}——机械对账计数（仅汇报不回填：W2 计数口径前置未完成，真值基准 HEAD 口径留激活轮登记）")
            elif s["type"] == "memory-structure-drift":
                lines.append(f"- memory-structure-drift `memory/`: {s['edge']}——结构对账（走 memory-governance Step1→Step3 修复）")
            elif s["type"] == "compact-verbatim-observation":
                miss = "；".join(sorted({c for h in s["sample"] for c in h["missing"]}))
                lines.append(f"- compact 逐字引用观察: compact-events {s['count']}/{s['judged']} 条摘要窗口内原词未逐字引用（高频未引用：{miss}；窗口覆盖率中位 {s.get('win_cov_median')}%，含在内；词表=CLAUDE.md Compact instructions）——观察位不判定不修复")
        lines.append("")
    text = "\n".join(lines)
    if not signals:
        text = ""  # 零字节清空语义：不 unlink——unlink 与并发写入交错会产生文件存在性竞态
    if dry_run:
        print(text if text else "(no signals)")
        return 0
    # 标记外内容保全（2026-09-26 事故修复）：hook 管辖面只限本对标记之间，标记外
    # 的人写内容（如主控登记的审计发现）跨扫描原样保留。事故实证：自查轮 T32-T36
    # 仅落 PENDING 即被本脚本 03:14 全量快照冲销（找回件 digests-20260926-audit-
    # findings.md）。正确形态仍是「登记不落 PENDING」（派生视图纪律不变）；本保护
    # 只是把单点误用的代价从静默丢失降为可发现保留。零信号清空同理只清标记内。
    try:
        old = PENDING.read_text(encoding="utf-8") if PENDING.exists() else ""
    except OSError:
        old = ""
    # 旧文件里只取标记外部分（标记内的旧信号视图随本次重扫自然淘汰，不复读）
    _M = "<!-- session-review:managed"
    if _M + " start -->" in old:
        _head, _rest = old.split(_M + " start -->", 1)
        _tail = _rest.split(_M + " end -->", 1)[1] if _M + " end -->" in _rest else ""
        _ext = (_head + _tail).strip()
    else:
        _ext = old.strip()  # 旧格式无标记：整份视为主控内容（兼容迁移期）
    if text:
        text = (_M + " start -->\n" + text + "\n" + _M + " end -->\n"
                + ("\n" + _ext + "\n" if _ext else ""))
    elif _ext:
        text = _ext + "\n"  # 零信号且存在主控内容：保留主控内容，仅清 hook 视图
    # （text 空且 _ext 空 → 维持零字节清空语义）
    # 锁内原子写：多 session 并发 Stop 各产全量快照，锁串行化写者、原子替换保护
    # 无锁读方（session-start）。全量快照语义 = 最新磁盘真值胜出，无需行级合并；
    # 旧快照后写短暂保留已消信号由下次 Stop 重扫自愈（PENDING 是派生视图）。
    try:
        with flock_ctx("pending"):
            atomic_write(PENDING, text)
    except TimeoutError:
        print("[session-review] PENDING 锁超时，跳过写（下次 Stop 重扫自愈）", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
