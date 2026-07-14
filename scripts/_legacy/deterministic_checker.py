#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deterministic Checker — 确定性检查清单

不依赖模型，纯确定性规则检查。
支持: Schema校验 / 字段完整性 / 数值边界 / 数据自洽 / 关键词反例 / 结构化断言

用法:
  from deterministic_checker import run_all
  failures = run_all(output_text, task_spec)
"""
import json, re


class SchemaChecker:
    def check(self, output, schema: dict) -> list:
        failures = []
        expected_type_map = {"string": str, "number": (int, float), "list": list, "dict": dict}
        for field, expected in schema.items():
            if field not in output:
                failures.append(f"缺少必填字段: {field}")
                continue
            if expected in expected_type_map:
                if not isinstance(output[field], expected_type_map[expected]):
                    failures.append(f"{field}: 期望 {expected}, 实际 {type(output[field]).__name__}")
        return failures


class FieldChecker:
    def check(self, output, required_fields: list) -> list:
        failures = []
        for field in required_fields:
            val = output.get(field) if isinstance(output, dict) else None
            if val is None or (isinstance(val, str) and not val.strip()):
                failures.append(f"字段 '{field}' 为空或缺失")
        return failures


class BoundaryChecker:
    def check(self, output, rules: list) -> list:
        failures = []
        for rule in rules:
            val = output.get(rule["field"]) if isinstance(output, dict) else None
            if val is None:
                continue
            if val < rule.get("min", float("-inf")):
                failures.append(f"{rule['field']}={val} < 下限 {rule['min']}")
            if val > rule.get("max", float("inf")):
                failures.append(f"{rule['field']}={val} > 上限 {rule['max']}")
        return failures


class KeywordChecker:
    def check(self, text: str, must_include: list = None, must_exclude: list = None) -> list:
        failures = []
        for kw in (must_include or []):
            if kw not in text:
                failures.append(f"缺少必需关键词: {kw}")
        for kw in (must_exclude or []):
            if kw in text:
                failures.append(f"包含禁用词: {kw}")
        return failures


class StructuredAssertionChecker:
    """结构化断言清单 — 覆盖确定性检查的语义缺口 (F9)"""

    def check(self, text: str, assertions: list) -> list:
        failures = []
        for assertion in assertions:
            atype = assertion.get("type", "")
            desc = assertion.get("description", "")
            if atype == "source_citation":
                citations = re.findall(r'(https?://[^\s]+|[\w/]+\.\w{2,4})', text)
                if not citations:
                    failures.append(f"断言失败: {desc} — 未找到来源引用")
            elif atype == "section_exists":
                pattern = assertion.get("pattern", "")
                if pattern and not re.search(pattern, text, re.IGNORECASE):
                    failures.append(f"断言失败: {desc} — 未找到章节 '{pattern}'")
            elif atype == "keywords_present":
                for kw in assertion.get("keywords", []):
                    if kw not in text:
                        failures.append(f"断言失败: {desc} — 缺少关键词 '{kw}'")
            elif atype == "conclusion_consistent":
                sm = re.search(r'摘要[：:]\s*(.*?)(?:。|\n|$)', text)
                cm = re.search(r'结论[：:]\s*(.*?)(?:。|\n|$)', text)
                if sm and cm:
                    for pos, neg in [("利好", "利空"), ("买入", "卖出"), ("增长", "下降")]:
                        if pos in sm.group(1) and neg in cm.group(1):
                            failures.append(f"断言失败: 结论一致性 — 摘要'{pos}'但结论'{neg}'")
        return failures


def run_all(output_text: str, task_spec: dict) -> list:
    """运行全部检查，返回失败列表（统一 list[str]）""" 
    if not isinstance(output_text, str):
        return ["输出非文本格式"]

    failures = []

    # 尝试解析 JSON 输出
    output_data = None
    try:
        output_data = json.loads(output_text)
    except (json.JSONDecodeError, TypeError):
        output_data = None

    schema = task_spec.get("output_schema", {})
    if schema and isinstance(output_data, dict):
        failures.extend(SchemaChecker().check(output_data, schema))

    required = task_spec.get("required_fields", [])
    if required and isinstance(output_data, dict):
        failures.extend(FieldChecker().check(output_data, required))

    boundaries = task_spec.get("boundary_rules", [])
    if boundaries and isinstance(output_data, dict):
        failures.extend(BoundaryChecker().check(output_data, boundaries))

    include = task_spec.get("keywords_must_include", [])
    exclude = task_spec.get("keywords_must_exclude", [])
    if include or exclude:
        failures.extend(KeywordChecker().check(output_text, include, exclude))

    assertions = task_spec.get("structured_assertions", [])
    if assertions:
        failures.extend(StructuredAssertionChecker().check(output_text, assertions))

    return failures
