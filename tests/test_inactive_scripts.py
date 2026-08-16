# -*- coding: utf-8 -*-
"""tests/test_inactive_scripts.py — 未激活脚本资产冒烟测试（P0-3 脚本激活 / P1-1 effort 预算 / P0-4 断点续传）。

覆盖方案 P0-3 / P0-4 / P1-1 / P2-1 的脚本侧落点：
  1. 5 个未激活/未索引脚本存在性 + 最小只读调用可运行：
     token_budget.py / checkpoint_manager.py / cycle_detector.py / self_heal.py / auto-decider.py
  2. token_budget.py L1-L4 effort 档位预设与 warn/block 行为（P1-1）
  3. orchestrator docket 产物含 resume_from + token_budget 字段；resume-status 断点续传输出
     （P0-4/P2-1，旧案卷无 resume_from 时向后兼容）
  4. orchestrator check-cycle 接线 cycle_detector（P0-3）

本文件独立于 run_smoke.py（纯遍历器，保持不动），按 run_smoke 约定提供 test_* 函数。
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPTS = SKILL_DIR / "scripts"

# ── 被点名的未激活/未索引脚本 ─────────────────────────────────
INACTIVE_SCRIPTS = [
    "token_budget.py",
    "checkpoint_manager.py",
    "cycle_detector.py",
    "self_heal.py",
    "auto-decider.py",
]


def _py(*args):
    """运行 python <args>，返回 CompletedProcess。

    编码健壮性（v3.8 · TC-20260816-3）：子进程强制 UTF-8 输出
    （PYTHONIOENCODING，防 GBK locale 下输出 GBK 字节致父进程 utf-8 解码失败、
    stdout 变 None）；errors="replace" 兜底（与 test_dispatch_planner 一致，
    防极端环境解码崩溃而非断言失败）。
    """
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    return subprocess.run([sys.executable, *args], capture_output=True,
                          text=True, encoding="utf-8", errors="replace", env=env)


def _load_module(name, relpath):
    spec = importlib.util.spec_from_file_location(name, str(SCRIPTS / relpath))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_orchestrator():
    return _load_module("trial_court_orchestrator_mod", "trial-court-orchestrator.py")


class _Args:
    pass


# ── 1. 存在性 + 最小只读调用 ─────────────────────────────────

def test_inactive_scripts_exist_and_helpable():
    """5 个未激活脚本存在，且 --help 只读调用 exit 0。"""
    for name in INACTIVE_SCRIPTS:
        p = SCRIPTS / name
        assert p.exists(), f"脚本缺失: {p}"
        r = _py(str(p), "--help")
        assert r.returncode == 0, f"{name} --help 退出码={r.returncode}: {r.stderr}"
        assert "usage" in r.stdout.lower(), f"{name} --help 无 usage 输出"
    print("✅ 未激活脚本存在且 --help 可运行")


def test_inactive_scripts_importable():
    """5 个未激活脚本可被 import（模块级无执行副作用）。"""
    for name in INACTIVE_SCRIPTS:
        _load_module(name.replace(".py", "_mod").replace("-", "_"), name)
    print("✅ 未激活脚本可 import")


# ── 2. token_budget effort 档位（P1-1） ──────────────────────

def test_token_budget_effort_tiers():
    """L1-L4 档位预设：token_cap 递增、sub_agents 递增、六阶段 limits 齐全。"""
    tb = _load_module("token_budget_mod", "token_budget.py")
    caps = {eff: tb.effort_limits(eff) for eff in ("L1", "L2", "L3", "L4")}
    assert caps["L1"]["token_cap"] < caps["L2"]["token_cap"] < \
        caps["L3"]["token_cap"] < caps["L4"]["token_cap"]
    assert caps["L1"]["sub_agents"] < caps["L4"]["sub_agents"]
    for eff, rec in caps.items():
        assert len(rec["limits"]) == 6, f"{eff} 应含二审终审制六阶段预算"
        assert all(rec["limits"][p] == rec["token_cap"] for p in rec["limits"])
    print("✅ token_budget L1-L4 effort 档位预设")


def test_token_budget_warn_block():
    """80% 预警 / 100% 阻断行为（P0-3）：超限未 override 时 blocked=True 且退出码 2。"""
    tb = _load_module("token_budget_mod", "token_budget.py")
    b = tb.TokenBudget({"质证": 1000})
    w = b.consume("质证", 850)
    assert w["status"] == "warn", f"85% 应为 warn，实际 {w['status']}"
    assert w["blocked"] is False
    e = b.consume("质证", 200)
    assert e["status"] == "exceeded"
    assert e["blocked"] is True
    o = b.consume("质证", 1, override=True)
    assert o["blocked"] is False
    print("✅ token_budget warn/block 行为")


def test_token_budget_effort_cli():
    """CLI：--effort 预设输出档位信息；超限时退出码 2。"""
    r = _py(str(SCRIPTS / "token_budget.py"), "--effort", "L3")
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out["effort"]["effort"] == "L3"
    assert out["effort"]["token_cap"] == 16000

    r = _py(str(SCRIPTS / "token_budget.py"), "--effort", "L2",
            "--consume", json.dumps(["举证", 9000]))
    assert r.returncode == 2, f"超 L2 预算应退出码 2，实际 {r.returncode}: {r.stdout}"
    print("✅ token_budget --effort CLI")


# ── 3. orchestrator docket + resume（P0-3/P0-4/P2-1） ────────

def test_orchestrator_docket_has_resume_and_budget():
    """docket 产物含 resume_from + token_budget 字段（断点续传 metadata + 阶段预算）。"""
    tc = _load_orchestrator()
    with tempfile.TemporaryDirectory() as tmp:
        a = _Args()
        a.issue = "测试议题：resume 字段"
        a.roles = 3
        a.type = "08-FinanceInvestment"
        a.out = os.path.join(tmp, "docket.json")
        a.max_rounds = 2
        rec = tc.cmd_docket(a)
        assert rec["resume_from"] == "00-立案", f"resume_from 应为 00-立案，实际 {rec['resume_from']}"
        assert rec["token_budget"]["effort"] == "L3"
        assert rec["token_budget"]["limits"]["质证"] == 16000
        assert "limits" in rec["token_budget"]
    print("✅ orchestrator docket 含 resume_from + token_budget")


def test_orchestrator_resume_status():
    """resume-status 输出可恢复状态（next_phase 推导 + 检查点目录读取）。"""
    tc = _load_orchestrator()
    with tempfile.TemporaryDirectory() as tmp:
        # 造案卷：假设已完成质证（02-质证）
        a = _Args()
        a.issue = "测试议题：断点续传"
        a.roles = 3
        a.type = "11-SecurityCompliance"
        a.out = os.path.join(tmp, "docket.json")
        a.max_rounds = 2
        tc.cmd_docket(a)
        d = json.loads(Path(a.out).read_text(encoding="utf-8"))
        d["resume_from"] = "02-质证"
        Path(a.out).write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")

        ck_root = os.path.join(tmp, "ckpt")
        r = _py(str(SCRIPTS / "trial-court-orchestrator.py"), "resume-status",
                "--docket", a.out, "--checkpoint-root", ck_root)
        assert r.returncode == 0, r.stderr
        out = json.loads(r.stdout)
        assert out["resume_from"] == "02-质证"
        assert out["next_phase"] == "03-一审"
        assert out["checkpoint"]["next"] == "00-立案"  # 无检查点记录时从首阶段起
    print("✅ orchestrator resume-status 断点续传状态")


def test_orchestrator_resume_backward_compat():
    """旧案卷无 resume_from 字段时不报错，按 00-立案 兜底（向后兼容）。"""
    tc = _load_orchestrator()
    with tempfile.TemporaryDirectory() as tmp:
        a = _Args()
        a.issue = "测试议题：旧案卷兼容"
        a.roles = 3
        a.type = "11-SecurityCompliance"
        a.out = os.path.join(tmp, "docket.json")
        a.max_rounds = 2
        rec = tc.cmd_docket(a)
        rec.pop("resume_from", None)
        Path(a.out).write_text(json.dumps(rec, ensure_ascii=False, indent=2), encoding="utf-8")

        r = _py(str(SCRIPTS / "trial-court-orchestrator.py"), "resume-status",
                "--docket", a.out)
        assert r.returncode == 0, r.stderr
        out = json.loads(r.stdout)
        assert out["resume_from"] == "00-立案"
        assert out["next_phase"] == "01-举证"
    print("✅ orchestrator resume-status 向后兼容")


# ── 4. orchestrator check-cycle 接线（P0-3） ─────────────────

def test_orchestrator_check_cycle():
    """check-cycle 接线 cycle_detector：成环退出码 1 且报环，无环退出码 0。"""
    with tempfile.TemporaryDirectory() as tmp:
        cyc = os.path.join(tmp, "cycle.json")
        acy = os.path.join(tmp, "acyclic.json")
        Path(cyc).write_text(json.dumps([["A", "B"], ["B", "A"]]), encoding="utf-8")
        Path(acy).write_text(json.dumps([["A", "B"], ["B", "C"]]), encoding="utf-8")

        r = _py(str(SCRIPTS / "trial-court-orchestrator.py"), "check-cycle", "--edges", cyc)
        assert r.returncode == 1, f"成环应退出码 1，实际 {r.returncode}: {r.stdout}"
        assert "CYCLE DETECTED" in r.stdout

        r = _py(str(SCRIPTS / "trial-court-orchestrator.py"), "check-cycle", "--edges", acy)
        assert r.returncode == 0, f"无环应退出码 0，实际 {r.returncode}: {r.stdout}"
        assert "NO CYCLE" in r.stdout
    print("✅ orchestrator check-cycle 接线")


# ── 5. self_heal / auto-decider 最小调用（P0-3） ─────────────

def test_self_heal_cli():
    """self_heal.py 最小输入可运行：错误分类输出 error_type。"""
    r = _py(str(SCRIPTS / "self_heal.py"), "--error-message", "connection refused")
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out["error_type"] == "network"
    print("✅ self_heal 最小调用")


def test_auto_decider_cli():
    """auto-decider.py 最小输入可运行：自动决策输出 action。"""
    r = _py(str(SCRIPTS / "auto-decider.py"), "--error-message", "file not found")
    assert r.returncode == 0, r.stderr
    out = json.loads(r.stdout)
    assert out["action"] in ("retry", "skip", "abort")
    print("✅ auto-decider 最小调用")


if __name__ == "__main__":
    test_inactive_scripts_exist_and_helpable()
    test_inactive_scripts_importable()
    test_token_budget_effort_tiers()
    test_token_budget_warn_block()
    test_token_budget_effort_cli()
    test_orchestrator_docket_has_resume_and_budget()
    test_orchestrator_resume_status()
    test_orchestrator_resume_backward_compat()
    test_orchestrator_check_cycle()
    test_self_heal_cli()
    test_auto_decider_cli()
    print("\n🎉 所有未激活脚本冒烟测试通过！")
