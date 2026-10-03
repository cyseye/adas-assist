#!/usr/bin/env python3
"""提交守门 hook（pre-commit + commit-msg 双模式，由 argv[1] 区分）。

**状态注记**：本件为「手动 git 提交守门」
唯一安装源（安装路径=.git/hooks pre-commit/commit-msg，见安装说明），当前全仓零精确
引用、设计安装路径零实例=待装资产非死资产；G2（cc-commit-gate.py）只拦 AI 发起提交，
手动提交守门唯靠本件，故保留。安装后本注记由消费方登记行取代。

进化来源：2026-09-01 四类实证缺陷——滚雪球 message（单条 3.3 万行全历史堆叠）/
type 与内容错配（type=docs 但 13/13 全代码）/ 单笔多语义打包 / 开发环境内容入库
（demo 探测插件+mock 数据进远端）。落地裁决：hook 硬门 + 纪律双落地（用户 2026-09-01）。

模式：
  pre-commit  校验 staged 内容（本地专用文件黑名单）
  commit-msg  校验提交消息（merge 豁免/格式/体量/多语义/type 对照），$1 = message 文件路径

逃生口：git commit --no-verify（标准行为，守门是提示不是牢笼）。
安装：.git/hooks/{pre-commit,commit-msg} 为 sh wrapper 调本脚本，git 自动传参。
"""
import re
import subprocess
import sys
from pathlib import Path

# ── pre-commit：staged 内容黑名单 ──────────────────────────────────
# 每条 = (路径子串, 说明)：staged 路径含子串即命中，防开发环境/瞬态产物上远端。
STAGED_BLOCKLIST = [
    ("project/frontend/mock/", "前端 demo 兜底数据（本地演示专用）"),
    ("dev-demo-mode.md", "demo 模式说明文档（本地演示专用）"),
    (".figma-workspace/", "figma 还原工作区瞬态产物"),
    (".build/", "构建/检查中间产物"),
    (".claude/.state/", "adas-assist 运行时状态"),
    (".zcode/", "本地瞬态目录"),
    ("project/frontend/screenshots/", "截图验证瞬态产物"),
    (".claude/settings.json", "本地个人配置（已跟踪，改动永不提交）"),
    ("tsconfig.tsbuildinfo", "TS 增量编译产物"),
]

# ── commit-msg：消息门 ────────────────────────────────────────────
TYPE_RE = re.compile(r"^(feat|fix|refactor|docs|chore|perf|test|style|revert)(\(.+\))?: \S")
# body 中额外的独立 type 段行（多语义打包特征）
TYPE_LINE_RE = re.compile(r"^\s*(feat|fix|refactor|docs|chore|perf|test|style|revert)\(")
MAX_MSG_LINES = 40
# type → 期望内容域（用于错配对照；mixed 不拦）
TYPE_DOMAIN = {
    "docs": {"doc"},
    "feat": {"code", "mixed", "doc"},
    "fix": {"code", "mixed", "doc"},
    "refactor": {"code", "mixed"},
    "chore": {"code", "config", "mixed", "doc"},
    "perf": {"code", "mixed"},
    "test": {"code", "mixed"},
    "style": {"code", "mixed"},
    "revert": {"code", "mixed", "doc", "config"},
}
CODE_EXT = {".java", ".ts", ".tsx", ".js", ".jsx", ".xml", ".sql", ".py", ".vue",
            ".css", ".scss", ".less", ".mjs", ".cjs", ".sh"}
DOC_EXT = {".md", ".docx", ".png", ".emf", ".svg", ".drawio"}

# KNOWLEDGE/lessons 投毒面语义提示：仅提示不拦截
# （守门是提示不是牢笼，与模块 docstring 逃生口哲学一致）。纯机械规则，零模型调用。
KNOWLEDGE_PATH_RE = re.compile(r"decisions/KNOWLEDGE\.md|lessons-?\d{4}-?\d{2}\.md|evolution-pool/")
_URL_ALLOW = ("arxiv.org", "github.com", "anthropic.com", "claude.com", "claude.ai",
              "docs.anthropic.com", "pmc.ncbi.nlm.nih.gov", "doi.org", "nature.com")
_INJ_LINE_RE = re.compile(
    r"```|^#+\s*(必读|指令|重要.{0,6}(请|须|必须))"
    r"|ignore\s+(all\s+)?(previous|prior|above)|disregard"
    r"|忽略(以上|之前|上述|全部)?(的)?(指令|内容)"
    r"|(请|务必|立即)?执行(以下|如下|下列)(指令|操作)"
    r"|你现在是|从现在起你是|system\s*prompt|系统提示词")


def _knowledge_semantic_hints(staged: list) -> None:
    targets = [p for p in staged if KNOWLEDGE_PATH_RE.search(p)]
    if not targets:
        return
    warnings = []
    for p in targets:
        diff = _git("diff", "--cached", "-U0", "--", p)
        for ln in diff.splitlines():
            if not ln.startswith("+") or ln.startswith("+++"):
                continue
            body = ln[1:]
            if _INJ_LINE_RE.search(body):
                warnings.append(f"  {p}: 新增行含指令注入特征模式: {body.strip()[:60]!r}")
            for m in re.findall(r"https?://([^/\s]+)", body):
                if not any(m == d or m.endswith("." + d) for d in _URL_ALLOW):
                    warnings.append(f"  {p}: 新增行含白名单外域 {m}（外源论断须附 intake id）")
    if warnings:
        print("[commit-gate] 语义提示（不拦截，人工复核）——KNOWLEDGE/lessons 面新增：", file=sys.stderr)
        print("\n".join(warnings[:10]), file=sys.stderr)


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True).stdout


def staged_files() -> list[str]:
    out = _git("diff", "--cached", "--name-only", "--diff-filter=ACMR")
    return [ln.strip() for ln in out.splitlines() if ln.strip()]


def content_domain(paths: list[str]) -> str:
    """staged 文件集主导内容域：code / doc / config / mixed / none（未知扩展不参与判定）。"""
    kinds = set()
    for p in paths:
        ext = Path(p).suffix.lower()
        if ext in CODE_EXT:
            kinds.add("code")
        elif ext in DOC_EXT:
            kinds.add("doc")
        elif ext in {".yml", ".yaml", ".json", ".toml"}:
            kinds.add("config")
    if not kinds:
        return "none"
    return next(iter(kinds)) if len(kinds) == 1 else "mixed"


def check_pre_commit() -> int:
    staged = staged_files()
    if not staged:
        return 0
    blocked = []
    for p in staged:
        for pattern, why in STAGED_BLOCKLIST:
            if pattern in p:
                blocked.append(f"  {p}  ← {why}")
                break
    if blocked:
        print("[commit-gate] 拦截：staged 含本地专用/瞬态文件，不应上远端：", file=sys.stderr)
        print("\n".join(blocked), file=sys.stderr)
        print("（确认确需提交：git commit --no-verify；一般应 git restore --staged <file>）", file=sys.stderr)
        return 1
    _knowledge_semantic_hints(staged)  # T32②③：KNOWLEDGE/lessons 面注入特征提示（不拦截）
    return 0


def check_commit_msg(msg_file: str) -> int:
    msg = Path(msg_file).read_text(encoding="utf-8", errors="replace")
    lines = msg.splitlines()
    errors = []

    subject = next((ln for ln in lines if ln.strip()), "")

    # 0) merge 豁免：git merge/pull 的默认消息非人工语义消息，
    #    拦截会把 merge 卡在半完成态（MERGE_HEAD 残留）
    if subject.startswith("Merge "):
        return 0

    # 1) 体量门：滚雪球特征（全历史堆叠动辄千行）
    if len(lines) > MAX_MSG_LINES:
        errors.append(f"message 共 {len(lines)} 行 > 上限 {MAX_MSG_LINES}——疑似滚雪球堆叠，"
                      f"每笔提交只写本笔语义")

    # 2) subject 格式门（拦 ``` 前缀/空 type/纯叙述）
    if subject.startswith("```") or not TYPE_RE.match(subject):
        errors.append(f"subject 不符合 conventional 格式（当前: {subject[:60]!r}）。"
                      f"要求: <type>(<scope>): <描述>，反引号/代码围栏不得进 message")

    # 3) 多语义门：body 中除 subject 外再出现独立 type(scope) 段 = 打包多笔语义
    extra = [ln.strip()[:50] for ln in lines[1:] if TYPE_LINE_RE.match(ln)]
    if extra:
        errors.append(f"body 内出现 {len(extra)} 个额外 type 段（如 {extra[0]!r}）——"
                      f"单笔提交只承载一类语义，请拆笔提交")

    # 4) type vs 内容域对照（空 staged / none 域跳过，防误拦）
    m = TYPE_RE.match(subject)
    if m:
        typ = m.group(1)
        staged = staged_files()
        if staged:
            domain = content_domain(staged)
            # none = 全为未知扩展名（无法判定域），不对照防误拦（如 .html/Dockerfile）
            if domain != "none":
                allowed = TYPE_DOMAIN.get(typ)
                if allowed is not None and domain not in allowed:
                    errors.append(f"type={typ} 但 staged 内容域为 {domain}——type 与内容错配"
                                  f"（实证: b8c7d172d type=docs 装了 13 个代码文件）")

    if errors:
        print("[commit-gate] 拦截本次提交：", file=sys.stderr)
        for e in errors:
            print(f"  ✗ {e}", file=sys.stderr)
        print("（修改 message 后重试；确需跳过: git commit --no-verify）", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "pre-commit":
        sys.exit(check_pre_commit())
    if mode == "commit-msg":
        sys.exit(check_commit_msg(sys.argv[2] if len(sys.argv) > 2 else ".git/COMMIT_EDITMSG"))
    print(f"用法: {sys.argv[0]} pre-commit | commit-msg <msgfile>", file=sys.stderr)
    sys.exit(2)
