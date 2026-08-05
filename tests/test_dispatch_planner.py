"""测试 dispatch-planner.py — 验证 A3 交付物模板注入（无 pytest 依赖）"""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
PY = sys.executable


def test_deliverable_template_fields():
    out = subprocess.run(
        [PY, str(SKILL / "scripts" / "dispatch-planner.py"), "--teams", "a-share-analysis", "--json"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    assert out.returncode == 0, out.stderr
    plan = json.loads(out.stdout)
    assert plan["teams"], "无匹配团队"
    t = plan["teams"][0]
    assert t["dispatch"], "无派工"
    for disp in t["dispatch"]:
        dt = disp["deliverable_template"]
        for key in ("role", "tools", "artifacts", "confidence", "uncertainties"):
            assert key in dt, f"deliverable_template 缺字段 {key}"
