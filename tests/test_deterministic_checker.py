"""测试 deterministic_checker.py — 确定性检查清单"""
import pytest
from pathlib import Path
import importlib.util

spec = importlib.util.spec_from_file_location("dc",
    str(Path.home() / ".config" / "opencode" / "skills" / "team-orchestration" / "scripts" / "deterministic_checker.py"))
dc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dc)


class TestSchemaChecker:
    def test_missing_field(self):
        f = dc.SchemaChecker().check({}, {"name": "string"})
        assert len(f) == 1
        assert "name" in f[0]

    def test_type_mismatch(self):
        f = dc.SchemaChecker().check({"count": "abc"}, {"count": "number"})
        assert len(f) == 1

    def test_valid(self):
        f = dc.SchemaChecker().check({"name": "test"}, {"name": "string"})
        assert len(f) == 0


class TestFieldChecker:
    def test_empty_field(self):
        f = dc.FieldChecker().check({"x": ""}, ["x"])
        assert len(f) == 1

    def test_valid_field(self):
        f = dc.FieldChecker().check({"x": "value"}, ["x"])
        assert len(f) == 0


class TestBoundaryChecker:
    def test_below_min(self):
        f = dc.BoundaryChecker().check({"v": 0}, [{"field": "v", "min": 1}])
        assert len(f) == 1

    def test_above_max(self):
        f = dc.BoundaryChecker().check({"v": 100}, [{"field": "v", "max": 50}])
        assert len(f) == 1

    def test_valid(self):
        f = dc.BoundaryChecker().check({"v": 25}, [{"field": "v", "min": 1, "max": 50}])
        assert len(f) == 0


class TestKeywordChecker:
    def test_missing_keyword(self):
        f = dc.KeywordChecker().check("hello", must_include=["world"])
        assert len(f) == 1

    def test_contains_excluded(self):
        f = dc.KeywordChecker().check("bad word here", must_exclude=["bad"])
        assert len(f) == 1


class TestStructuredAssertions:
    def test_source_citation_found(self):
        text = "数据来源: https://example.com/data"
        f = dc.StructuredAssertionChecker().check(text, [{"type": "source_citation", "description": "需标注来源"}])
        assert len(f) == 0

    def test_source_citation_missing(self):
        text = "这个数据来自我的分析"
        f = dc.StructuredAssertionChecker().check(text, [{"type": "source_citation", "description": "需标注来源"}])
        assert len(f) == 1

    def test_section_exists(self):
        text = "## 结论\n最终结果..."
        f = dc.StructuredAssertionChecker().check(text, [{"type": "section_exists", "pattern": "## 结论"}])
        assert len(f) == 0

    def test_section_missing(self):
        text = "## 分析\n内容..."
        f = dc.StructuredAssertionChecker().check(text, [{"type": "section_exists", "pattern": "## 结论"}])
        assert len(f) == 1

    def test_conclusion_consistent(self):
        text = "摘要：市场表现利好。结论：建议利空操作。"
        f = dc.StructuredAssertionChecker().check(text, [{"type": "conclusion_consistent", "description": "一致性"}])
        assert len(f) == 1

    def test_keywords_present(self):
        f = dc.StructuredAssertionChecker().check("报告内容", [{"type": "keywords_present", "keywords": ["风险提示"]}])
        assert len(f) == 1


class TestRunAll:
    def test_invalid_input(self):
        f = dc.run_all(123, {})  # 非文本
        assert len(f) >= 1

    def test_empty_text(self):
        f = dc.run_all("", {})
        assert len(f) == 0

    def test_with_all_checks(self):
        text = "摘要：增长。结论：增长。数据: https://x.com\n## 结果"
        spec = {
            "keywords_must_include": ["数据"],
            "keywords_must_exclude": ["错误"],
            "structured_assertions": [
                {"type": "source_citation", "description": "来源"},
                {"type": "section_exists", "pattern": "## 结果"},
                {"type": "conclusion_consistent", "description": "一致性"},
            ],
        }
        f = dc.run_all(text, spec)
        assert len(f) == 0
