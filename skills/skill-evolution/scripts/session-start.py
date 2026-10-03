#!/usr/bin/env python3
"""session-start.py — SessionStart 钩子：开局把 PENDING 积压喂回主控。

闭合自进化环的「最后一跳」：session-review.py(Stop) 已自动扫描信号并产出
PENDING.md，但主控开局没有任何机制去读它 → 积压无人跟进（已实证积压 4 条）。
本脚本在会话启动时读 PENDING，非空则 stdout 输出摘要，借 SessionStart 的
additionalContext 注入会话开头。指令按信号三档分级：
低风险（评估/回填/只读核验）自动消化仅汇报；中风险（待办型：库治理/经验汇总）
开局仅汇报、挂周评估批量确认一次；高风险（涉改 skill/复盘缺陷）仍 AskUserQuestion——
待办型信号不再每次会话打断用户。注入本身走 digest_days 节流（backlog-periodic-digest：
积压归定期批次，窗口内只留指针，到期或周评估时统一消化）。
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# 共享状态读写唯一通道：写者分区——本脚本只写 start-state（pending_seen），
# reflex-check 只写 stop-state；flock 兜底多 session 同写者并发。
# 双根（迁移 ~/.claude 后）：ASSET=单源资产（PENDING/signal-tiers 随迁），
# REPO=项目根（reflex 运行数据随项目走）。
from shared_state import asset_claude, atomic_write, data_claude, flock_ctx, io_budget, load_partition


ASSET = asset_claude()
REPO = data_claude().parent
PENDING = ASSET / "decisions" / "postmortems" / "PENDING.md"
STATE_START = REPO / ".claude" / ".build" / "reflex-start-state.json"


def _append_log(entry: dict) -> None:
    """运行数据采集：开局积压量落日志，支撑一周后评估分级消化效果。
    过 rotate_jsonl（T116 第三写者补线，2026-09-28 对抗臂残留项：三写者同闸，
    单改两个会漏本写者）。"""
    try:
        from shared_state import rotate_jsonl
        rotate_jsonl(REPO / ".claude" / ".build" / "reflex-hooks.jsonl", "reflex_hooks")
        path = REPO / ".claude" / ".build" / "reflex-hooks.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:  # noqa: BLE001 — 日志失败不影响 hook 主流程
        pass


def _slim_weekly_eval(full: str, report_path: Path) -> str:
    """T90 注入瘦身（2026-09-27）：周评估报告「摘要+指针」模式。
    保留：①含 ⚠/✗ 的行原样（主控异常信号）②含「缺口」的行原样（登记类信号）
    ③✅/指标行只留行名（首个 ：/，前的指标名）不计详情。末尾附完整报告落盘指针。
    全文已在 report_path 落盘，直接指过去不建副本；读不到全文时降级为
    落 .claude/.build/weekly-eval-latest.md 再指（fallback 通道）。
    """
    keep: list[str] = []
    ok_names: list[str] = []
    for ln in full.splitlines():
        if "⚠" in ln or "✗" in ln or "缺口" in ln:
            keep.append(ln)
        elif ln.startswith("- ✅"):
            ok_names.append(re.split(r"[：,，]", ln, 1)[0].lstrip("- ✅ "))
        # 其余行（子列表/聚合行）全部丢弃——均在落盘报告中可查
    if ok_names:
        keep.append(f"- ✅ 达标 {len(ok_names)} 项：{'；'.join(ok_names)}（详情见完整报告）")
    out = "\n".join(keep)
    out += (f"\n\n（T90 瘦身注入：仅保留异常信号行与达标项名；完整报告见 `{report_path}`，"
            "WEEKLY_EVAL_FULL=1 回全量注入。）")
    return out


def _adr_knowledge_proposal(ln: str, claude_dir: Path) -> list[str]:
    """方案 C（autonomous-evolution-design）patch-ready 提案：adr-consistency 的
    KNOWLEDGE 缺条目子类 → 生成 KNOWLEDGE 条目行文本，附在注入后供用户确认才改。
    提案只进 stdout 不回写 PENDING——PENDING 行被类型解析/狼来了摘要/50 行截断
    三重消费，行文本变更会使去重失真并挤占截断额度。本正则锚 `KNOWLEDGE 缺条目`
    与 session-review 渲染短语两侧互指，改一须同步。
    返回 (提案行, slug 清单) 二元组——slug 供 proposal 事件留痕，激活判据
    （autonomous-evolution-design:22 确认率）可按 slug 对账 KNOWLEDGE.md 实际新增。
    """
    try:
        m = re.search(r"KNOWLEDGE 缺条目 ([\w\-,]+)", ln)
        if not m:
            return [], []
        out: list[str] = []
        slugs: list[str] = []
        for slug in m.group(1).split(",")[:3]:
            adr_base = claude_dir / "decisions" / "adr"
            dom_path = next(((dom, adr_base / dom / f"{slug}.md")
                             for dom in ("meta", "data")
                             if (adr_base / dom / f"{slug}.md").exists()),
                            None)
            if dom_path is None:
                continue
            dom, path = dom_path
            text = path.read_text(encoding="utf-8")
            fm = dict(re.findall(r"^(title|status):\s*(.+)$", text, re.M))
            # title 缺失（部分 ADR 靠 H1 承载标题）→ 回退 H1，再回退 slug
            m_h1 = re.search(r"^# (.+)$", text, re.M)
            title = (fm.get("title") or (m_h1.group(1).strip() if m_h1 else slug))
            out.append(f"  ↳ 提案（确认才改）：KNOWLEDGE.md 对应 tag 节追加 `- [{title}](adr/{dom}/{slug}.md) | adr | （摘要待补 ≤30 字） | 链: -`")
            slugs.append(slug)
        return out, slugs
    except Exception as _e:  # noqa: BLE001 — 留痕批：静默空列表曾使沉淀链路断裂无痕（B2-4）
        print(f"[session-start] ADR 提案生成失败（跳过）：{_e}", file=sys.stderr)
        return [], []


def main() -> int:
    # hook 不能阻断主流程：任何异常 stderr 可见 + exit 0，绝不抛给会话
    try:
        # 从 stdin 读 session_id（与 reflex-check.py 同款）：此前硬编码 "nosession"
        # 导致跨会话数据无法区分，周评估按会话聚合时失真
        session_id = "nosession"
        try:
            raw = sys.stdin.read()
            if raw.strip():
                session_id = str(json.loads(raw).get("session_id") or "nosession")
        except Exception:
            pass
        # T38② CPE 缓解（2026-09-26）：项目级 .claude/settings.json 含 hooks 配置时
        # stderr 警示（论文 C-4 向量=恶意仓预置项目 hooks → bypassPermissions 下
        # 无批准执行；用户级托管校验缺位，最低成本缓解=可见性警示，不阻断）
        try:
            _ps = Path.cwd() / ".claude" / "settings.json"
            if _ps.is_file() and "hooks" in _ps.read_text(encoding="utf-8"):
                print(f"[session-start] ⚠ 本项目 {_ps} 含 hooks 配置（CPE C-4 注入向量面，"
                      "确认系本人配置而非仓库自带；hooks 命令将以本机权限执行）", file=sys.stderr)
        except Exception:
            pass
        # T81 数据源新鲜度体检（2026-09-27 包A残·中档）：解释器一动 9-hook 同断且各自无声
        # （recall 断流 7 天系首例非孤例）——开局一行体检：关键资产存在性+周报时效，只告警不阻断
        try:
            _checks = [
                ("KNOWLEDGE", ASSET / "decisions" / "KNOWLEDGE.md", None),
                ("PENDING", ASSET / "decisions" / "postmortems" / "PENDING.md", None),
                ("recall脚本", ASSET / "skills" / "skill-evolution" / "scripts" / "knowledge-recall.py", None),
                ("周报", ASSET / ".build" / "weekly-eval-report.md", 7),  # T88 读方收锚（2026-09-27）：原幻影嵌套根
            ]
            _stale = []
            for _name, _p, _days in _checks:
                if not _p.exists():
                    _stale.append(f"{_name} 缺失({_p})")
                elif _days and (time.time() - _p.stat().st_mtime) > _days * 86400:
                    _stale.append(f"{_name} 超{_days}天未刷新")
            if _stale:
                print(f"[session-start] ⚠ 数据源新鲜度体检：{'；'.join(_stale)}"
                      "（解释器/路径漂移嫌疑，T81 B1⑩）\n", file=sys.stderr)
        except Exception:
            pass
        # 模型键回归自检（PCF 20260919 双档终裁）：换号工具会重写 settings 抹掉治理值，
        # 已复发 3 次。只告警不改值——自动改写会与用户合法换号冲突，判定权留给用户/主控。
        # 告警值锚死 ADR 记载值；读失败按 fail-open 静默（hook 禁阻断主流程）。
        try:
            expected_main = "glm-5.3-flash[1M]"  # 单源：adr/meta/model-tier-main-only-key-nodes.md 追加 4（2026-09-21 会话默认改 sonnet）
            settings_path = Path.home() / ".claude" / "settings.json"
            actual = (json.loads(settings_path.read_text(encoding="utf-8"))
                      .get("env", {}).get("ANTHROPIC_MODEL"))
            if actual and actual != expected_main:
                print(f"[session-start] ⚠ ANTHROPIC_MODEL 漂移：现值 {actual}，ADR 记载值 {expected_main}"
                      f"（换号工具重写嫌疑，裁决见 model-tier-main-only-key-nodes 追加 3/4；恢复须人工裁决）\n")
                _append_log({"ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                             "hook": "session-start", "session_id": session_id,
                             "event": "model-key-drift", "actual": actual})
        except Exception:
            pass
        # 周评估到期检测：评估指标与 jq 命令早已定义但无触发宿主，效果数据积累无人消费
        # （反射层自身效果无人评——元层反馈回边悬空）。到期判定与 weekly-eval.py 周日锚
        # 同构（marker 日期早于本周日锚即到期）——原 mtime 滚动 7 天与脚本日期锚错拍：
        # 周六消费后周日重算的新报告会被本处节流吞掉最长 6 天（逆向审查 High-1 修复）。
        # 评估只读属低风险。检测必须在 PENDING 的 early-return 之前，否则无积压会话永远漏检。
        marker = REPO / ".claude" / ".build" / "weekly-eval.marker"
        due = True
        try:
            if marker.exists():
                days_since_sunday = (datetime.now().weekday() + 1) % 7
                week_anchor = (datetime.now() - timedelta(days=days_since_sunday)).date()
                marker_day = datetime.fromtimestamp(marker.stat().st_mtime).date()
                due = marker_day < week_anchor
        except Exception:
            pass  # stat 失败按到期处理：宁可多提醒一次，不可静默漏检
        if due:
            # 指标计算已下沉 cron 脚本 weekly-eval.py（model-governance 裁决：采集分析
            # 禁实时进模型）；主控只读报告结论做处置，主控消化后自行 touch marker。
            report = REPO / ".claude" / ".build" / "weekly-eval-report.md"
            print("## 周评估到期（weekly-eval-due）\n")
            if report.exists():
                _full = report.read_text(encoding="utf-8").strip()
                # T90 注入瘦身（2026-09-27）：全量报告 ~4.2k 字符/次会话，
                # 主控真正要读的只有异常信号；改「摘要+指针」——⚠/✗/缺口登记行原样
                # 保留（主控信号），✅ 类行只留行名不计详情，末尾指回完整报告落盘路径。
                # 报告全文已有落盘（weekly-eval-report.md），不新建副本；无落盘场景
                # （本分支不触达）留 fallback 落 latest.md 以防未来读口变更。
                # WEEKLY_EVAL_FULL=1 回全量（向后兼容逃生口）。
                if os.environ.get("WEEKLY_EVAL_FULL") == "1":
                    print(_full)
                else:
                    print(_slim_weekly_eval(_full, report))
                print("\n↑ 指标由 cron 脚本预计算（零模型）。主控只读结论：异常指标按切片排查+抽样复核，中风险待办批量确认（AskUserQuestion multiSelect），只读仅汇报；完成后 `touch .claude/.build/weekly-eval.marker`（项目侧）。")
            else:
                print("周评估报告缺失（cron 脚本 weekly-eval.py 未产出）：跑 `python3 ~/.claude/skills/skill-evolution/scripts/weekly-eval.py <项目根>` 生成后再消化，主控不做实时 jq 计算。\n")

            _append_log({"ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                         "hook": "session-start", "session_id": session_id,
                         "event": "weekly-eval-due"})
        text = PENDING.read_text(encoding="utf-8").strip() if PENDING.exists() else ""
        if not text:
            _append_log({"ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                         "hook": "session-start", "session_id": session_id,
                         "event": "none", "pending_low": 0, "pending_high": 0})
            return 0
        # 周期节流（backlog-periodic-digest）：积压注入不再每会话展开——信号已由
        # 狼来了折叠压噪，但每次开局仍整段注入干扰用户。归定期批次（digest_days
        # 窗口，与周评估同频）：到期注入即 touch marker，窗口内只留一行指针。
        # 信号仍在 PENDING.md 不丢，批次到期时由周评估统一规划消化。fail-open：marker/预算异常按到期处理。
        pend_marker = REPO / ".claude" / ".build" / "reflex-pending.marker"
        _pend_cfg = io_budget("pending_injection")
        digest_days = int((_pend_cfg or {}).get("digest_days") or 0)
        if _pend_cfg is None or "digest_days" not in _pend_cfg:
            # on_read_fail=TIGHT（io-budgets 语义表）：预算不可读≠无预算，按最严执行
            # ——本轮只留指针不注入正文。原 fail-open 全量注入方向恰与截断防超支语义相反
            #（campaign-20260916 簇2 首批修复件）。
            print("[session-start] pending_injection 预算不可读，本轮只留指针（fail-tight）")
            print(f"完整清单见 `~/.claude/decisions/postmortems/PENDING.md`，按 severity 优先消化。")
            _append_log({"ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                         "hook": "session-start", "session_id": session_id,
                         "event": "pending-budget-unreadable"})
            return 0
        due_digest = True
        try:
            if digest_days > 0 and pend_marker.exists():
                due_digest = (datetime.now().timestamp() - pend_marker.stat().st_mtime
                              > digest_days * 86400)
        except Exception:  # noqa: BLE001 — stat 失败宁可多提示一次
            pass
        if not due_digest:
            n_sig = sum(1 for ln in text.splitlines() if ln.startswith("- "))
            print(f"[session-start] 自进化积压 {n_sig} 条已入定期批次（{digest_days} 天窗口内"
                  f"不重复展开，到期或周评估时统一消化）；"
                  f"完整清单见 `~/.claude/decisions/postmortems/PENDING.md`。"
                  f"近 7 天探索轮末总账见 `~/.claude/decisions/postmortems/BACKLOG.md` 尾部，"
                  f"同题开工前先查（2026-09-25 方向E C3 补链）。")
            _append_log({"ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                         "hook": "session-start", "session_id": session_id,
                         "event": "pending-throttled", "pending_total": n_sig})
            return 0
        pend_marker.touch()
        print("## 自进化积压（session-review 自动发现，待消化）\n")
        # 注入预算数值单源 io-budgets.pending_injection（P0-1 清偿）；fail-closed=
        # 预算不可读时不注入正文只留指针（信号仍在 PENDING.md 不丢，开局零过载）
        pend_cfg = io_budget("pending_injection") or {}
        pending_max_lines = int(pend_cfg.get("max_lines") or 0)
        muted_after = int(pend_cfg.get("muted_after_reminds") or 0)
        if pending_max_lines <= 0 or muted_after <= 0:
            print("[session-start] io-budgets.pending_injection 不可读，本轮只留指针（fail-closed）")
            print(f"完整清单见 `~/.claude/decisions/postmortems/PENDING.md`，按 severity 优先消化。")
        else:
            # 积压过多时截断防开局 token 过载：保留分组标题 + 前若干条，其余提示见原文
            lines = text.splitlines()
            if len(lines) > pending_max_lines:
                print("\n".join(lines[:pending_max_lines]))
                print(f"\n…另有 {len(lines) - pending_max_lines} 行信号，完整见 `~/.claude/decisions/postmortems/PENDING.md`，按 severity 优先消化。")
            else:
                print(text)
        # 解析 PENDING 信号行，按类型分级给消化指令（标准：_shared/evolution-discipline.md §信号消化分级）。
        # 低风险 = 评估/回填/只读核验（产物可逆）；中风险 = 待办型（库治理/经验汇总，
        # 需用户裁决但不紧急）；高风险 = 涉改 skill 逻辑或复盘真实缺陷。
        # 分级真值单源于 _shared/signal-tiers.json（新增类型改 JSON 即可）；不设代码内兜底集合
        # （避免 JSON↔代码两处同改）——读取失败留空集合并全归 high，保守侧安全。
        import re
        _tiers_file = ASSET / "skills" / "_shared" / "signal-tiers.json"
        try:
            _tiers = json.loads(_tiers_file.read_text(encoding="utf-8"))
            low_risk_types = set(_tiers["low_risk_types"])
            mid_risk_types = set(_tiers["mid_risk_types"])
        except Exception:
            low_risk_types, mid_risk_types = set(), set()
        cur_skill = None
        low_items: list[str] = []
        mid_items: list[str] = []
        high_groups: dict[str, int] = {}
        for ln in lines:
            if ln.startswith("### → "):
                m = re.match(r"### → `([^`]+)`", ln)
                cur_skill = m.group(1) if m else ln
            elif ln.startswith("- "):
                sig_type = ln[2:].split(" ", 1)[0].strip("` ")
                if sig_type in low_risk_types:
                    low_items.append(ln)
                elif sig_type in mid_risk_types:
                    mid_items.append(ln)
                elif cur_skill:
                    high_groups[cur_skill] = high_groups.get(cur_skill, 0) + 1
        _append_log({"ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                     "hook": "session-start", "session_id": session_id,
                     "event": "pending", "pending_low": len(low_items),
                     "pending_mid": len(mid_items),
                     "pending_high": sum(high_groups.values())})
        # 「狼来了」抑制：同一条信号跨会话反复注入而无人消化（如长期不用的 skill 的
        # baseline-gap——魔鬼测试成长验证实证：同一信号已注入 4+ 次仍每会话全文展开），
        # 用户会麻木进而忽略新出现的真信号。第 3 次起不再展开只留一行计数——
        # 信号本身仍在 PENDING.md 不丢，仅开局注入降噪（≥2 次真实重现后才建的机制）
        import hashlib
        fresh_low, muted = [], 0
        fresh_mid, muted_mid = [], 0
        try:
            # 计数与分级在锁内一体完成：分级依赖计数真值，锁外预读再写回会基于
            # 陈旧快照丢更新（多 session 并发 SessionStart 时后写覆盖先写）。
            # 锁内操作毫秒级，锁持有时间可忽略。
            with flock_ctx("reflex-start"):
                st = load_partition("start")
                seen: dict = st.get("pending_seen") or {}
                for ln, bucket in [(ln, "low") for ln in low_items] + [(ln, "mid") for ln in mid_items]:
                    digest = hashlib.sha256(ln.encode()).hexdigest()[:16]
                    seen[digest] = seen.get(digest, 0) + 1
                    if seen[digest] < muted_after:
                        (fresh_low if bucket == "low" else fresh_mid).append(ln)
                    elif bucket == "low":
                        muted += 1
                    else:
                        muted_mid += 1
                # 保留最近 100 键防状态文件膨胀
                if len(seen) > 100:
                    seen = dict(list(seen.items())[-100:])
                st["pending_seen"] = seen
                atomic_write(STATE_START, json.dumps(st, ensure_ascii=False))
        except TimeoutError:
            print("[session-start] start-state 锁超时，跳过计数写", file=sys.stderr)
        except Exception:  # noqa: BLE001 — 计数持久化失败不影响注入主流程
            pass
        print("\n---\n主控动作（信号分级，标准：`~/.claude/skills/_shared/evolution-discipline.md §信号消化分级`）：")
        if fresh_low:
            print(f"\n**低风险（{len(fresh_low)} 项）→ 主控直接消化，仅汇报结果**（评估/回填/只读核验，不 AskUserQuestion；消化中若需改 skill 逻辑或删文件 → 升级为高风险先问）：")
            proposal_sent = 0
            for ln in fresh_low:
                print(ln)
                # 方案 C 提案只挂未 mute 的 adr-consistency 行（mute 行已被狼来了折叠，
                # 提案随其自然抑制）；全会话 ≤3 条防注入膨胀
                if (ln[2:].split(" ", 1)[0].strip("` ") == "adr-consistency"
                        and proposal_sent < 3):
                    gen, slugs = _adr_knowledge_proposal(ln, ASSET)
                    for p in gen:
                        print(p)
                    if gen:
                        proposal_sent += 1
                        _append_log({"ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                     "hook": "session-start", "session_id": session_id,
                                     "event": "proposal", "type": "adr-consistency",
                                     "slugs": ",".join(slugs)})
        if muted:
            print(f"\n**另有 {muted} 条已知信号已提醒 ≥{muted_after} 次未消化，不再展开**（多为等待真实使用的 baseline-gap，完整清单见 PENDING.md；新信号出现时仍会正常展开）。")
        if fresh_mid:
            print(f"\n**中风险（{len(fresh_mid)} 项，待办型）→ 不 AskUserQuestion，挂周评估批量确认一次**（处理方式见 §周评估）：")
            for ln in fresh_mid:
                print(ln)
        if muted_mid:
            print(f"\n另有 {muted_mid} 条中风险已提醒 ≥{muted_after} 次未消化，不再逐条展开（完整清单见 PENDING.md，周评估时批量确认）。")
        if high_groups:
            print("\n**高风险（涉修业务代码/改 skill/复盘缺陷）→ AskUserQuestion 确认后才动**（multiSelect=true），建议选项：")
            for skill, n in high_groups.items():
                print(f"- {skill}（{n} 项信号）")
            print("选「Other」可输入自定义 skill 或跳过。")
        print("默认不全跑七 phase 全链（临时编排即可）。")
    except Exception as exc:  # noqa: BLE001 — hook 容错：stderr 可见，不阻断会话
        print(f"[session-start] 读取 PENDING 失败: {exc}", file=sys.stderr)
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
