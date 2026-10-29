"""Explicit asset/data roots and atomic local writes; no host configuration lookup."""
from __future__ import annotations
import os
import tempfile
from pathlib import Path

def _configured_roots():
    """显式双根缺一拒绝，避免资产与数据混写。"""
    asset = os.environ.get("ADAS_ASSIST_ASSET_ROOT")
    data = os.environ.get("ADAS_ASSIST_DATA_ROOT")
    if not asset or not data:
        raise ValueError("ADAS_ASSIST_ASSET_ROOT and ADAS_ASSIST_DATA_ROOT must be supplied together")
    asset_path, data_path = Path(asset), Path(data)
    if not asset_path.is_absolute() or not data_path.is_absolute():
        raise ValueError("adas-assist roots must be absolute paths")
    if not (asset_path / "skills").is_dir():
        raise ValueError("ADAS_ASSIST_ASSET_ROOT must contain skills/")
    return asset_path.resolve(), data_path.resolve()

def validate_data_path(path: Path) -> Path:
    """显式双根模式拒绝已有软链接/父路径把写入导向数据根以外。"""
    configured = _configured_roots()
    path = Path(path)
    if configured:
        resolved = path.resolve()
        root = configured[1]
        if resolved != root and root not in resolved.parents:
            raise ValueError("path escapes ADAS_ASSIST_DATA_ROOT")
    return path

def atomic_write(path: Path, text: str) -> None:
    """同目录临时文件 + fsync + os.replace：读方永远看不到半写内容。

    与 flock 正交：锁串行化写者，原子替换保护无锁读方。fsync 保证 replace 前
    内容落盘（崩溃后旧文件完好，不存在空文件态）。
    """
    path = validate_data_path(path)
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

def asset_root() -> Path:
    return _configured_roots()[0]

def data_root() -> Path:
    return _configured_roots()[1]
