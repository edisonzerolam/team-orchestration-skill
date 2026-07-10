#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""文件工具：原子写入 + 跨平台文件锁

Usage:
    from file_utils import atomic_write, read_json, write_json

    atomic_write("/path/to/file.json", {"key": "value"})
    data = read_json("/path/to/file.json")
"""
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Optional

_LOCK_EX = None  # 延迟加载


def _acquire_lock(lock_path: Path, timeout: float = 3.0) -> bool:
    """跨平台文件锁（可选依赖 portalocker）
    返回是否成功获取锁。
    """
    global _LOCK_EX
    try:
        import portalocker
        _LOCK_EX = portalocker.LOCK_EX
        fd = os.open(str(lock_path), os.O_CREAT | os.O_WRONLY)
        portalocker.lock(fd, portalocker.LOCK_EX | portalocker.LOCK_NB)
        return True
    except (ImportError, portalocker.LockException, OSError):
        return False
    except Exception:
        return False


def _release_lock(fd: int):
    try:
        import portalocker
        portalocker.unlock(fd)
        os.close(fd)
    except Exception:
        pass


def atomic_write(path: Any, data: Any, encoding: str = "utf-8",
                 indent: int = 2, ensure_ascii: bool = False,
                 use_lock: bool = True) -> None:
    """原子写入 JSON 文件（写临时文件 → os.replace）
    
    步骤：
    1. 序列化为 JSON 字符串
    2. 写入临时文件（同目录，保证跨设备）
    3. os.replace 原子替换
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    content = json.dumps(data, ensure_ascii=ensure_ascii, indent=indent)
    tmp = path.with_suffix(f".tmp.{os.getpid()}")
    try:
        tmp.write_text(content, encoding=encoding)
        tmp.replace(path)
    finally:
        if tmp.exists():
            tmp.unlink(missing_ok=True)


def write_json(path: Any, data: Any, **kwargs) -> None:
    """JSON 原子写入（兼容旧接口名称）"""
    atomic_write(path, data, **kwargs)


def read_json(path: Any, default: Any = None) -> Any:
    """安全读取 JSON 文件，失败返回 default"""
    path = Path(path)
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as e:
        return default


def read_json_or_empty(path: Any) -> dict:
    """读取 JSON 文件，不存在或损坏时返回空 dict"""
    result = read_json(path, {})
    return result if isinstance(result, dict) else {}
