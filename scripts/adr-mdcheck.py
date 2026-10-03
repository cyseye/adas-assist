#!/usr/bin/env python3
"""adr-mdcheck.py — ADR 目录不变量机械校验（20260927 沉淀治理轮落地件）

四个不变量（方案单源=仓内 decisions/ 知识治理 digest §四（未包含时按下列不变量执行））：
  I1 status 枚举白名单：Accepted | Accepted (partial) | Accepted (trial) | Proposed | Superseded | Deprecated
  I2 supersedes 闭环：非空时目标必须存在（adr/meta 或 adr/meta/archive）；目标在场则其 superseded_by 必须回填本件 slug
  I3 命名判据（T45② 落地）：slug 全局唯一、语义命名；YYYYMMDD 日期后缀仅允许
     一次性事件/战役/verdict/外参批次类（关键词判据见 EVENT_WORDS），常驻机制类禁日期后缀
  I4 frontmatter 必备键：status / date（title 可选）
fail-only：只报告不改文件；退出码 0=全过，1=存在 ERROR（WARN 不影响）。
用法：
  python3 scripts/adr-mdcheck.py                # 全量校验
  python3 scripts/adr-mdcheck.py --next-id T    # 台账发号：扫 PENDING+BACKLOG 的 T 号 max+1 并查重
  python3 scripts/adr-mdcheck.py --sync-count   # 把 KNOWLEDGE 计数注释同步为实测值（唯一写点，消手写漂移 R4）
零第三方依赖（Python 3 标准库）。
"""
import re
import sys
from pathlib import Path

ASSET = Path(__file__).resolve().parent.parent          # 本仓根（scripts/ 上溯）
ADR_META = ASSET / "decisions" / "adr" / "meta"
LEDGERS = [ASSET / "decisions" / "postmortems" / "PENDING.md",
           ASSET / "decisions" / "postmortems" / "BACKLOG.md"]

STATUS_ENUM = {"Accepted", "Accepted (partial)", "Accepted (trial)",
               "Proposed", "Superseded", "Deprecated"}
# （I3 已降为无条件样式 WARN，无需豁免词表）

FM_RE = re.compile(r"\A---\s*\n(.*?)\n---", re.S)
KEY_RE = {k: re.compile(rf"^{k}:\s*(.*)$", re.M) for k in ("status", "date", "supersedes", "superseded_by")}


def frontmatter(text):
    m = FM_RE.match(text)
    return m.group(1) if m else None


def get_key(fm, key):
    if fm is None:
        return None
    m = KEY_RE[key].search(fm)
    return m.group(1).strip().strip('"') if m else None


def main():
    errors, warns = [], []
    files = sorted(ADR_META.glob("*.md"))
    slugs = {p.stem: p for p in files}
    archive_slugs = {p.stem for p in (ADR_META / "archive").glob("*.md")} if (ADR_META / "archive").exists() else set()

    for p in files:
        slug, text = p.stem, p.read_text(encoding="utf-8")
        fm = frontmatter(text)
        # I4 frontmatter 必备键
        if fm is None:
            errors.append(f"I4 {slug}: 无 YAML frontmatter")
            fm = ""
        for k in ("status", "date"):
            if get_key(fm, k) is None:
                errors.append(f"I4 {slug}: 缺必备键 {k}")
        # I1 status 枚举
        st = get_key(fm, "status")
        if st is not None and st not in STATUS_ENUM:
            errors.append(f"I1 {slug}: status『{st}』不在白名单 {sorted(STATUS_ENUM)}")
        # I3 命名样式（WARN 级：E2 实证日期命名系推荐形态之一，不强制统一；判据=slug 唯一+date 键必有）
        if re.match(r"^(.*?)-(\d{8})$", slug):
            warns.append(f"I3 {slug}: 日期后缀与语义命名混用（样式提示，不强改——改名断链成本>收益）")
        # I2 supersedes 闭环
        sup = get_key(fm, "supersedes")
        if sup and sup not in ('""', "''"):
            targets = []
            for t in re.split(r"[,\n]", sup):
                t = t.strip().lstrip("- ").strip()
                if t and t not in ('""', "''") and ":" not in t:
                    targets.append(t)
            for target in targets:
                if target in slugs:
                    back = get_key(frontmatter(slugs[target].read_text(encoding="utf-8")), "superseded_by")
                    if slug not in (back or ""):
                        errors.append(f"I2 {slug}: supersedes→{target} 在场但对方 superseded_by 未回填（E1 双向原子原则）")
                elif target not in archive_slugs:
                    warns.append(f"I2 {slug}: supersedes→{target} 目标不存在（历史删除件，仅 git 可溯；存量悬空按清账单逐条销号）")
        # I2 反向：Superseded 状态必须有 superseded_by
        if st == "Superseded" and not get_key(fm, "superseded_by"):
            errors.append(f"I2 {slug}: status=Superseded 但 superseded_by 为空")

    # I5 外参召回面对账（R8 机械化：external/ 件在 KNOWLEDGE 无索引行即报）
    kn = ASSET / "decisions" / "KNOWLEDGE.md"
    ext_dir = ASSET / "decisions" / "external"
    if kn.exists() and ext_dir.exists():
        kn_text = kn.read_text(encoding="utf-8")
        # I6 索引重复行检测（20260930 sys-01 防复发门：历史曾实证三组 ADR 双登记稀释召回单源）
        seen, kn_dups = {}, []
        for ln in kn_text.splitlines():
            m = re.search(r"- \[([^\]]+)\]\((?:adr/meta/)?([^)]+\.md)\)", ln)
            if m:
                key = (m.group(1).strip(), m.group(2))
                seen[key] = seen.get(key, 0) + 1
        for (title, tgt), n in sorted(seen.items()):
            if n > 1:
                kn_dups.append(f"{title}→{tgt}×{n}")
        if kn_dups:
            errors.append(f"I6 KNOWLEDGE 索引行重复登记（稀释召回单源，去重保留一条）：{'; '.join(kn_dups)}")
        for p in sorted(ext_dir.glob("*.md")):
            if f"]({p.parent.name}/{p.name})" not in kn_text and f"]({p.name})" not in kn_text:
                warns.append(f"I5 external/{p.name}: KNOWLEDGE 零索引行=零召回（外参件结论行必登义务）")

    print(f"adr-mdcheck: {len(files)} 件（adr/meta），ERROR {len(errors)} / WARN {len(warns)}")
    for e in errors:
        print("ERROR", e)
    for w in warns:
        print("WARN ", w)
    return 1 if errors else 0


def next_id(prefix):
    pat = re.compile(rf"\b{re.escape(prefix)}-?(\d+)['′]?\b")
    seen, per_file_counts = set(), {}
    for f in LEDGERS:
        if not f.exists():
            continue
        text = f.read_text(encoding="utf-8")
        hits = pat.findall(text)
        seen.update(hits)
        counts = {}
        for n in hits:
            counts[n] = counts.get(n, 0) + 1
        per_file_counts[f.name] = {n: c for n, c in counts.items() if c > 2}
    if not seen:
        print(f"{prefix}1")
        return
    mx = max(int(n) for n in seen)
    print(f"next = {prefix}{mx + 1}（现存 max={prefix}{mx}，共 {len(seen)} 号）")
    # 同一文件内同号出现 >2 次=疑似多头登记/撞号；跨台账同号属双记设计不报
    for fname, dups in per_file_counts.items():
        if dups:
            print(f"WARN {fname} 同号多次出现（疑似撞号，人工消歧）：{sorted(dups)}")


def sync_count():
    """计数注释机械同步（R4 根治：衍生数据不设人工单源；只改 `<!-- 计数：meta N / data N` 前缀数字，session-review 正则契约不变）"""
    kn = ASSET / "decisions" / "KNOWLEDGE.md"
    meta_n = len(list(ADR_META.glob("*.md")))
    data_n = len(list((ASSET / "decisions" / "adr" / "data").glob("*.md")))
    # T119 判据（2026-09-28）：未 tracked 的 ADR 计入即 WARN——防 committed 态复现
    # 计数 breach（计数已含未入库件，后续 git 操作/归档时漂移无锚可考）
    import subprocess
    for label, files in (("meta", sorted(ADR_META.glob("*.md"))),
                         ("data", sorted((ASSET / "decisions" / "adr" / "data").glob("*.md")))):
        if not files:
            continue
        r = subprocess.run(
            ["git", "-C", str(ASSET), "ls-files", "--others", "--exclude-standard",
             *[str(f.relative_to(ASSET)) for f in files]],
            capture_output=True, text=True, timeout=15)
        untracked = [l for l in r.stdout.splitlines() if l.strip()]
        if untracked:
            print(f"WARN 计数含未 tracked ADR（{label}）：{untracked}——入库前计数为暂态，commit 后复跑核对")
    text = kn.read_text(encoding="utf-8")
    new, n = re.subn(r"<!-- 计数：meta \d+ / data \d+",
                     f"<!-- 计数：meta {meta_n} / data {data_n}", text, count=1)
    if n == 0:
        print("ERR: 计数注释句式未匹配（session-review 正则契约前缀），拒绝盲写")
        return 1
    if new == text:
        print(f"count ok（meta {meta_n} / data {data_n} 已同步）")
        return 0
    kn.write_text(new, encoding="utf-8")
    print(f"synced → meta {meta_n} / data {data_n}")
    return 0


def backlog_len_check(limit=2000):
    """BACKLOG 行长安检（T86 落地，2026-09-28）：V2-2 判据「新增行≤2000 字符」
    原零执法——超限行.print 出供压缩；全文件现行都扫（存量超限=逐轮消化对象）。"""
    f = LEDGERS[-1] if LEDGERS[-1].name == "BACKLOG.md" else \
        next((x for x in LEDGERS if x.name == "BACKLOG.md"), None)
    if not f or not f.exists():
        print("BACKLOG.md 不存在，跳过")
        return 0
    bad = [(i, len(l)) for i, l in enumerate(f.read_text(encoding="utf-8").splitlines(), 1)
           if len(l) > limit]
    for i, n in bad:
        print(f"WARN 行{i} 长 {n} > {limit}（逐轮消化对象）")
    print(f"BACKLOG 行长安检：超限 {len(bad)} 行")
    return 0


def lifecycle_retro_grep(skill_name):
    """追认禁令三条件机械 grep（T99③ 落地，2026-09-28；条款源
    decision-lifecycle/SKILL.md:35，源自 org-formations U11）：对已静默删改的 skill
    做「事后追认/合并」前，三条件齐（git 有变更 + 引用计数归零 + 无 revert commit）
    即禁追认——补 revert 不洗白。本命令只出机械读数，裁决权仍在 lifecycle 门。
    注：U11 原始件在 archive（org-formations），「双 grep 路径全集」此处实现为
    资产面+台账面两族（skills/commands/agents/standards/rules/两地图 × decisions/）。"""
    import subprocess
    home = Path.home() / ".claude"
    # 条件1：git 历史有变更（skill 目录曾存在提交）
    log = subprocess.run(["git", "-C", str(home), "log", "--oneline", "--",
                          f"skills/{skill_name}"], capture_output=True, text=True)
    cond1 = bool(log.stdout.strip())
    # 条件2：引用计数归零（资产面+台账面两族，排除本 grep 自身与 git 内部）
    ref = subprocess.run(["grep", "-rl", skill_name,
                          str(home / "skills"), str(home / "commands"), str(home / "agents"),
                          str(home / "standards"), str(home / "rules"),
                          str(home / "README.md"), str(home / "AGENTOS-MAP.md"),
                          str(home / "decisions")],
                         capture_output=True, text=True)
    refs = [l for l in ref.stdout.splitlines()
            if l.strip() and "__pycache__" not in l and not l.endswith((".pyc", ".jsonl"))]
    cond2 = not refs
    # 条件3：无 revert commit（提交标题含 revert+skill 名）
    rev = subprocess.run(["git", "-C", str(home), "log", "--oneline", "--all", "--grep=revert",
                          "-i", "--", f"skills/{skill_name}"], capture_output=True, text=True)
    cond3 = not bool(rev.stdout.strip())
    verdict = cond1 and cond2 and cond3
    print(f"[{skill_name}] 追认禁令三条件：")
    print(f"  ① git 有变更史: {cond1}")
    print(f"  ② 引用计数归零: {cond2}（现存活引用 {len(refs)} 处：{refs[:5]}）")
    print(f"  ③ 无 revert commit: {cond3}")
    print(f"  ⇒ {'⛔ 三条件齐=禁追认（补 revert 不洗白）' if verdict else '✅ 不触发禁令（仍须走 lifecycle 门全流程）'}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "--next-id":
        next_id(sys.argv[2])
        sys.exit(0)
    if len(sys.argv) >= 2 and sys.argv[1] == "--sync-count":
        sys.exit(sync_count())
    if len(sys.argv) >= 2 and sys.argv[1] == "--backlog-len":
        sys.exit(backlog_len_check())
    if len(sys.argv) >= 3 and sys.argv[1] == "--lifecycle-grep":
        sys.exit(lifecycle_retro_grep(sys.argv[2]))
    sys.exit(main())
