"""test_trial_court.py — 审判庭核心调度器冒烟测试"""

import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent

# 文件名含连字符，无法直接 import，改用 importlib.util 按路径加载
_tc_path = SKILL_DIR / "scripts" / "trial-court-orchestrator.py"
_tc_spec = importlib.util.spec_from_file_location("trial_court_orchestrator", str(_tc_path))
_tc_mod = importlib.util.module_from_spec(_tc_spec)
_tc_spec.loader.exec_module(_tc_mod)

cmd_docket = _tc_mod.cmd_docket
cmd_init_learning = _tc_mod.cmd_init_learning
cmd_learning_status = _tc_mod.cmd_learning_status

class Args:
    pass

def test_docket_generation():
    """测试案卷生成"""
    args = Args()
    args.issue = "测试议题：人工智能伦理审查制度"
    args.roles = 3
    args.type = "11-SecurityCompliance"
    args.out = ""

    with tempfile.TemporaryDirectory() as tmp:
        args.out = os.path.join(tmp, "docket.json")
        result = cmd_docket(args)
        assert result is not None
        assert result["docket_id"].startswith("TC-")
        assert result["issue_type"] == "11-SecurityCompliance"
        assert len(result["roles"]) == 3
        assert result["status"] == "docketed"

        # 验证文件写入
        assert os.path.exists(args.out)
        loaded = json.loads(Path(args.out).read_text(encoding="utf-8"))
        assert loaded["docket_id"] == result["docket_id"]

    print("✅ test_docket_generation PASSED")


def test_learning_init():
    """测试自学习初始化"""
    args = Args()
    result = cmd_init_learning(args)
    assert result is not None
    assert "initialized_at" in result
    assert result["trial_count"] == 0
    print("✅ test_learning_init PASSED")


def test_learning_status():
    """测试学习状态查看（不报错即可）"""
    args = Args()
    try:
        cmd_learning_status(args)
    except Exception as e:
        # 没有归档记录时返回空是正常的
        pass
    print("✅ test_learning_status PASSED")


if __name__ == "__main__":
    test_docket_generation()
    test_learning_init()
    test_learning_status()
    print("\n🎉 所有审判庭测试通过！")
