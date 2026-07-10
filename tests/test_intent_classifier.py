"""测试 intent_classifier.py — 3-bucket 意图分类"""
import pytest
from pathlib import Path
import importlib.util

spec = importlib.util.spec_from_file_location("ic",
    str(Path.home() / ".config" / "opencode" / "skills" / "team-orchestration" / "scripts" / "intent_classifier.py"))
ic = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ic)


class TestTrivial:
    @pytest.mark.parametrize("task", [
        "查一下Python文档", "删除文件test.sh", "改第3行变量名",
        "重命名函数", "打开配置文件",
    ])
    def test_trivial(self, task):
        r = ic.classify(task)
        assert r["bucket"] == "trivial", f"{task} → {r}"

    def test_trivial_false_positive(self):
        r = ic.classify("分析股票")
        assert r["bucket"] != "trivial"  # 含分析关键词


class TestStandard:
    @pytest.mark.parametrize("task", [
        "分析腾讯股票的财务数据",
        "写一篇AI行业分析报告",
        "开发一个登录页面",
        "评估这个项目的技术方案",
        "比较React和Vue的异同",
    ])
    def test_standard(self, task):
        r = ic.classify(task)
        assert r["bucket"] == "standard", f"{task} → {r}"


class TestAmbiguous:
    @pytest.mark.parametrize("task", [
        "优化一下代码", "看看这个app的设计",
        "你觉得怎么改比较好", "建议一下改进方向",
    ])
    def test_ambiguous(self, task):
        r = ic.classify(task)
        assert r["bucket"] == "ambiguous", f"{task} → {r}"
        assert "clarification" in r and len(r["clarification"]) >= 2

    def test_ambiguous_false_positive(self):
        r = ic.classify("写一篇关于AI优化的深度研究报告")
        assert r["bucket"] != "ambiguous"  # 长文本不触发


class TestEdge:
    def test_empty(self):
        r = ic.classify("")
        assert r["bucket"] == "standard"

    def test_whitespace(self):
        r = ic.classify("   ")
        assert r["bucket"] == "standard"

    def test_clarify(self):
        r = ic.clarify("优化一下", "优化数据库查询")
        assert "优化数据库查询" in r
