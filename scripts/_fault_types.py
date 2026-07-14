# -*- coding: utf-8 -*-
"""故障类型共享数据模块

供 self_heal.py 和 failure-analyzer.py 共同引用，消除循环导入风险。
"""
FAULT_TYPES = {
    "FT-01": {"name": "AgentHang",        "severity": 1, "recoverable": True,  "desc": "Agent 僵死"},
    "FT-02": {"name": "ToolFailure",       "severity": 2, "recoverable": True,  "desc": "工具调用失败"},
    "FT-03": {"name": "OutputQuality",     "severity": 2, "recoverable": True,  "desc": "输出质量不合格"},
    "FT-04": {"name": "Hallucination",     "severity": 3, "recoverable": False, "desc": "语义坍缩/幻觉"},
    "FT-05": {"name": "DependencyFail",    "severity": 2, "recoverable": True,  "desc": "依赖 Agent 故障"},
    "FT-06": {"name": "ContextOOM",        "severity": 3, "recoverable": True,  "desc": "上下文预算溢出"},
    "FT-07": {"name": "Degradation",       "severity": 4, "recoverable": False, "desc": "连续退化"},
    "FT-08": {"name": "Deadlock",          "severity": 3, "recoverable": False, "desc": "跨 Agent 死锁"},
    "FT-09": {"name": "DataSourcePoison",  "severity": 4, "recoverable": False, "desc": "数据源污染"},
    "FT-10": {"name": "ConfigError",       "severity": 4, "recoverable": False, "desc": "配置/环境错误"},
    "FT-11": {"name": "ResourceLeak",      "severity": 3, "recoverable": True,  "desc": "资源泄漏（速率限制/连接池耗尽/磁盘满）"},
}

FAULT_CODE_MAP = {
    "FT-01": "ERR-HANG", "FT-02": "ERR-TOOL", "FT-03": "ERR-QUALITY",
    "FT-04": "ERR-HALL", "FT-05": "ERR-DEP", "FT-06": "ERR-CTX",
    "FT-07": "ERR-DEGRADE", "FT-08": "ERR-DEADLOCK",
    "FT-09": "ERR-DATA", "FT-10": "ERR-CONFIG", "FT-11": "ERR-RESOURCE",
}

FAULT_CAUSES = {
    "FT-01": "Agent 长时间无响应（心跳超时）",
    "FT-02": "工具调用失败，退出码或返回异常",
    "FT-03": "输出质量评分低于 0.6，可能为幻觉或不完整",
    "FT-04": "多个信息来源产生矛盾结论，置信度均低于阈值",
    "FT-05": "依赖的上游 Agent 故障或超时",
    "FT-06": "上下文预算接近上限，推理质量可能下降",
    "FT-07": "连续 3 次执行时间或质量下降",
    "FT-08": "多个 Agent 互相等待形成死锁",
    "FT-09": "数据源可能存在污染（与历史经验矛盾）",
    "FT-10": "配置或环境参数异常",
    "FT-11": "资源泄漏（速率限制/连接池耗尽/磁盘满）",
    "FT-UK": "未识别的故障类型",
}

RECOVERY_STRATEGIES = ["retry", "degrade", "rollback", "switch", "circuit_break", "skip", "escalate"]
