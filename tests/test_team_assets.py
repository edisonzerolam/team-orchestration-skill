# -*- coding: utf-8 -*-
"""tests/test_team_assets.py — 专家团资产一致性 + 补齐完整性门禁。

将 scripts/check_team_consistency.py 与 scripts/check_agent_completeness.py
纳入 run_smoke 冒烟通道：
  - consistency：39 团队 plugin.json 声明 == 磁盘资产（无 stub 缺文件命名冲突）
  - completeness：白名单（本次补齐）团队 agent 满足 agent-template 完整模板

依据 TC-20260809：专家团资产补齐 + 编辑引擎增强方案（v2.0 final）。
"""
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
PY = sys.executable


def _run(script: str):
    res = subprocess.run([PY, str(SCRIPTS / script)], capture_output=True, text=True)
    if res.returncode != 0:
        raise AssertionError(
            f"{script} exit={res.returncode}\nstdout={res.stdout[-2000:]}\nstderr={res.stderr[:500]}"
        )
    return res.stdout


def test_team_consistency():
    out = _run("check_team_consistency.py")
    assert "✅" in out or "一致" in out, out


def test_agent_completeness():
    out = _run("check_agent_completeness.py")
    assert out.strip().endswith("exit 0") or "满足完整模板" in out, out
    assert "❌" not in out, out
