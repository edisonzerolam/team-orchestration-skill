# -*- coding: utf-8 -*-
"""tests/test_team_assets.py — 专家团资产一致性 + 补齐完整性门禁。

将 scripts/check_team_consistency.py 与 scripts/check_agent_completeness.py
纳入 run_smoke 冒烟通道：
  - consistency：39 团队 plugin.json 声明 == 磁盘资产（无 stub 缺文件命名冲突）
  - completeness：白名单（本次补齐）团队 agent 满足 agent-template 完整模板

依据 TC-20260809：专家团资产补齐 + 编辑引擎增强方案（v2.0 final）。

注（v3.6 / test-workflow 回归修正）：_run 原用 subprocess.run(capture_output=True)
捕获嵌套子进程 stdout，在 DSH/Windows 沙箱的 piped-stdio 边界下返回 None，导致
test_agent_completeness 结构性假阴。改为同进程内前导脚本把脚本 stdout 重定向到
临时文件后在父进程读回，全程不跨管道捕获子进程输出（规避 harness stdio:'pipe'
EPERM 边界）。
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
PY = sys.executable


def _run(script: str) -> str:
    """在 DSH/Windows piped-stdio 边界下可靠运行脚本并取回 stdout。

    避免 subprocess.run(..., capture_output=True) 的嵌套管道捕获（该路径在
    danger-full-access 下仍会因 sandbox 不允许开命名管道而返回 None/空，见
    harness 文档 stdio:'pipe' 边界）。改为把 stdout/stderr 直接写到一个
    父进程预先打开的临时文件句柄（非管道），运行后读回该文件。
    """
    fd, tmp = tempfile.mkstemp(suffix=".out")
    try:
        # 编码健壮性（v3.8 · TC-20260816-3）：子进程强制 UTF-8 输出
        # （PYTHONIOENCODING 影响 stdout 重定向到文件句柄时的编码，防 GBK locale
        # 下写 GBK 字节、父进程 utf-8 读回崩于 byte 0xc1）；读回 errors="replace" 兜底。
        env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            r = subprocess.run([PY, str(SCRIPTS / script)], stdout=f,
                               stderr=subprocess.STDOUT, env=env)
        if r.returncode != 0:
            with open(tmp, encoding="utf-8", errors="replace") as f:
                tail = f.read()[-2000:]
            raise AssertionError(f"{script} exit={r.returncode}\n{tail}")
        with open(tmp, encoding="utf-8", errors="replace") as f:
            return f.read()
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def test_team_consistency():
    out = _run("check_team_consistency.py")
    assert "✅" in out or "一致" in out, out


def test_agent_completeness():
    out = _run("check_agent_completeness.py")
    assert out.strip().endswith("exit 0") or "满足完整模板" in out, out
    assert "❌" not in out, out
