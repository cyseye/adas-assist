#!/usr/bin/env python3
"""shared_state.py — 共享运行时状态读写 helper：flock 互斥 + 临时文件 os.replace 原子写。

为什么需要：PENDING.md / reflex-*-state.json 是 gitignored 运行时共享文件，多个
session 的 hook 进程并发读-改-写会互相覆盖（已实证「狼来了」降噪失效事故），且无
git 仲裁兜底。本模块是所有 hook 脚本写这些文件的唯一合法通道。

设计要点（为什么）：
- 锁文件与数据文件分离，放 .claude/.build/locks/，永不删除——unlink 锁文件后
  新旧持锁者锁住不同 inode，互斥失效（flock 正确性前提）。
- 只用 LOCK_NB 轮询 + 超时，绝不用阻塞式 flock——持锁进程异常死亡时阻塞式会
  永久挂死 hook；超时由调用方统一降级（跳过写），共享状态均为派生/可重算数据，
  最坏损失 = 数据迟到一周期而非损坏。
- atomic_write 使无锁读方（如 session-start 读 PENDING）永远看不到半写内容。
- 本文件是唯一允许裸写共享状态的模块，其余脚本必须经本 helper。
"""
from __future__ import annotations

import contextlib
import json
import os
import sys
import tempfile
import time
from pathlib import Path


# 双根解析（迁移 ~/.claude 后）：资产=单源随脚本走（__file__ 上溯），数据=随项目走
# （cwd 上溯）。旧 _repo_root 单根 __file__ 上溯在 ~/.claude 内会错命中 home，导致
# 运行时数据写进用户目录——与「数据跟随项目」裁决冲突，故拆双根。
def asset_claude() -> Path:
    """单源资产根 ~/.claude：本文件所在处（skills/_shared/decisions 等资产随迁）。
    判据=含 skills/ 实体而非裸 .claude 目录——幻影数据根（写入方 mkdir 造出的
    ~/.claude/.claude）无 skills/，不会被误认成资产根（2026-09-17 自中毒实证）。"""
    for parent in Path(__file__).resolve().parents:
        if (parent / ".claude" / "skills").is_dir():
            return parent / ".claude"
    return Path.home() / ".claude"


def data_claude() -> Path:
    """运行时数据根：cwd 上溯第一个含 .claude 的目录（找不到回落 cwd，数据就近落盘）。
    资产仓内部的 .claude（如 ~/.claude/.claude）不算命中——那是写入方 mkdir(parents=True)
    在资产根 cwd 下造出的幻影数据根（2026-09-17 实证：一旦被创建即自中毒劫持后续解析），
    资产仓内 cwd 的数据根恒为资产根本身。"""
    cwd = Path.cwd().resolve()
    asset_root = asset_claude().resolve()
    for cand in [cwd, *cwd.parents]:
        cc = cand / ".claude"
        # 资产根本身是合法命中（资产仓的运行数据就落这儿）；只排资产仓内部更深的嵌套
        if cc.is_dir() and (cc.resolve() == asset_root or asset_root not in cc.resolve().parents):
            return cc
    return cwd / ".claude"


REPO = data_claude().parent  # 项目根（运行时数据域：.build/.state/plans/memory 随项目）


def project_slug() -> str:
    """Claude Code projects/ 目录 slug 单源（T129 2026-09-29 收敛三处独立推导）：
    项目根中 / 与 . 均换 - 加前导 -。资产仓内 cwd（data==asset）用数据根本身——
    此时 REPO 解析为 home，slug 须取 ~/.claude 本身（"-Users-cc--claude"）。
    同型缺陷史：knowledge-recall T104、search-sessions sys-01 两处漏 dot 各自
    独立推导所致——此后新增 projects/ 路径消费方一律 import 本函数，禁再写局部推导。"""
    d = data_claude()
    root = d if d.resolve() == asset_claude().resolve() else d.parent
    return str(root).replace("/", "-").replace(".", "-")
_BUILD = data_claude() / ".build"
STATE_START = _BUILD / "reflex-start-state.json"  # session-start 唯一写者
STATE_STOP = _BUILD / "reflex-stop-state.json"    # reflex-check 唯一写者

# 锁竞争极端场景下的等待上限：锁内操作均毫秒级，1s 覆盖异常争用；超时跳过写保
# hook 不挂死（各调用点统一降级策略，见调用方 except 分支）
LOCK_TIMEOUT = 1.0
LOCK_POLL = 0.05


@contextlib.contextmanager
def flock_ctx(name: str, timeout: float = LOCK_TIMEOUT):
    """对 .build/locks/{name}.lock 取排他 flock，锁内执行读-改-写。

    锁文件仅作互斥介质不写内容；异常死亡时 OS 自动释放锁，LOCK_NB 轮询保证
    等待方超时可退（阻塞式 flock 无法探测死锁）。仅 Linux/macOS 生效——fcntl
    不可用的平台抛 ImportError，由各 hook 外层容错兜底（stderr + exit 0），
    不阻塞会话主流程。
    """
    import fcntl
    lock_path = _BUILD / "locks" / f"{name}.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fh = open(lock_path, "a+")
    try:
        deadline = time.monotonic() + timeout
        while True:
            try:
                fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise TimeoutError(f"shared-state 锁超时: {name}") from None
                time.sleep(LOCK_POLL)
        yield
    finally:
        try:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
        except Exception:  # noqa: BLE001 — 释放失败随 fd close 兜底
            pass
        fh.close()


def read_text_lazy(path: Path) -> str:
    """读文本；缺失/读失败返回空串（PENDING 消费方容忍）。"""
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def read_json_lazy(path: Path) -> dict:
    """读 JSON；缺失/损坏/非 dict 一律返回 {}——状态文件损坏不应崩 hook。"""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def io_budget(key: str):
    """读 io-budgets.json 指定键（数值单源：hook/skill 禁复写常量，P0-1 清偿）。

    fail-closed 语义：任何读取失败返回 None，调用方跳过受控行为（注入/截断），
    禁在代码侧内置领域数值兜底——JSON↔代码两处同改即漂移（修正清单 V2 关键风险）。
    """
    cfg = read_json_lazy(asset_claude() / "skills" / "_shared" / "io-budgets.json")
    return cfg.get(key) if cfg else None


def atomic_write(path: Path, text: str) -> None:
    """同目录临时文件 + fsync + os.replace：读方永远看不到半写内容。

    与 flock 正交：锁串行化写者，原子替换保护无锁读方。fsync 保证 replace 前
    内容落盘（崩溃后旧文件完好，不存在空文件态）。
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.chmod(tmp, 0o644)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def jsonl_tail(path: Path, n: int = 50) -> list[dict]:
    """读末尾 ≤n 条完整 JSON 行（倒序取够后回正序）。

    坏尾行/空行跳过：O_APPEND 单行写在 POSIX 下原子，半行只可能来自写进程崩溃，
    消费方跳过优于报错（报错会把崩溃现场变成下一次 hook 故障）。
    """
    if not path.exists():
        return []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []
    out: list[dict] = []
    for line in reversed(text.splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
        if len(out) >= n:
            break
    out.reverse()
    return out


def count_jsonl_lines(path: Path) -> int:
    """统计完整 JSON 行数（坏行不计）——计数虚高会误触覆盖度阈值（死/冷 skill 判定）。"""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return 0
    n = 0
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            json.loads(line)
            n += 1
        except json.JSONDecodeError:
            pass
    return n


def rotate_jsonl(path: Path, key_prefix: str, keep: int | None = None) -> str | None:
    """registry jsonl 轮转（议题G3）：超阈 mv→gzip 同名日期件，保留最近 keep 个。

    阈值单源 io-budgets.evolution_cadence（<key_prefix>_rotate_lines /
    <key_prefix>_rotate_bytes），键缺失或 ≤0 =功能未启用（fail-closed，同
    reflex_hooks_truncate_lines 语义）。保留数 keep 同源读
    registry_rotate_keep（2026-09-19 finish-check 收敛：调用方硬编码 keep=3
    双点删除）；键缺失回退 3 并 stderr 提示（fail-open 但留痕）。
    返回轮转动作描述串（供写者 stderr 留痕），
    未触发返回 None。flock 串行化（并发 PostToolUse hook 同时轮转会双份压缩）。
    轮转后原文件消失，下次 append 自然重建——固定名读者语义兼容（历史数据在
    gz 件中，读者按窗口统计不受影响）。
    """
    cad = io_budget("evolution_cadence") or {}
    if keep is None:
        if f"{key_prefix}_rotate_keep" in cad:
            keep = int(cad[f"{key_prefix}_rotate_keep"])
        else:
            keep = 3  # 键缺失回退（fail-open 但 stderr 留痕）
            print(f"[shared_state.rotate_jsonl] {key_prefix}_rotate_keep 键缺失，"
                  f"回退 keep=3（单源 io-budgets.evolution_cadence 应补键）",
                  file=sys.stderr)
    max_lines = int(cad.get(f"{key_prefix}_rotate_lines") or 0)
    max_bytes = int(cad.get(f"{key_prefix}_rotate_bytes") or 0)
    if max_lines <= 0 and max_bytes <= 0:
        return None
    try:
        if not path.exists():
            return None
        size = path.stat().st_size
        if max_lines > 0:
            n = count_jsonl_lines(path)
            over = n > max_lines
            lines_seen = n
        else:
            over = size > max_bytes
            lines_seen = -1
        if not over and (max_bytes <= 0 or size <= max_bytes):
            # 字节维未启用（=0）时不得参与判定——否则 size<=0 恒假会把「行数未超」
            # 的文件也判超阈逐次轮转（2026-09-28 反臂夹具实证：reflex_hooks 只配
            # lines 键时 1 行文件每写必轮转）
            return None
        import gzip
        with flock_ctx(f"rotate-{path.name}", timeout=LOCK_TIMEOUT):
            date = time.strftime("%Y%m%d")
            gz = path.parent / f"{path.stem}-{date}.jsonl.gz"
            seq = 1
            while gz.exists():  # 同日二次轮转防覆盖
                gz = path.parent / f"{path.stem}-{date}-{seq}.jsonl.gz"
                seq += 1
            src = path.read_bytes()
            with gzip.open(gz, "wb", compresslevel=6) as fh:
                fh.write(src)
            path.unlink()  # 下次 hook append 重建新文件
        # 按 mtime 排序（adv#6 修复 2026-09-28）：同日 seq 件（-20260928-1.gz）字典序
        # 排在 base 件（-20260928.gz）之前，按名排序会把最新档先修剪掉
        olds = sorted(path.parent.glob(f"{path.stem}-*.jsonl.gz"), key=lambda p: p.stat().st_mtime)
        pruned = 0
        for old in olds[:-keep] if keep > 0 else olds:
            old.unlink()
            pruned += 1
        n_txt = f"{lines_seen}行" if lines_seen >= 0 else "行数未统计（字节阈值触发）"
        return (f"rotated {path.name}: {n_txt}/{size}B 超 "
                f"{key_prefix}_rotate_lines={max_lines}/bytes={max_bytes} → {gz.name}"
                + (f"（清理更老 {pruned} 件）" if pruned else ""))
    except Exception as exc:  # noqa: BLE001 — 轮转是增益不是刚需，失败不阻断 hook 写入
        print(f"[shared_state.rotate_jsonl] {path.name} 轮转失败（跳过）: {exc}",
              file=sys.stderr)
        return None


def load_partition(kind: str) -> dict:
    """读单写者状态分区；文件缺失/为空返回空 dict（首日冷启动语义）。"""
    path = STATE_START if kind == "start" else STATE_STOP
    return read_json_lazy(path)

def norm_model_tier(raw) -> str:
    """model 自由文本 → 四类归一键（T94 收敛单源，2026-09-28：原 weekly-eval
    与 collect 双副本自此函数收敛；T94 病灶=`glm` 关键字入 main 侧——本环境执行体
    实际路由 glm-5.3-flash，`glm` 泛匹配把执行档记成 main_only，致「升 main 事件=0、
    opus 仅关键节点不可验证」。修正：`glm` 从主面词表移除、`flash` 入执行面词表；
    主面只认显式角色词（主控/主裁/主模型/裁决/终审/ceo）与 main/opus/fable；裸 `glm` 双义（主/执行族皆 glm-*）不归两侧=unattributed。
    口径单源=本函数，两消费方 import 禁再镜像。"""
    s = str(raw or "").strip().lower()
    if not s:
        return "unattributed"
    has_exec = any(k in s for k in ("sonnet", "haiku", "flash", "执行", "exec", "spawn"))
    has_main = any(k in s for k in ("主控", "主裁", "主模型", "裁决", "终审", "ceo", "opus", "main", "fable"))
    if has_main and has_exec:
        return "main_plus_exec"
    if has_exec:
        return "exec_only"
    if has_main:
        return "main_only"
    return "unattributed"
