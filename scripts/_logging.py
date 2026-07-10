#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Structured logging + metrics + trace_id for Team Orchestration

Usage:
  from _logging import get_logger, MetricsRegistry, setup_metrics

  logger = get_logger("orchestrator", trace_id="abc123")
  logger.info("task_started", task="分析茅台", phase=1)

  metrics = setup_metrics()
  metrics.inc("task.completed")
  metrics.record("duration_ms", 1234, tags={"task_type": "research"})
"""
import json, logging, time, uuid, os
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timezone

_metrics_registry = None
_loggers = {}


class JsonFormatter(logging.Formatter):
    def format(self, record):
        extra = getattr(record, "extra", {})
        return json.dumps({
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "module": record.module or "",
            "line": record.lineno or 0,
            **extra,
        }, ensure_ascii=False)


def get_logger(name: str, trace_id: str = "", level=logging.INFO):
    key = f"{name}.{trace_id}"
    if key in _loggers:
        return _loggers[key]

    logger = logging.getLogger(key)
    logger.setLevel(level)
    logger.handlers.clear()

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)

    logger.trace_id = trace_id or _gen_trace_id()
    _loggers[key] = logger
    return logger


def _gen_trace_id() -> str:
    return uuid.uuid4().hex[:8]


class MetricsRegistry:
    """Minimal JSON-lines metrics, zero dependencies"""

    def __init__(self, path: str = ""):
        self.path = Path(path or os.environ.get(
            "TO_METRICS_PATH",
            str(Path.home() / ".opencode" / "metrics" / "team-orchestration.jsonl"),
        ))
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.counters = defaultdict(int)
        self.histograms = defaultdict(list)
        self._start = time.time()

    def inc(self, name: str, delta: int = 1, tags: dict = None):
        self.counters[(name, _tag_key(tags))] += delta

    def record(self, name: str, value: float, tags: dict = None):
        self.histograms[(name, _tag_key(tags))].append(value)

    def flush(self):
        records = []
        for (name, tkey), count in self.counters.items():
            records.append({"metric": name, "type": "counter",
                           "value": count, "tags": _tag_value(tkey)})
        for (name, tkey), values in self.histograms.items():
            if values:
                records.append({"metric": name, "type": "histogram",
                               "value": sum(values)/len(values),
                               "count": len(values),
                               "min": min(values), "max": max(values),
                               "tags": _tag_value(tkey)})
        records.append({"metric": "uptime_s", "type": "gauge",
                       "value": int(time.time() - self._start)})
        self.path.write_text(
            "\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n",
            encoding="utf-8",
        )


def _tag_key(tags: dict = None) -> str:
    return json.dumps(tags or {}, sort_keys=True)


def _tag_value(key: str) -> dict:
    try:
        return json.loads(key)
    except: return {}


def setup_metrics(path: str = "") -> MetricsRegistry:
    global _metrics_registry
    if _metrics_registry is None:
        _metrics_registry = MetricsRegistry(path)
    return _metrics_registry


def get_metrics() -> MetricsRegistry | None:
    return _metrics_registry
