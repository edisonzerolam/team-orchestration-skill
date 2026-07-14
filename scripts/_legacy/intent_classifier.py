#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Intent Classifier — 3-bucket 任务意图分类器

根据任务描述判断意图类型：
  - trivial: 短任务/简单操作，直调通用 agent
  - standard: 需完整流程
  - ambiguous: 范围模糊，需澄清

用法:
  from intent_classifier import classify, clarify
  result = classify("查一下Python文档")
"""
import re

TRIVIAL_SKIP = {"分析", "研究", "写", "设计", "评估", "比较", "开发", "实现"}
AMBIGUOUS_KW = {"优化", "看看", "建议", "你觉得", "调整", "改进", "怎么改"}


def classify(task: str) -> dict:
    """返回 {bucket, reason, clarification}

    bucket: "trivial" | "standard" | "ambiguous"
    reason: 分类理由
    clarification: ambiguous 时返回 ["选项A: ...", "选项B: ..."]
    """
    if not task or not task.strip():
        return {"bucket": "standard", "reason": "空任务，走默认流程"}

    task_lower = task.lower()

    # Ambiguous 优先: 含模糊关键词且无具体对象
    ambiguous_kw_matched = [kw for kw in AMBIGUOUS_KW if kw in task_lower]
    if ambiguous_kw_matched and len(task) < 12:
        questions = _generate_clarification(task)
        return {"bucket": "ambiguous", "reason": f"含模糊关键词 '{ambiguous_kw_matched[0]}'，需澄清",
                "clarification": questions}

    # Trivial: 短任务且无复杂动词
    if len(task) < 15 and not any(kw in task_lower for kw in TRIVIAL_SKIP):
        return {"bucket": "trivial", "reason": f"短任务({len(task)}字)且无复杂动词"}

    return {"bucket": "standard", "reason": "走完整流程"}


def _generate_clarification(task: str) -> list:
    """生成 2 个澄清选项"""
    return [
        f"选项A: 你希望我直接处理 '{task}' 并给出结果？",
        f"选项B: 你希望我先评估 '{task}' 的范围和方案？",
    ]


def clarify(original_task: str, user_choice: str) -> str:
    """用户选择后的任务细化"""
    return f"{original_task}（明确方向：{user_choice}）"
