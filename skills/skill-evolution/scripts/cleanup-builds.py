#!/usr/bin/env python3
"""cleanup-builds.py — Stop hook 自动清理各 skill 的 .build/ 中间产物。

为什么 Stop hook（非手动）：用户选自动清——每次会话结束清陈旧防积压。
中间产物可重建（是迭代过程的 JSON 快照，结论已入最终产物），故门槛低于 skill
文件改动，无需逐次确认。脚本只 unlink 匹配模式的文件（毫秒级，无重计算）。

迭代轮次类（review/fix/red-team round、consensus round、PCF 三件套）带 final 守卫：
仅当同 .build 目录存在对应收敛标志（report.review.final / consensus.final /
review.pcf.final）时才清理——防 Stop hook 在跨 turn 迭代进行中误清活跃 round。

保留项（最终产物 + 指标快照）靠「不匹配清理模式」天然安全，不建白名单索引：
  verify-report / consensus.final / lifecycle-decision / report.review.final /
  review.pcf.final / loop-summary / metrics.latest / clarified-requirements

不触碰 prd-generator 的 .build（由其 post_update.py 管理，命名模式不重叠）。

2026-08-16 进化（用户裁决「不留中间过程」）：
  - 仓库级 .claude/.build/ 改白名单反转——只留反射层运行数据（reflex-hooks.jsonl /
    weekly-eval.marker / reflex 状态文件与共享状态锁目录），验证报告/测试脚本/夹具全清
    （旧模式法漏网实证）
  - plans/ 归档 >7 天清理（过程档案无消费者，曾积 41 文件无一被再读）
分类依据见 references/cleanup-rules.md「decision-skill 中间产物」节。
"""
from __future__ import annotations

import argparse
import sys
import json
import subprocess
import time
from pathlib import Path

# 迭代轮次类中间产物 → 收敛标志：仅当同 .build 目录存在对应 final 时才清理。
# 为什么 final 守卫：Stop hook 每次会话结束触发，但跨 turn 进行中的迭代
# （尚未产出 final）其 round 报告仍活跃——无守卫会被误清，致迭代丢失报告。
GUARDED_PATTERNS = {
    "report.review.round.*.json":       "report.review.final.json",
    "report.fix.round.*.json":          "report.review.final.json",
    "report.red-team*.json":            "report.review.final.json",
    "consensus.round*.proposal.*.json": "consensus.final.json",
    "consensus.round*.summary.json":    "consensus.final.json",
    "review.pcf.round.*.json":          "review.pcf.final.json",
}
# 单次产物（非迭代轮次，无收敛标志，始终可清）。
# report.evolution.json 不在此列：被 session-review.py 断环检测消费
# （Stop hook 顺序 cleanup→session-review，先删破坏断环），由 evolve 流程自行清理。
# 单次产物均本地保留（debates.md 等），无始终可清的非迭代产物。
UNGUARDED_PATTERNS = ()


def _repo_root() -> Path:
    # 双根（迁移 ~/.claude 后）：项目根走 cwd 上溯（运行时数据随项目）；
    # 资产根 skill 级 .build 在 main 内单独并扫
    from shared_state import data_claude
    return data_claude().parent


def find_build_dirs(repo: Path) -> list[Path]:
    # 找所有 .build 目录；排除 prd-generator（其 post_update.py 自管 PRD 产物）
    builds = []
    for p in repo.rglob(".build"):
        if p.is_dir() and "prd-generator" not in p.parts:
            builds.append(p)
    return builds


# 仓库级 .build（.claude/.build）走白名单反转：只保留反射层运行数据，其余全清。
# 为什么与 skill 级不同策略：用户 2026-08-16 裁决「不留中间过程」——验证报告/测试
# 脚本/夹具的结论当轮已汇报进对话，文件即过程；旧模式匹配法（只清 round.*）对
# 命名不符合模式的报告全漏网（实证：3 份验证报告+测试脚本滞留）。白名单一次封死。
# locks/ 必须在列：删掉锁目录会破坏 flock 互斥（unlink 锁文件后新旧持锁者锁不同
# inode），且持锁进程的锁随文件删除悬空；reflex-state.json 保留至旧文件迁移完成。
# weekly-eval-report.md 必须在列（2026-09-13 战役 F3）：cron 产出的周评估报告是主控
# 「读结论后处置」的唯一输入，曾因不在白名单被本脚本删除致周评估链空转 77 次。
# weekly-eval-analysis.marker 落资产根 ~/.claude/.build（非项目根），本函数现不扫资产根——
# 若未来扫描面扩到资产根，该 marker 须一并入白名单（节流纪元被删=分析段天天重烧模型）。
REPO_BUILD_WHITELIST = {"reflex-hooks.jsonl", "reflex-state.json",
                        "reflex-start-state.json", "reflex-stop-state.json",
                        "weekly-eval.marker", "weekly-eval-report.md", "locks",
                        # 2026-09-16 战役 D1 实证：周期宿主资产曾因不在列被本脚本清空
                        # （evolution-daily.log 蒸发、pending-history.jsonl 丢失致 age 恒 0）
                        "evolution-daily.log", "pending-history.jsonl",
                        "joint-review.marker", "reflex-pending.marker",
                        # 2026-09-27 进化批/外参节律锚（ADR evolution-cadence-tiers 追加节，
                        # 双宿主：写者=weekly-eval.py/主控，读者=weekly-eval.py+主控）
                        "evolution-batch.marker", "last-external-action.marker",
                        # cleanup-ledger=台账本尊（原 campaign.final.md 白名单随战役机制移除）
                        "cleanup-ledger.jsonl",
                        # quarantine=U7 回滚指针暂存区（mode-verify #17）：移入而非直删，
                        # 白名单防止递归自清（TTL 归 _prune_quarantine，不靠白名单续命）
                        "quarantine"}

# U7 申诉并置回滚指针（campaign-20260917-mode-verify #17）：.build 独有件移 quarantine/
# 暂存而非直删，ledger 条目带 restore_hint（误删恢复路径=回移一行 mv）；TTL 过后真删。
QUARANTINE = "quarantine"
QUARANTINE_TTL_DAYS = 7.0


def _prune_quarantine(qroot: Path, dry_run: bool) -> None:
    """quarantine TTL 清理：超 QUARANTINE_TTL_DAYS 的暂存日期目录真删（回滚窗口已过）。"""
    if not qroot.is_dir():
        return
    cutoff = time.time() - QUARANTINE_TTL_DAYS * 86400
    for d in qroot.iterdir():
        try:
            if d.is_dir() and d.stat().st_mtime < cutoff and not dry_run:
                import shutil
                shutil.rmtree(d)
        except OSError:
            pass


def _referenced_in_decisions(name: str) -> bool:
    """S5 窄化补强（mode-verify #10）：白名单外持久项删除前对 decisions/ 做一跳引用 grep——
    ADR/裁决引用中的件不是纯过程产物，直删即复现 asset-vanished（D1 实证）。存在性触发
    非全量对账（org-formations 收编条 5：防江南奏销案式扩大化）；grep 失败按被引用处理
    （宁留勿删，与 _contains_whitelisted 同款 fail-closed）。"""
    asset = Path.home() / ".claude"
    roots = [r for r in (asset / "decisions", asset / "skills" / "skill-evolution" / "decisions") if r.is_dir()]
    if not roots:
        return False
    try:
        r = subprocess.run(["grep", "-rl", "--", name, *[str(p) for p in roots]],
                           capture_output=True, timeout=15)
        return r.returncode == 0
    except Exception:
        return True


# 近期活跃底限：Stop 钩子由任意会话触发，另一会话在途的验证夹具/测试脚本可能刚
# 写入——mtime 在此窗口内跳过，防跨会话误删活跃产物（验证夹具写入发生在分钟级）。
RECENT_FLOOR = 3600


def _contains_whitelisted(p: Path) -> bool:
    """子目录资产保护：iterdir 顶层按名匹配保护不了白名单资产嵌在待删子目录内
    的情况——删除前须查后代，否则随父目录 rmtree 一并蒸发（漏保修复 2026-09-16）。"""
    try:
        return any(c.name in REPO_BUILD_WHITELIST for c in p.rglob("*"))
    except OSError:
        return True  # 遍历失败按可能含白名单资产处理，宁留勿删


def _prune_dir(d: Path, dry_run: bool, removed: list[str]) -> None:
    """删子目录内容但跳过白名单条目（含嵌套），目录壳保留以守护白名单资产。"""
    for c in list(d.iterdir()):
        if c.name in REPO_BUILD_WHITELIST:
            continue
        if c.is_dir():
            _prune_dir(c, dry_run, removed)
        else:
            if not dry_run:
                try:
                    c.unlink()
                    removed.append(str(c))
                except OSError:
                    pass
            else:
                removed.append(str(c))
    # 目录壳若已空且自身非白名单，交由上层 rmtree 语义保持——此处不删壳，
    # 防止「壳删除后白名单判定锚点丢失」；空壳对 .build 语义无害。


def clean_repo_build(repo: Path, dry_run: bool) -> list[str]:
    """仓库级 .build：非白名单且超过活跃底限的全清（含子目录如 test-fixtures/）。
    删除动作两道前置门（mode-verify #10/#17）：decisions/ 一跳引用 grep（被引用=留）+
    .build 独有件移 quarantine/ 暂存（restore_hint 回滚窗口 TTL 后真删）。"""
    repo_build = repo / ".claude" / ".build"
    removed = []
    if not repo_build.is_dir():
        return removed
    _prune_quarantine(repo_build / QUARANTINE, dry_run)
    now = time.time()
    for f in repo_build.iterdir():
        if f.name in REPO_BUILD_WHITELIST:
            # reflex-hooks.jsonl 截断归口 daily-archive._truncate_reflex_hooks（阈值单源
            # io-budgets.reflex_hooks_truncate_lines），此处不重复设机制（双源防漂移）
            continue
        try:
            if now - f.stat().st_mtime < RECENT_FLOOR:
                continue
        except OSError:
            pass
        if _referenced_in_decisions(f"{f.parent.name}/{f.name}" if f.parent.name != QUARANTINE else f.name):
            continue  # S5 引用对账命中：被 decisions/ 引用的持久项不删（宁留勿删）
        if dry_run:
            removed.append(str(f))
            continue
        try:
            before = len(removed)
            hint = ""
            if f.is_dir() and _contains_whitelisted(f):
                # 含白名单资产的目录不整体 rmtree，只剪非白名单内容（漏保修复）
                _prune_dir(f, dry_run, removed)
            else:
                # U7 回滚指针：.build 独有件移 quarantine/<date>/，恢复=一行 mv 回移
                qdir = repo_build / QUARANTINE / time.strftime("%Y-%m-%d")
                qdir.mkdir(parents=True, exist_ok=True)
                import shutil
                qpath = qdir / f.name
                shutil.move(str(f), str(qpath))
                hint = str(qpath)
                removed.append(str(f))
            # 删除台账（dept-evolution 首批裁决件，asset-vanished 追溯唯一凭据）：
            # append-only 一行一删；restore_hint=quarantine 回滚指针（U7，无暂存时留空）。
            if len(removed) > before:
                try:
                    with open(repo_build / "cleanup-ledger.jsonl", "a", encoding="utf-8") as lf:
                        lf.write(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
                                             "path": str(f), "by": "cleanup-builds",
                                             "restore_hint": hint},
                                            ensure_ascii=False) + "\n")
                except OSError:
                    pass
        except OSError:
            pass
    return removed


def clean_stale_plans(repo: Path, dry_run: bool, max_age_days: float = 7.0) -> list[str]:
    """plans/ 归档清理：>7 天的 plan 文件删除。

    plan 是过程档案（gitignored），harness 只在活跃会话引用最新 plan——
    停滞超周的旧 plan 无消费者，实证 41 个文件积 432K 无一被再读。
    """
    import time
    removed = []
    plans_dir = repo / ".claude" / "plans"
    if not plans_dir.is_dir():
        return removed
    cutoff = time.time() - max_age_days * 86400
    for f in plans_dir.glob("*.md"):
        try:
            if f.stat().st_mtime < cutoff:
                if dry_run:
                    removed.append(str(f))
                else:
                    f.unlink()
                    removed.append(str(f))
        except OSError:
            pass
    return removed


def _unlink_matching(build_dir: Path, pattern: str, guard_path: Path | None,
                     dry_run: bool) -> list[str]:
    removed = []
    # 收敛纪元：round 文件 mtime 必须不晚于 final——final 既是收敛标志也是时间纪元。
    # 为什么不用绝对活跃窗口：跨会话误删场景是「另一会话 final 后续写新轮次」
    # （如修复后再评审），新 round mtime 必晚于 final；绝对窗口对「会话闲置中场
    # 但迭代仍活」无法区分、对「final 后 10 分钟续写新轮」又太钝。纪元两案通吃。
    guard_mtime = None
    if guard_path is not None:
        try:
            guard_mtime = guard_path.stat().st_mtime
        except OSError:
            return removed  # final 刚被并发删除：视为迭代进行中，保守保留
    for f in build_dir.glob(pattern):
        if not f.is_file():
            continue
        try:
            if guard_mtime is not None and f.stat().st_mtime > guard_mtime:
                continue  # 晚于纪元的轮次 = 仍在进行中的迭代，保留（宁留勿误删）
        except OSError:
            continue
        if dry_run:
            removed.append(str(f))
        else:
            try:
                f.unlink()
                removed.append(str(f))
            except OSError:
                pass
    return removed


def clean_build(build_dir: Path, dry_run: bool) -> list[str]:
    removed = []
    # 守卫类：仅当对应收敛标志（final）存在时才清理——迭代进行中（无 final）保留 round
    for pattern, guard in GUARDED_PATTERNS.items():
        if not (build_dir / guard).exists():
            continue
        removed.extend(_unlink_matching(build_dir, pattern, build_dir / guard, dry_run))
    # 单次产物：始终可清（无收敛标志）
    for pattern in UNGUARDED_PATTERNS:
        removed.extend(_unlink_matching(build_dir, pattern, None, dry_run))
    return removed


def main() -> int:
    parser = argparse.ArgumentParser(description="清理各 skill .build/ 中间产物")
    parser.add_argument("--dry-run", action="store_true", help="只列清单不删除")
    args = parser.parse_args()

    builds = find_build_dirs(_repo_root())
    total = []
    for b in builds:
        total.extend(clean_build(b, args.dry_run))
    # 资产仓 skill 级 .build（11 迁移 skill）：与项目仓同守卫规则清理
    from shared_state import asset_claude
    for b in find_build_dirs(asset_claude()):
        total.extend(clean_build(b, args.dry_run))
    # 仓库级白名单清理与 plans 归档（skill 级 .build 之外的进化面，2026-08-16）
    # 只清项目根——资产仓无 .claude/.build 与 plans（运行时数据随项目裁决）
    repo_removed = clean_repo_build(_repo_root(), args.dry_run)
    total.extend(repo_removed)
    total.extend(clean_stale_plans(_repo_root(), args.dry_run))

    if args.dry_run:
        if total:
            print("待清理（--dry-run，不实际删除）：")
            for f in total:
                print(f"  {f}")
        else:
            print("无中间产物需清理")
    else:
        # hook 模式：输出到 stderr，不污染会话 stdout
        print(f"[cleanup] 清理 {len(total)} 个中间产物", file=sys.stderr)
        # 清理台账（campaign-20260916 归口件）：删除动作必须可溯源——D1 实证
        # 「蒸发者不可考」的根因就是删除无留痕。append-only，读者=asset-vanished 扫描。
        if total:
            try:
                ledger = asset_claude() / ".build" / "cleanup-ledger.jsonl"
                ledger.parent.mkdir(parents=True, exist_ok=True)
                import json as _json
                with ledger.open("a", encoding="utf-8") as fh:
                    for t in total:
                        # 仓库级删除已由 clean_repo_build 自带台账（含 quarantine
                        # restore_hint）落行——此处再写即双行误读（T39-H2 实证
                        # 10 事件记成 20）。跳过防重。
                        if t in repo_removed:
                            continue
                        fh.write(_json.dumps({
                            "date": time.strftime("%Y-%m-%d %H:%M:%S"),
                            "target": t,
                            "path": t,  # finish-check F-B1 轮1：补 path 键——session-review:814 只读 path，缺省致 skill 级删除对 vanished 检测恒不可见
                            "reason": "cleanup-builds stop-hook",
                            "actor": "cleanup-builds.py",
                            "restore_hint": "",  # skill 级直删件无暂存（U7 仅覆盖仓库级 .build 独有件）
                        }, ensure_ascii=False) + "\n")
            except OSError:
                pass  # 台账失败不阻断清理主流程，但 P-A3-1 判据会捕获此类静默
    return 0


if __name__ == "__main__":
    sys.exit(main())
