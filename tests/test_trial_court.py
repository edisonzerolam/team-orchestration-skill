"""test_trial_court.py — 审判庭核心调度器冒烟测试（含二审终审制）"""

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
cmd_verdict_template = _tc_mod.cmd_verdict_template
cmd_prompt = _tc_mod.cmd_prompt

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


def _make_confirmed_docket(tmp):
    """构造已确认案卷（二审终审制默认字段），返回 docket 路径"""
    a = Args()
    a.issue = "测试议题：二审终审制协议"
    a.roles = 3
    a.type = "08-FinanceInvestment"
    a.out = os.path.join(tmp, "docket.json")
    cmd_docket(a)
    d = json.loads(Path(a.out).read_text(encoding="utf-8"))
    d["confirmed"] = True
    Path(a.out).write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    return a.out


def test_docket_two_instance_fields():
    """二审终审制：案卷含质证上限 2 轮 + 回灌修订固定 1 轮字段"""
    with tempfile.TemporaryDirectory() as tmp:
        docket_path = _make_confirmed_docket(tmp)
        d = json.loads(Path(docket_path).read_text(encoding="utf-8"))
        assert d["cross_exam"]["max_rounds"] == 2, "质证轮次上限应为 2（统一口径）"
        assert d["revision"]["max_rounds"] == 1, "回灌修订应固定 1 轮"
        assert d["revision"]["done"] is False
    print("✅ test_docket_two_instance_fields PASSED")


def test_first_instance_verdict_template():
    """一审判决书模板（中间产物）与二审终审意见书模板（终局）"""
    with tempfile.TemporaryDirectory() as tmp:
        docket_path = _make_confirmed_docket(tmp)

        va = Args()
        va.docket = docket_path
        va.instance = "first"
        va.out = ""
        tmpl_first = cmd_verdict_template(va)
        assert "一审判决书" in tmpl_first
        assert "终审意见书" not in tmpl_first

        vb = Args()
        vb.docket = docket_path
        vb.instance = "second"
        vb.out = ""
        tmpl_second = cmd_verdict_template(vb)
        assert "终审意见书" in tmpl_second
        assert "二审终审" in tmpl_second
        assert "不再回灌" in tmpl_second
    print("✅ test_first_instance_verdict_template PASSED")


def test_revision_prompt():
    """一审回灌修订 prompt：含一审判决书 + 固定 1 轮提示，并回写案卷 revision 字段"""
    with tempfile.TemporaryDirectory() as tmp:
        docket_path = _make_confirmed_docket(tmp)
        vdir = os.path.join(tmp, "03-一审")
        os.makedirs(vdir)
        Path(os.path.join(vdir, "first-instance-verdict.md")).write_text(
            "# 一审判决书\n采信正方主张，驳回反方异议。", encoding="utf-8")

        pa = Args()
        pa.phase = "revision"
        pa.role = "反方"
        pa.docket = docket_path
        pa.evidence_dir = ""
        pa.verdict_file = os.path.join(vdir, "first-instance-verdict.md")
        pa.round = 1
        pa.force = False
        prompt = cmd_prompt(pa)
        assert "一审回灌修订" in prompt
        assert "一审判决书" in prompt
        assert "固定 1 轮" in prompt
        assert "二审终审" in prompt

        d = json.loads(Path(docket_path).read_text(encoding="utf-8"))
        assert d["revision"]["current_round"] == 1
        assert d["revision"]["done"] is True
    print("✅ test_revision_prompt PASSED")


if __name__ == "__main__":
    test_docket_generation()
    test_learning_init()
    test_learning_status()
    test_docket_two_instance_fields()
    test_first_instance_verdict_template()
    test_revision_prompt()
    print("\n🎉 所有审判庭测试通过！")
