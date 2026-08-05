# -*- coding: utf-8 -*-
"""tests/test_references.py — 引用完整性冒烟测试。

接入 run_smoke.py 后，每次运行冒烟测试都会自动校验技能内所有
本地文档引用（references/ scripts/ tests/）是否真实存在，
让"死链 / 缺失配套文件"在审计中自动暴露，而非拖到最后才发现。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_references as cr


def test_no_broken_local_references():
    scanned, refs, broken = cr.scan()
    assert not broken, (
        f"{len(broken)} 条本地引用无法解析（扫描 {scanned} 文件 / {refs} 引用）：\n"
        + "\n".join(f"  {doc}: {tok}" for doc, tok in broken)
    )
