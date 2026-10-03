#!/usr/bin/env python3
"""collect.py — PostToolUse 钩子：全局调用日志采集器。

每次 Skill/Agent 工具调用后由 settings.json 的 PostToolUse hook 触发，
把调用记录追加到 skill-evolution/registry/invocations.jsonl。

定位：全局调用日志=覆盖度唯一数据源（单轨真值），session-review.py
的 scan_skill_coverage 与触发语料校准据此消费。per-skill registry 已退役
（历史留痕不再写入）。hook 每次都跑故只 append 一行。
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

# 脚本位于 skill-evolution/scripts/，registry 在同级上一层的 registry/
REGISTRY = Path(__file__).resolve().parent.parent / "registry" / "invocations.jsonl"


def extract_target(tool_name: str, tool_input: dict) -> str:
    """从 hook 入参提取被调用对象标识。

    Skill 调用取 skill 名；Agent 调用不一定关联 skill，用 subagent_type
    作标识，缺则取 description 前 40 字，便于在日志里辨认是哪个 agent。
    """
    if not isinstance(tool_input, dict):
        return ""
    if tool_name == "Skill":
        return tool_input.get("skill") or ""
    if tool_name == "Read-SKILL":
        return tool_input.get("skill") or ""
    if tool_name == "Agent":
        return tool_input.get("subagent_type") or (tool_input.get("description") or "")[:40]
    return ""


def extract_user_input(envelope: dict) -> str:
    """从 envelope 提取用户原始输入（触发语料采集）。

    PostToolUse hook envelope 含 user_input 字段（用户当前会话输入）。
    限制长度避免过大（200 字符），用于后续触发语料分析优化 skill description。

    2026-09-25 补采集（BACKLOG T25 次级 gap「user_input 死字段，设计有 0 行有值」）：
    不同 harness 版本 envelope 键名不一，user_input 恒空时按序回退 prompt/user_prompt
    两个常见键；仍取不到则维持空串（死字段现状不因回退引入新值形态）。
    """
    for key in ("user_input", "prompt", "user_prompt"):
        val = envelope.get(key)
        if isinstance(val, str) and val.strip():
            return val[:200]
    return ""


def tail_user_input(envelope: dict) -> str:
    """user_input 死字段回填（2026-09-25 方向D C1 续探轮）：envelope 无值时
    从本会话转录尾部取最后一条真实 user 消息文本（排除 tool_result 行），复用
    inherited_model 的 tail 64KB 限读模式；纯写者补字段零新机制。下游
    session-review scan_calibration_skill_triggers 现结构性饿死（非空率 2/90），
    本补丁为其解锁语料源。"""
    tp = envelope.get("transcript_path")
    if not tp:
        return ""
    try:
        size = os.path.getsize(tp)
        # 递进尾窗：真实 user 文本可被长工具回合推出 64KB 窗（2026-09-25 实测 0/5），
        # 逐级扩到 512KB/2MB，找到即止；行倒序扫，跳过 tool_result 型 user 行。
        for window in (65536, 524288, 2097152):
            with open(tp, "rb") as f:
                f.seek(max(0, size - window))
                tail = f.read().decode("utf-8", "ignore")
            for line in reversed(tail.splitlines()):
                if '"type"' not in line or '"user"' not in line:
                    continue
                try:
                    obj = json.loads(line)
                except Exception:
                    continue
                if obj.get("type") != "user" or obj.get("isSidechain"):
                    continue
                content = obj.get("message", {}).get("content")
                texts = []
                if isinstance(content, str):
                    texts.append(content)
                elif isinstance(content, list):
                    for blk in content:
                        if isinstance(blk, dict) and blk.get("type") == "text":
                            texts.append(blk.get("text", ""))
                txt = " ".join(t for t in texts if t).strip()
                if txt:
                    return txt[:200]
    except Exception:
        return ""
    return ""


def extract_success(tool_response, tool_name: str = "") -> str | None:
    """从 tool_response 提取成功/失败标志（容错，偏保守）。

    PostToolUse hook stdin 含 tool_response（工具返回）。结构因工具而异，故只检测
    明显错误标志、不轻易判失败——避免误标。None=无法判定则不写该字段。
    session-review 据此检测"高频失败 skill → 待改进"，补采集环质量维度。

    2026-09-14 修复假信号管道：token98 战役发现 6873 条留痕 fail=0（无生产者消费端
    恒 0 假信号同类项）——原判据漏掉 dict.is_error、content 列表内文与 Bash 非零
    exit code 三类真实失败形态。仍保守：判不了返回 None，宁缺勿误标。
    2026-09-28 T103 Agent 形态扩展（实施前研究臂 567 条实测：async_launched 92.9%/
    sync completed 6.5%/启动失败 str 0.5%）：R1 status=completed→ok（sync 交付，与
    Skill 口径对齐）；R2 async_launched→None（启动时刻无结局，防「启动即 ok」假
    信号）；R3/R4 status failed|error→fail、其他值（stopped 等）→None（主动停非
    失败）；R5 str 前缀 Error:→fail（仅前缀锚定防报告正文误杀）。R1-R5 按
    tool_name=="Agent" 门控，防其他工具 response 恰含 status 键误判。
    """
    if tool_response is None:
        return None
    if tool_name == "Agent":
        if isinstance(tool_response, dict):
            status = tool_response.get("status")
            if status == "completed":
                return "ok"
            if status in ("failed", "error"):
                return "fail"
            if status:  # async_launched/stopped/cancelled 等一切非 completed 非失败值
                return None
            return _extract_success_base(tool_response)
        if isinstance(tool_response, str) and tool_response.lstrip().startswith("Error:"):
            return "fail"
        return _extract_success_base(tool_response)
    return _extract_success_base(tool_response)


# 显式失败标记（T111 判据重写 2026-09-28 消化轮；与 collect-all-tools.py
# FAIL_MARKERS 镜像同批）：语义裁定=ok 指「工具执行完成」（非业务正确性——业务正确性
# 本就不可从输出机械判定），fail 指显式错误形态。原「宁缺勿误标」致 3.9 万行恒 None
# （可判率审计 0/38202，AP-2 anti-pattern），失败率指标全样本死信号；现 ok/fail/None
# 三态分列。扩表依据=真实 tool_result 形态采样（is_error 流/Exit code N 前缀）+高频
# harness 报错文案；误杀面（正文恰含标记词）仅入计数不执法，可接受。
FAIL_MARKERS = (
    "traceback", '"error"', "command failed", "exit code",
    "operation not permitted", "command not found", "no such file",
    "permission denied", "connection refused", "syntaxerror",
    "fatal:", "unhandled exception", "tool_error", "api error",
)


def _judge_text(s: str) -> str | None:
    """字符串判据主体（T111 重写；dict 分支与 str 分支共用，两镜像同批）。"""
    low = s.lower()
    if any(m in low for m in FAIL_MARKERS):
        return "fail"
    if re.search(r"\bexit code[: ]+[1-9]\d*\b", low):
        return "fail"
    # 完成语义（T111 重写）：非空输出且无失败标记=ok；空输出判不了仍 None
    return "ok" if s.strip() else None


def _extract_success_base(tool_response) -> str | None:
    """原判据主体（2026-09-14 三类失败形态；2026-09-28 T111 重写可判率语义），Agent 分支收尾与普通工具共用。"""
    if tool_response is None:
        return None
    if isinstance(tool_response, dict):
        if tool_response.get("error"):
            return "fail"
        if tool_response.get("is_error"):
            return "fail"
        if "success" in tool_response:
            return "ok" if tool_response["success"] else "fail"
        # 命令输出形态（2026-09-29 生产探针实锤：Bash 类 response 为 stdout/stderr dict，
        # 原 content-only 判据全 None=生产链 0 判定真断点）；exitCode 数值为准，
        # stdout+stderr 合流走字符串判据；仅空输出且 exitCode=0 判 ok（Bash true 形态）
        for _k in ("stdout", "output", "result", "text"):
            if _k in tool_response:
                ec = tool_response.get("exitCode", tool_response.get("exit_code"))
                if isinstance(ec, int) and ec != 0:
                    return "fail"
                _txt = "\n".join(str(v) for k2, v in tool_response.items()
                                 if k2 in (_k, "stderr", "output", "result", "text")
                                 and isinstance(v, str))
                if _txt.strip():
                    return _judge_text(_txt)
                return "ok" if isinstance(ec, int) else None
        # content 列表（Anthropic 工具结果标准形态）：抽取 text 块做字符串判据
        content = tool_response.get("content")
        if isinstance(content, list):
            texts = [b.get("text", "") for b in content
                     if isinstance(b, dict) and isinstance(b.get("text"), str)]
            if texts:
                return extract_success("\n".join(texts))
        # 文件类工具形态（2026-09-29 T-B1 活体探针实锤，/tmp/claude/tb1-raw-responses.jsonl）：
        # Read={type:"text",file:{filePath,content,numLines,...}}、Edit={filePath,
        # oldString,newString,structuredPatch,...}、Write={type:"create",filePath,
        # content,...}——均无 error/is_error/success/stdout 键，原判据全 None=行级 0 判定
        # 残留断点。结构化结果返回即「执行完成」语义 ok；失败形态不经 PostToolUse
        # （活体实测 Read miss/Bash exit 1 均无 hook 行），无新增误杀面。
        file_obj = tool_response.get("file")
        if isinstance(tool_response.get("filePath"), str) or isinstance(file_obj, dict):
            return "ok"
        return None
    if isinstance(tool_response, str):
        return _judge_text(tool_response)
    # 顶层 list（2026-09-29 T-B1 活体探针实锤：mcp 类 response=[{type:"text",text}]
    # 列表形态，原判据对非 dict 非 str 直接 None）：合流 text 块走字符串判据
    if isinstance(tool_response, list):
        texts = [b.get("text", "") for b in tool_response
                 if isinstance(b, dict) and isinstance(b.get("text"), str)]
        if texts:
            return _judge_text("\n".join(texts))
    return None


def extract_effort_trace(text: str) -> str | None:
    """提取 effort 固定格式留痕行（P0-3，格式 canonical=model-governance.md §5）。

    主控升 high 时按 §5 留痕「本档 effort=…，触发器=…」；本采集器把该行原样
    落 invocations 单轨（effort_trace 事件；usage-stats 探头消费未实现——样本门预注册中，勿在探针前按此口径出报告）。
    只认固定前缀防误采普通叙述；正则放宽空格差异，字段内容不解析（裁决留人工）。
    """
    m = re.search(r"本档\s*effort\s*=\s*([^，,。；\n]{1,20})[，,]\s*触发器\s*=\s*([^\n]{1,80})", text)
    if not m:
        return None
    return f"effort={m.group(1).strip()} trigger={m.group(2).strip()}"


# 主控「直读 SKILL.md 执行」绕过 Skill 工具是既有采集盲区（2026-09-13 实测漏记 91%：
# 9 部门 skill 23 次执行仅录 2 次），Read 命中 SKILL.md 记弱信号补分母。
# Read≠执行的语义噪声由消费侧权重判定兜底（≥1 strong 或 ≥2 weak 才算活跃），
# 不在此处猜语义。正则守门：形态为双根绝对路径，阳性对照 66/66 全命中。
SKILL_READ_RE = re.compile(r"/skills/([A-Za-z0-9_-]+)/SKILL\.md$")


def _norm_model_tier(raw) -> str:
    """T94 收敛（2026-09-28）：实现迁 shared_state.norm_model_tier 单源
    （镜像副本删除，兑现本 docstring 原收敛义务），本壳保留调用点兼容。"""
    from shared_state import norm_model_tier
    return norm_model_tier(raw)


def inherited_model(envelope: dict) -> str | None:
    """KPI5 写者回填（2026-09-18 轮 V1 证伪裁决落地）：Agent 未显式传
    model 时从本会话转录末条 assistant message 回填继承档。数据源实证存在
    （PostToolUse envelope 标配 transcript_path，转录 assistant 消息含 model 字段），
    纯写者补字段零新机制；tail 64KB 限读防大转录整载。"""
    tp = envelope.get("transcript_path")
    if not tp:
        return None
    try:
        size = os.path.getsize(tp)
        with open(tp, "rb") as f:
            f.seek(max(0, size - 65536))
            tail = f.read().decode("utf-8", "ignore")
        hits = re.findall(r'"model"\s*:\s*"([^"]+)"', tail)
        return hits[-1][:32] if hits else None
    except Exception:
        return None


def main() -> int:
    try:
        raw = sys.stdin.read()
        envelope = json.loads(raw) if raw.strip() else {}
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        REGISTRY.parent.mkdir(parents=True, exist_ok=True)
        # PostToolUse hook：envelope 含 tool_name/tool_input/tool_response/user_input
        tool_name = envelope.get("tool_name", "")
        tool_input = envelope.get("tool_input", {}) or {}
        if tool_name == "Read":
            m = SKILL_READ_RE.search(str(tool_input.get("file_path", "")))
            if m:
                tool_name = "Read-SKILL"  # 弱信号：直读执行/引用不区分，消费侧加权
                tool_input = {"skill": m.group(1)}
        record = {
            "ts": ts,
            # session_id 会话聚合键（T25② 补采集，2026-09-22）：空串兜底对齐同 registry
            # 嫡亲 collect-all-tools.py，禁 null（消费侧 .get 直取防 None 字符串）
            "session_id": str(envelope.get("session_id") or ""),
            "tool": tool_name,
            "target": extract_target(tool_name, tool_input),
        }
        if tool_name == "Agent":  # R2 归因分母：spawn 档位/隔离标签（N 探索 K1 #1a）
            for _k in ("model", "effort", "isolation"):
                _v = tool_input.get(_k)
                if _v:
                    record[_k] = _v
        # 采 spawn 模型路由（批次二项 3，model-config-campaign-20260916）：Agent 调用
        # 显式传的 model 类别名（如 sonnet/opus）——升级率对账数据源；未传=继承会话档。
        if tool_name == "Agent":
            model = tool_input.get("model")
            if model:
                record["model"] = str(model)[:32]
            else:  # KPI5 继承档回填（inherited_model docstring 见上）
                inh = inherited_model(envelope)
                if inh:
                    record["model"] = inh
                    record["model_source"] = "inherited"
            # T33① 写端接线（2026-09-26）：双写 model 原文+model_tier 四键（原文保留审计
            # 可回溯，tier 供 KPI 分母机械消费）；无 model 信息时落 unattributed 显式键
            record["model_tier"] = _norm_model_tier(model or inherited_model(envelope))
        # 采用户原始输入（触发语料采集，限制长度避免过大）
        user_input = extract_user_input(envelope) or tail_user_input(envelope)
        if user_input:
            record["user_input"] = user_input
        # 采成功/失败（容错：无 tool_response 或无法判定则省略该字段）
        success = extract_success(envelope.get("tool_response"), tool_name=envelope.get("tool_name", ""))
        if success is not None:
            record["success"] = success
        # 采 effort 升档留痕（P0-3）：用户输入或回执文本中出现固定格式行即记一条
        trace = extract_effort_trace(user_input) or None
        if trace is None and isinstance(envelope.get("tool_response"), str):
            trace = extract_effort_trace(envelope["tool_response"])
        if trace:
            with REGISTRY.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps({"ts": ts,
                                     "session_id": record["session_id"],
                                     "tool": "effort-trace", "target": trace},
                                    ensure_ascii=False) + "\n")
        with REGISTRY.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as exc:  # noqa: BLE001 — hook 不能阻断主流程，捕获后写 stderr 可见、exit 0
        print(f"[collect] 采集失败: {exc}", file=sys.stderr)
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
