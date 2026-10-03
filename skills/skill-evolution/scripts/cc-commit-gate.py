#!/usr/bin/env python3
"""Claude Code PreToolUse 门：只拦 AI（Bash 工具）发起的 git commit，手动提交完全不经过此处。

架构裁决（用户 2026-09-02）：原 .git/hooks 全局门撤除（手动提交零阻拦），
校验逻辑前移到 Claude Code hook 层，复用 commit-gate.py 双模式不重复实现：
  pre-commit 模式 → staged 本地专用文件黑名单（提交前必查）
  commit-msg 模式 → 消息格式/体量/多语义/type 对照（从 -m/--message/-F/--file 提取）

放行规则（逃生口语义与原门一致）：
  非 git commit 命令 / 含 --no-verify / message 提取失败（引号不平衡等）→ 放行
阻断输出走 stderr + exit 2，拦截原因回传给 AI 自行修正 message。
"""
import json
import re
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

GATE = Path(__file__).parent / "commit-gate.py"

PATTERNS = Path(__file__).parents[2] / "_shared" / "security-patterns.json"


def _ss():
    """T20（2026-09-21）扫描管道公共件装载——secret-scan.py 单源（文件名含连字符
    不可直接 import；spec 加载，参照 weekly-eval.py _kr_mod 先例）。
    变体池/编码段提取+滑窗拼接/词粘连后验实现全部移交公共件，本门只留
    hits/seen 账本与模式匹配编排。"""
    import importlib.util
    p = Path(__file__).parents[2] / "_shared" / "scripts" / "secret-scan.py"
    spec = importlib.util.spec_from_file_location("secret_scan", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _normalized_texts(s: str) -> dict[str, str]:
    """薄壳（T20 2026-09-21）：实现单源 _shared/scripts/secret-scan.py
    normalized_texts（G1/G2 并集池）。crossline=url 前缀语义为既有消费方保留：
    crossline 并入 clean（collapse 天然去换行），url 深度1沿用 `url-` 名。"""
    return _ss().normalized_texts(s)


def scan_text_secrets(text: str, max_hits: int = 10) -> list[str]:
    """G2 文本面（消息/任意文本）扫 L2 模式（T16 P1：-F 消息藏匿堵口）。
    P3 演练修复（2026-09-21）：与 staged 面同款变换道——跨行重组/URL 解码/NFKC
    归一化/base64·hex 解码二扫（原仅 staged 面有，消息面编码与断行藏匿实锤绕过）。
    T19⑥ 2026-09-21：G1 V2.2 管道移植——变体池升级为完整规范化管道
    （封分段/零宽/软连字/双 URL 编码/阿拉伯数字/小写 bearer 六类同款逃逸）。"""
    try:
        pats = json.loads(PATTERNS.read_text(encoding="utf-8")).get("patterns", [])
    except (OSError, ValueError) as e:
        print(f"[cc-commit-gate] G2 文本扫描故障 fail-open：{e}", file=sys.stderr)
        return []
    hits, seen = [], set()
    ss = _ss()

    def _match(t: str, prefix: str = "", flags: int = 0) -> None:
        for p in pats:
            for m in re.finditer(p["re"], t, flags):
                # 词粘连后验（T19⑥ V2.5，实现单源公共件 is_word_fused）：去空白
                # 变体的 cred 类命中若前邻字符为字母，系普通词尾粘连假 sk-/Bearer
                # （跨行粘连误报实证）——凭证开头不可能嵌在词中，丢弃
                if (p["id"].startswith("cred-")
                        and prefix in ("clean-", "crossline-", "digits-", "nfkc-", "bounds-")
                        and ss.is_word_fused(t, m.start())):
                    continue
                key = (f"{prefix}{p['id']}", m.group(0)[:40])
                if key not in seen:
                    seen.add(key)
                    hits.append(f"{key[0]}: {m.group(0)[:40]}…（{p['desc']}）")
                if len(hits) >= max_hits:
                    return

    # T19⑥ 2026-09-21：G1 V2.2 管道移植——变体池替换原三变换（原 crossline-/
    # url-/nfkc- 前缀语义保留为子集；casefold 变体配 IGNORECASE 封小写 bearer）
    for prefix, variant in _normalized_texts(text).items():
        _match(variant, prefix="" if prefix == "raw" else f"{prefix}-",
               flags=re.IGNORECASE if prefix == "casefold" else 0)
        if len(hits) >= max_hits:
            return hits
    # 编码段提取在规范化文本上跑——封分段藏匿。
    # T19⑥ 2026-09-21：G1 V2.2 管道移植——剥不可见逐行（空白保留，段边界不与
    # 普通词粘连致解码失败）+collapse 整体（封跨行分段）双道各扫一遍
    nt = _normalized_texts(text)
    cleaned_lines = ss.strip_invisible(text).splitlines()
    for ln in cleaned_lines + [nt["clean"]]:
        _scan_encoded_line(ln, pats, hits, seen, max_hits)
        if len(hits) >= max_hits:
            return hits
    return hits


def _scan_encoded_line(line: str, pats: list, hits: list, seen: set, max_hits: int) -> None:
    """薄壳（T20 2026-09-21）：段提取（静态+空白分段滑窗子序列拼接）与解码
    全部单源 _shared/scripts/secret-scan.py decoded_segments；本函数只留
    encoded-<id> 账本编排。历史阈值（b64 ≥12/hex ≥24，P3 收严）与 sha256 等
    真二进制解码失败静默跳过语义由公共件保持。"""
    for _seg, text in _ss().decoded_segments(line):
        for p in pats:
            for m in re.finditer(p["re"], text):
                key = (f"encoded-{p['id']}", m.group(0)[:40])
                if key not in seen:
                    seen.add(key)
                    hits.append(f"{key[0]}: {m.group(0)[:40]}…（{p['desc']}，base64/hex 编码藏匿）")
                if len(hits) >= max_hits:
                    return


def _binary_staged_warns(max_hits: int = 10) -> list[str]:
    """T19 二进制面：numstat `-` `-` 标记的文件无法静态扫描。设计裁决=阻断+提示：
    二进制藏匿凭证是最高风险外流面且零静态可见性，fail-closed 优先；误拦代价极低
    （改文本存储或 --no-verify 一次显式豁免），故并入 hits 阻断而非仅提示。"""
    try:
        import subprocess as sp
        out = sp.run(["git", "diff", "--cached", "--numstat"],
                     capture_output=True, text=True, errors="replace").stdout
    except OSError as e:
        print(f"[cc-commit-gate] G2 二进制扫描故障 fail-open：{e}", file=sys.stderr)
        return []
    warns = []
    for ln in out.splitlines():
        parts = ln.split("\t")
        if len(parts) == 3 and parts[0] == "-" and parts[1] == "-":
            print(f"[cc-commit-gate] 二进制文件 {parts[2]} 未扫描（无法验证是否含敏感内容，按阻断处理）",
                  file=sys.stderr)
            warns.append(f"[阻断] binary-unscanned: {parts[2]}（二进制文件未扫描，fail-closed——改文本存储或 --no-verify 显式豁免）")
            if len(warns) >= max_hits:
                break
    return warns


def scan_staged_secrets(max_hits: int = 10) -> list[str]:
    """G2：staged diff 扫 L2 敏感模式（单源 security-patterns.json）。异常 fail-open+stderr 留痕
    （门自身故障不应卡死全部提交，但须可观测——与上文 payload 解析失败同语义）。
    只扫新增行（+ 行）——删除敏感内容属清洗动作，扫删除行会使 T17 清洗提交被自身门
    死锁（2026-09-20 复盘轮 real-run 实证：清洗 diff 的 - 行命中致提交被拦）。"""
    try:
        import subprocess as sp
        # errors=replace：二进制 staged 时 diff 输出含非 UTF-8 字节，replace 防
        # 解码异常整轮 fail-open（T19 实测：否则连二进制 warn 都出不来）
        diff = sp.run(["git", "diff", "--cached", "-U0"], capture_output=True,
                      text=True, errors="replace").stdout
        if not diff.strip():
            return _binary_staged_warns(max_hits)
        added = "\n".join(ln[1:] for ln in diff.splitlines()
                          if ln.startswith("+") and not ln.startswith("+++"))
        if not added.strip():
            return _binary_staged_warns(max_hits)
        pats = json.loads(PATTERNS.read_text(encoding="utf-8")).get("patterns", [])

        def _match(text: str, prefix: str = "", flags: int = 0) -> None:
            for p in pats:
                for m in re.finditer(p["re"], text, flags):
                    key = (f"{prefix}{p['id']}", m.group(0)[:40])
                    if key not in seen:
                        seen.add(key)
                        hits.append(f"{key[0]}: {m.group(0)[:40]}…（{p['desc']}）")
                    if len(hits) >= max_hits:
                        return

        hits, seen = [], set()
        _match(added)
        if len(hits) >= max_hits:
            return hits
        # P3 演练修复（2026-09-21）三变换面：跨行重组/URL 解码/NFKC——
        # T19⑥ 2026-09-21：G1 V2.2 管道移植——三变换升级为完整规范化变体池
        # （原 crossline-/url-/nfkc- 前缀语义保留为池的子集；新增 clean-/digits-/
        # casefold- 前缀；封分段/零宽/软连字/双 URL 编码/阿拉伯数字/小写 bearer）
        for prefix, variant in _normalized_texts(added).items():
            _match(variant, prefix="" if prefix == "raw" else f"{prefix}-",
                   flags=re.IGNORECASE if prefix == "casefold" else 0)
            if len(hits) >= max_hits:
                return hits
        # T19 解码二扫：base64/hex 段解码后复扫同一模式集（编码藏匿口）。
        # T19⑥ 2026-09-21：G1 V2.2 管道移植——剥不可见逐行（空白保留，段边界
        # 不与普通词粘连致解码失败）+collapse 整体（封跨行分段）双道各扫一遍
        nt = _normalized_texts(added)
        cleaned_lines = _ss().strip_invisible(added).splitlines()
        for ln in cleaned_lines + [nt["clean"]]:
            _scan_encoded_line(ln, pats, hits, seen, max_hits)
            if len(hits) >= max_hits:
                break
        return hits + _binary_staged_warns(max_hits)
    except (OSError, ValueError, KeyError) as e:
        print(f"[cc-commit-gate] G2 扫描故障 fail-open：{e}", file=sys.stderr)
        return []


def is_git_commit(tokens: list[str]) -> bool:
    """红队演练 P1 修复（2026-09-20 T16）：放宽 token 匹配封逃逸。
    原只认字面相邻 `git commit`——`/usr/bin/git commit`、`git -C . commit`、
    alias `git ci`、`sh -c 'git commit'` 全逃逸（演练 7/11 绕过主因）。
    现判：tokens 含 git 家族（basename=git）且同句内出现 commit/ci 子命令。
    P3 演练 C 修复（2026-09-21）：`git -c alias.x=commit x` 形态——key=value token
    的 value 侧再判（alias.<名>=commit 视同 commit 子命令）。"""
    has_git = any(t == "git" or t.endswith("/git") for t in tokens)
    has_commit = any(t in ("commit", "ci")
                     or re.fullmatch(r"alias\.[\w-]+=commit", t) for t in tokens)
    return has_git and has_commit


def _unwrap_shell(tokens: list[str]) -> list[str]:
    """P3 演练 A 修复（2026-09-21）：sh -c 'git commit …' 包装还原。
    外层 shlex 把引号内整串切成一个 token，is_git_commit 见不到内层命令——
    递归（≤3 层）解析 -c 载荷后再判。解析失败返回原样（上层 fail 分支接手）。"""
    for _ in range(3):
        idx = next((i for i, t in enumerate(tokens)
                    if t in ("sh", "bash", "zsh")
                    and i + 2 < len(tokens) and tokens[i + 1] == "-c"), None)
        if idx is None:
            return tokens
        payload = " ".join(tokens[idx + 2:])
        try:
            tokens = shlex.split(payload)
        except ValueError:
            return tokens
    return tokens


def extract_messages(tokens: list[str]) -> list[str]:
    """收集 -m/--message 与 -F/--file 的值（多个 -m 时 git 按序拼接，此处仅校验各段）。"""
    msgs = []
    for i, t in enumerate(tokens):
        nxt = tokens[i + 1] if i + 1 < len(tokens) else None
        if t in ("-m", "--message") and nxt:
            msgs.append(nxt)
        elif t.startswith("--message="):
            msgs.append(t.split("=", 1)[1])
        elif t in ("-F", "--file") and nxt:
            p = Path(nxt)
            if p.exists():
                msgs.append(p.read_text(encoding="utf-8", errors="replace"))
        elif t.startswith("--file="):
            p = Path(t.split("=", 1)[1])
            if p.exists():
                msgs.append(p.read_text(encoding="utf-8", errors="replace"))
    return msgs


def run_gate(mode: str, *args: str) -> int:
    return subprocess.run(["python3", str(GATE), mode, *args]).returncode


def main() -> int:
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError as _e:  # 留痕批：守门 hook 读空即放行无痕（B2-2）
        print(f"[cc-commit-gate] payload 解析失败，守门跳过：{_e}", file=sys.stderr)
        return 0
    cmd = data.get("tool_input", {}).get("command", "")

    try:
        tokens = shlex.split(cmd)
    except ValueError as _e:  # 留痕批：不猜语义放行但须可观测（B2-3）
        # P3 演练硬化（2026-09-21）：消息面确实无法解析，但 staged 内容面
        # 不依赖消息——引号失衡的真 commit 不应零扫描放行（fail-open 收窄为
        # 「消息面放行+内容面照扫」）。
        print(f"[cc-commit-gate] 命令引号解析失败，消息面放行、staged 内容面照扫：{_e}", file=sys.stderr)
        g2 = scan_staged_secrets()
        if g2:
            print("[cc-commit-gate] G2 安全门阻断：staged 含 L2 敏感内容（协议见 standards/security-protocol.md）：",
                  file=sys.stderr)
            for hit in g2:
                print(f"  - {hit}", file=sys.stderr)
            return 2
        return 0

    tokens = _unwrap_shell(tokens)  # P3 演练 A 修复：sh -c 包装还原后再判
    if not is_git_commit(tokens):
        return 0
    if "--no-verify" in tokens:
        # 红队演练 P2 修复（T16）：逃生不再零留痕——stderr+审计行落盘（谁/何时），
        # 满足证据链硬门（设计内逃生保留，但可审计）。P3 复盘：截断 200→500 防证据链缺口。
        try:
            from datetime import datetime
            log = Path(__file__).parents[2] / "skill-evolution" / "registry" / "gate-audit.log"
            with log.open("a") as f:
                f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S}\tno-verify-escape\t{cmd[:500]}\n")
        except OSError:
            pass
        print("[cc-commit-gate] --no-verify 逃生已留痕（gate-audit.log），敏感内容外流责任自负", file=sys.stderr)
        return 0

    rc = run_gate("pre-commit")
    if rc != 0:
        print("[cc-commit-gate] staged 校验未过，命令已阻断，见上方 commit-gate 输出", file=sys.stderr)
        return 2

    # G2 push 内容门（2026-09-20 安全蓝图 P1）：staged diff 敏感串扫描，模式集单源
    # skills/_shared/security-patterns.json（协议 standards/security-protocol.md）。
    # 零模型纯 regex；L2 命中即阻断；逃生=--no-verify 或模式集白名单演进（带日期理由）。
    g2 = scan_staged_secrets()
    if g2:
        print("[cc-commit-gate] G2 安全门阻断：staged 含 L2 敏感内容（协议见 standards/security-protocol.md）：",
              file=sys.stderr)
        for hit in g2:
            print(f"  - {hit}", file=sys.stderr)
        print("清洗后重试（拓扑降占位符/凭证降'见本地 .env'）或 --no-verify 逃生", file=sys.stderr)
        return 2

    # 红队演练 P1 修复（T16）：-F 文件提交消息面纳入 G2（消息藏敏感串曾绕过）。
    # P3 演练 B 修复（2026-09-21）：多段 -m 按 git 拼接语义合并后一次扫描——
    # 原逐段扫描使 `-m "192." -m "168.5.2"` 分段藏匿绕过（红队实锤）。
    msgs = extract_messages(tokens)
    msg_hits = scan_text_secrets("\n".join(msgs)) if msgs else []
    if msg_hits:
        print("[cc-commit-gate] G2 安全门阻断：commit 消息含 L2 敏感内容：", file=sys.stderr)
        for hit in msg_hits:
            print(f"  - {hit}", file=sys.stderr)
        return 2

    # EVOLUTION 同步提醒（进化轮正向#4，2026-09-16）：staged 含 skill 文档改动而无任何
    # EVOLUTION/decisions 变更 → warn 不阻断（signal-changed-unsynced 18/22 条实证
    # 「skill 改动忘沉淀」高频复发；复用本 hook 宿主零新增机制）。
    try:
        staged = subprocess.run(["git", "diff", "--cached", "--name-only"],
                                capture_output=True, text=True).stdout.split()
        skill_hits = [f for f in staged if f.startswith(("skills/", ".claude/skills/"))]
        sync_hits = [f for f in staged if "EVOLUTION" in f or "/decisions/" in f]
        if skill_hits and not sync_hits:
            print(f"[cc-commit-gate] 提醒：{len(skill_hits)} 个 skill 文件入库但无 EVOLUTION/decisions "
                  "同步——进化留痕义务见 evolution-discipline（不阻断）", file=sys.stderr)
    except OSError:
        pass

    if msgs:
        with tempfile.NamedTemporaryFile("w", suffix=".msg", delete=False) as f:
            f.write("\n\n".join(msgs))
            tmp = f.name
        rc = run_gate("commit-msg", tmp)
        Path(tmp).unlink(missing_ok=True)
        if rc != 0:
            print("[cc-commit-gate] message 校验未过，命令已阻断；"
                  "按上方提示修正 -m 内容后重试", file=sys.stderr)
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
