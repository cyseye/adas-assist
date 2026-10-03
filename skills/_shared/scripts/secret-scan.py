#!/usr/bin/env python3
"""secret-scan.py——G1/G2 共享扫描公共件（单源）。

地位声明（T20，2026-09-21 抽取）：本模块是双门扫描管道的**唯一实现**，由
  G1 skills/skill-evolution/scripts/g1-outbound-guard.py（_scan_variants 薄壳）
  G2 skills/skill-evolution/scripts/cc-commit-gate.py（_normalized_texts/
     _scan_encoded_line/_match 后验 薄壳）
消费。抽取依据：2026-09-21 轮⑥ G1/G2 双门三处同款修改（bounds 变体/滑窗拼接/
词粘连后验）触发预设演化条件——同类修改再发即抽公共件，双门勿再各自实现。
模式集单源仍是 _shared/security-patterns.json（本模块不持有模式，只收 pats 参数）。

三件公共逻辑：
  a) normalized_texts(s)——完整规范化变体池（G1/G2 实现并集）
  b) segment_candidates(text) / decoded_segments(text)——编码段提取+滑窗拼接+解码
  c) is_word_fused(text, match_start)——cred 类词粘连后验
零模型纯 regex；无 I/O、无副作用。
"""
import base64
import re
import unicodedata
import urllib.parse

# 零宽家族 U+200B/200C/200D/2060/FEFF + 软连字符 U+00AD（规范化首步剥除）
_INVISIBLE = "​‌‍⁠﻿­"
# T19⑥后续（2026-09-21 异质化探针实证 4 向绕过追加）：U+034F 组合连接符、
# U+180E 蒙古元音分隔符——均零宽不可见但不在上集合且 NFKC 不映射。剥除面
# 统一为「_INVISIBLE ∪ Unicode Cf 格式字符 ∪ U+034F」：Cf 类全为不可见格式
# 控制符（不含正常文本用字母/标点），不误伤可读文本；Mn 声调类不剥（防剥
# 正常带调文字）。
_EXTRA_INVISIBLE = "͏᠎"
# 二轮追加（2026-09-21 验证轮实锤 6 漏）：变体选择符 U+FE00-FE0F/U+E0100-E01EF
# （Mn 类但纯零宽选择语义，剥之不伤 U+0300-U+036F 正常声调）、Hangul 填充
# U+115F/U+1160、非字符 U+FFFE/FFFF（含各平面尾 FFFE/FFFF，非字符判据）。
def _is_invisible(c: str) -> bool:
    cp = ord(c)
    return (c in _INVISIBLE or c in _EXTRA_INVISIBLE
            or unicodedata.category(c) == "Cf"
            or 0xFE00 <= cp <= 0xFE0F or 0xE0100 <= cp <= 0xE01EF
            or cp in (0x115F, 0x1160)
            or cp == 0xFFFE or cp == 0xFFFF
            or (cp & 0xFFFE) == 0xFFFE and cp >= 0x10000)  # 各平面尾非字符


def strip_invisible(s: str) -> str:
    return "".join(c for c in s if not _is_invisible(c))


def normalized_texts(s: str) -> dict[str, str]:
    """完整规范化变体池（G1/G2 实现并集）。

    管道：①剥不可见字符→②去空白 collapse→③Nd 数字归一（unicodedata.digit，
    仅 ord>127 的 isdigit 字符，封阿拉伯-印度数字；NFKC 不映射该类）→④NFKC→
    ⑤casefold（基于**保留空白**的 cleaned——collapse 会使 `Bearer\\s+token` 类
    关键字+空格模式失配，casefold 变体专职大小写面）→URL 解码迭代到不动点
    上限 5 层（每层产物入池，封多重嵌套编码）。

    G1/G2 原差异（并集说明）：
    - crossline：G2 既有消费方兼容别名，= clean（collapse 天然去换行）；G1 原无。
    - URL 变体双道（T19⑥ G1）：保留空白版 url{N}（保 \\b 与 \\s+ 语义）+ 去空白版
      url{N}c（封空白分段）。G2 原仅去空白版且深度1名为 `url`——为兼容别名保留
      `url`（=url1c）。池取并集后双门覆盖面为超集，原有变换全保留。
    """
    cleaned = strip_invisible(s)
    collapsed = re.sub(r"\s+", "", cleaned)
    digit_norm = "".join(str(unicodedata.digit(c)) if c.isdigit() and ord(c) > 127 else c
                         for c in collapsed)
    # bounds：字母↔数字边界重划（无空白文本 \b 不成立，须显式在交界插空格，
    # 封「api{ip}end」类粘字——V2.4 实测逃逸形态，字面量示例不入本件防自绊）
    bounds = re.sub(r"(?<=[A-Za-z])(?=\d)|(?<=\d)(?=[A-Za-z])", " ", digit_norm)
    texts = {"raw": s, "clean": collapsed, "crossline": collapsed,
             "digits": digit_norm, "bounds": bounds,
             "nfkc": unicodedata.normalize("NFKC", collapsed),
             "casefold": unicodedata.normalize("NFKC", cleaned).casefold(),
             # nopunct（二轮 2026-09-21）：去 `.`/`_`/`~` 标点分段但**保留空白与
             # `-`**——封「sk- 前缀+密文以标点两半相连」形态（`-` 须保留否则
             # sk- 前缀自毁）；保留空白使 \b 与词粘连后验语义不破坏，正常含点/
             # 下划线文本不产生新命中面
             "nopunct": re.sub(r"[._~]", "", cleaned)}
    # nodiact（二轮 2026-09-21）：Mn 组合声标**密度门控**剥离——密文逐字符插
    # U+0301 类声标致模式字符类被打断。全局剥 U+0300-U+036F 伤正常带调文字
    # （误伤红线），故仅在 Mn 占比 >20%（正常带调文本远低于此，插入spam ≈50%）
    # 时生成该变体；变体缺失时 G1/G2 自动跳过，不影响正常流量。
    if cleaned:
        mn = sum(1 for c in cleaned if unicodedata.category(c) == "Mn")
        if mn / len(cleaned) > 0.2:
            texts["nodiact"] = "".join(c for c in cleaned
                                       if unicodedata.category(c) != "Mn")
    # esc 变体（P7 堵法 2026-09-22）：\xHH 十六进制与 \NNN 八进制转义字面量
    # 解码（红队实锤 `\x2fUs[e]rs\x2fcc\x2f.ssh\x2fconfig` 全模式 MISS——
    # 自指例按立件惯例字符类伪装防本件自绊）。误伤
    # 防线三重：①密度门控——原文须含 ≥2 个转义序列才生成变体（单处字面转义
    # 串如正则文档/测试 payload 字面量不触发，本件与 g1/g2 测试件自证）；
    # ②只解 \xHH、2-3 位八进制与 \uHHHH/\u{H+}（轮⑭ 2026-09-22 扩：红队
    # 实锤 \u 家族与转义序列跨界截断/插空白两向全 MISS——surrogate 对先配对
    # 合成（允许序列间空白，封对拆码点），孤 \u 值直接 chr（孤代理仅在内存
    # 匹配面，不落盘）；≥2 序列时对去空白文本追加一支拼接变体封「\x2␣f」
    # 类截断）；③变体入池后仍须命中 L2 模式才算命中（命中回验），池多一支
    # 变体不影响无转义文本的匹配面。
    esc_seq = re.compile(
        r"\\x\{?([0-9a-fA-F]{2})\}?"
        r"|\\[uU]\{([0-9a-fA-F]{1,4})\}"
        r"|\\[uU]([0-9a-fA-F]{4})"
        r"|\\([0-7]{2,3})")
    esc_pair = re.compile(
        r"\\[uU]\{?([dD][89abAB][0-9a-fA-F]{2})\}?\s*"
        r"\\[uU]\{?([dD][cdefCD-EF][0-9a-fA-F]{2})\}?")

    def _esc_decode(src: str) -> str:
        paired = esc_pair.sub(
            lambda m: chr(0x10000 + ((int(m.group(1), 16) - 0xD800) << 10)
                           + (int(m.group(2), 16) - 0xDC00)), src)
        return esc_seq.sub(
            lambda m: (chr(int(m.group(1), 16)) if m.group(1)
                       else chr(int(m.group(2) or m.group(3), 16))
                       if (m.group(2) or m.group(3))
                       else chr(int(m.group(4), 8))), paired)

    _esc_seen: set[str] = set()
    for _src in (cleaned, collapsed):
        if len(esc_seq.findall(_src)) + len(esc_pair.findall(_src)) >= 2:
            _dec = _esc_decode(_src)
            if _dec not in _esc_seen and _dec not in texts.values():
                _esc_seen.add(_dec)
                texts["esc" if "esc" not in texts else "esc_ws"] = _dec
    cur = s
    for depth in range(1, 6):  # 解码到不动点，上限 5 层（防解码炸弹；封 ≥3 层嵌套编码）
        nxt = urllib.parse.unquote(cur)
        if nxt == cur:
            break
        cur = nxt
        spaced_u = strip_invisible(cur)
        texts[f"url{depth}"] = spaced_u
        texts[f"url{depth}c"] = re.sub(r"\s+", "", spaced_u)
    if "url1c" in texts:
        texts["url"] = texts["url1c"]  # G2 深度1 兼容别名（去空白）
    return texts


def segment_candidates(text: str) -> set[str]:
    """编码段静态提取 + 空白分段滑窗拼接子序列全试。

    ①静态：b64 字符集 ≥12（尾 `=` ≤2）与 hex ≥24 两类；②滑窗：同行内 ≥2 个
    连续「纯 b64 字符 token（body≥4）」依序拼接，连续子序列 run[i:j] 全试
    （≤15 组合）——噪声词（lookup 等普通词 body≥4 入 run）污染整串拼接致解码
    失败逃逸，子序列全试封之；拼接总长 ≥12 由 seg 侧约束。误伤防线=解码失败
    静默跳过 + 解码产物须中模式双重过滤。调用方传入的 text 须为规范化
    （剥不可见+保留空白逐行，或 collapse 整体）文本。标点分段容错（T19⑥后续
    2026-09-21，二轮扩）：额外对去 `._~` 与去 `._-~` 两版本重跑同一提取（封
    「b64 两半以标点相连」逃逸）；组合面=各版本静态提取+滑窗，滑窗 ≤15 组合
    约束不变，总量有界不爆炸。
    """
    segs: set[str] = set()
    for t in (text, re.sub(r"[._~]", "", text), re.sub(r"[._\-~]", "", text)):
        segs |= {m.group(0) for m in re.finditer(r"[A-Za-z0-9+/]{12,}={0,2}", t)}
        segs |= {m.group(0) for m in re.finditer(r"[0-9a-fA-F]{24,}", t)}
        run = []
        for tok in t.split() + [""]:
            if re.fullmatch(r"[A-Za-z0-9+/]{4,}={0,2}", tok):
                run.append(tok)
                continue
            if len(run) >= 2:
                for i in range(len(run)):
                    for j in range(i + 1, len(run) + 1):
                        seg = "".join(run[i:j])
                        if len(seg) >= 12:
                            segs.add(seg)
            run = []
    return segs


def decode_segment(seg: str):
    """单段解码：hex 段（≥24 纯 hex）先试 bytes.fromhex，失败回退 b64；
    解码异常/产物非 UTF-8 文本（真二进制如 sha256）返回 None 静默跳过
    ——此即误伤防线第二重。"""
    raw = None
    if re.fullmatch(r"[0-9a-fA-F]{24,}", seg):
        try:
            raw = bytes.fromhex(seg)
        except ValueError:
            pass
    if raw is None:
        try:
            raw = base64.b64decode(seg + "=" * (-len(seg) % 4), validate=True)
        except Exception:
            return None  # 非法编码段：静默跳过
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return None  # 解码后非文本（真二进制）：静默跳过


def decoded_segments(text: str):
    """segment_candidates 结果逐段解码，yield (seg, decoded_text)。"""
    for seg in segment_candidates(text):
        decoded = decode_segment(seg)
        if decoded is not None:
            yield seg, decoded


def is_word_fused(text: str, match_start: int) -> bool:
    """cred 类词粘连后验（V2.5）：命中前邻字符为字母 → 普通词尾粘连假
    sk-/Bearer（实测 task-orchestrator+description 跨行粘连误报）——凭证开头
    不可能嵌在词中。仅对 cred- 前缀模式 + 去空白系变体（COLLAPSED_PREFIXES）
    调用；保留空白变体 \b 自成立不需此后验。"""
    return match_start > 0 and text[match_start - 1].isalpha()
