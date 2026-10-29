"""Explicit-file memory index parser and tokenizer; no host lookup or writes."""
from __future__ import annotations
import re
from pathlib import Path

STOP_BIGRAMS = {
    "一下", "这个", "那个", "什么", "怎么", "可以", "需要", "进行", "使用", "一个",
    "没有", "我们", "然后", "如果", "但是", "还有", "现在", "可能", "应该", "或者",
    "帮我", "看看", "处理", "相关", "问题",
    # ↑「问题」：纯泛词无区分度——教训 anchor 多含「真问题/源问题」字样，
    # 「帮我处理一下这个问题」曾误召回 Design restraint（魔鬼测试实证）
    # ↓开发通文 bigram（2026-09-19 误召回放实证）：KNOWLEDGE anchor 长条目普遍含这些词，
    # 任意两个即过 4 分门槛（命中率 anchor 覆盖仅 4-6%），如「实现时复用现有分页机制」
    # 误召「组织阵型螺旋进化定版」（实现+机制）、「分层与文档同步」误召「知识文档治理总纲」；
    # 六条已验证正例（表格列宽/探针/git 提交/文档压缩/token/figma）命中均不依赖这批词
    "机制", "实现", "现有", "分层", "文档", "同步",
}

TYPE_WORDS = {"adr", "postmortem", "capa", "verify", "consensus", "lifecycle", "json", "md", "build", "tag", "skill"}

def _tokens(text: str) -> tuple[set[str], set[str]]:
    """英文 token（≥3 字符）+ 中文 bigram 双通道分词，各滤泛词。"""
    en = {t.lower() for t in re.findall(r"[A-Za-z0-9_-]{3,}", text)}
    en -= TYPE_WORDS
    zh: set[str] = set()
    for span in re.findall(r"[一-鿿]{2,}", text):
        zh |= {span[i:i + 2] for i in range(len(span) - 1)}
    zh -= STOP_BIGRAMS
    return en, zh

def _frontmatter_trigger(md_path: Path) -> str:
    """读教训文件 frontmatter 的 trigger 字段（何时应想起，一行字符串）；无则空串。

    trigger 是 hook 之外的显式召回锚点：索引行 hook 描述的是"教训内容"，
    trigger 描述的是"触发场景"（如「写 playwright 探针断言时」），任务 prompt
    与场景词重合而与教训正文不重合时靠它命中。文件读取失败按无 trigger 处理，
    不影响索引主流程。
    """
    return _frontmatter_fields(md_path)[0]

def _frontmatter_fields(md_path: Path) -> tuple[str, str]:
    """一次文件读取同时取 trigger 与 modified（复用读盘，不为一字段翻倍 IO）。
    modified 是 recency 因子与淘汰候选的日期源；缺失返回空串（因子按 0 计）。
    """
    try:
        text = md_path.read_text(encoding="utf-8")
    except Exception:  # noqa: BLE001 — 单文件读失败不拖垮索引
        return "", ""
    fm = re.match(r"^---\s*\n(.*?)\n---", text, re.S)
    if not fm:
        return "", ""
    body = fm.group(1)
    tm = re.search(r"^trigger:\s*(.+)$", body, re.M)
    dm = re.search(r"^modified:\s*(.+)$", body, re.M)
    if not dm:
        # 平台自动时间戳写在 metadata 块内（缩进 modified:），顶层无值时回退读取，
        # 否则 recency 因子在真实数据下恒为 0（死因子）。
        dm = re.search(r"^\s{2,}modified:\s*(.+)$", body, re.M)
    return (tm.group(1).strip() if tm else ""), (dm.group(1).strip()[:10] if dm else "")

def _load_memory_index(path: Path) -> list[dict]:
    """memory 索引行 `- [Title](file.md) — hook`：Title 拆词 + hook 描述作锚点。

    教训文件带 frontmatter `trigger:` 时追加进 anchor 参与匹配（无该字段行为
    不变）；trigger 单独存字段供注入时标注命中来源（title/hook/trigger 三来源）。
    """
    entries: list[dict] = []
    if not path.exists():
        return entries
    for ln in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"- \[([^\]]+)\]\(([^)]+)\)\s*[—-]+\s*(.+)", ln)
        if m:
            title, rel, hook = m.groups()
            md_path = path.parent / rel.strip()
            trigger = _frontmatter_trigger(md_path)
            entries.append({
                "src": f"memory:{path.parent.name}",
                "title": title.strip(),
                "path": str(md_path),
                "summary": hook.strip(),
                "anchor": f"{title} {hook} {trigger}".rstrip(),
                "trigger": trigger,
            })
    return entries
