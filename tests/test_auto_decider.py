"""测试 auto-decider.py — 自动化错误决策引擎"""
import pytest
import importlib.util
import sys
from pathlib import Path

SCRIPTS_DIR = Path.home() / ".config" / "opencode" / "skills" / "team-orchestration" / "scripts"
spec = importlib.util.spec_from_file_location("auto_decider", str(SCRIPTS_DIR / "auto-decider.py"))
ad = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ad)


class TestErrorClassification:
    @pytest.mark.parametrize("error_msg,expected_type", [
        ("timeout: 连接超时", "timeout"),
        ("timed out after 30s", "timeout"),
        ("HTTP 529 Server overloaded", "rate_limited"),
        ("too many requests, please slow down", "rate_limited"),
        ("服务器过载", "rate_limited"),
        ("SyntaxError: invalid syntax", "syntax_error"),
        ("IndentationError: unexpected indent", "syntax_error"),
        ("FileNotFoundError: no such file", "file_not_found"),
        ("Cannot find path", "file_not_found"),
        ("model not found: zen/mimo-v2.5-free", "model_not_found"),
        ("unknown agent type: researcher-ds", "model_not_found"),
        ("Insufficient balance", "insufficient_balance"),
        ("quota exhausted for today", "insufficient_balance"),
        ("Permission denied", "permission_denied"),
        ("EACCES: access denied", "permission_denied"),
        ("some random unknown error 42", "unknown"),
    ])
    def test_classification(self, error_msg, expected_type):
        assert ad.classify_error(error_msg) == expected_type

    def test_empty_string(self):
        assert ad.classify_error("") == "unknown"

    def test_none(self):
        assert ad.classify_error(None) == "unknown"


class TestDecide:
    def test_retry_on_timeout(self):
        dec = ad.decide("auto", "timeout: connection lost")
        assert dec["action"] == "retry"

    def test_abort_on_syntax_error(self):
        dec = ad.decide("auto", "SyntaxError: bad syntax")
        assert dec["action"] == "abort"

    def test_skip_on_file_not_found(self):
        dec = ad.decide("auto", "FileNotFoundError: missing.txt")
        assert dec["action"] == "skip"

    def test_abort_after_max_retries(self):
        dec = ad.decide("timeout", "timeout", retry_count=3)
        assert dec["action"] == "abort"

    def test_retry_under_max_retries(self):
        dec = ad.decide("timeout", "timeout", retry_count=1)
        assert dec["action"] == "retry"

    def test_unknown_default_skip(self):
        dec = ad.decide("auto", "weird cryptic error #999")
        assert dec["action"] == "skip"

    def test_new_timeout_added_on_retry(self):
        dec = ad.decide("auto", "timeout: connection lost")
        if dec["action"] == "retry":
            assert "new_timeout" in dec
            assert dec["new_timeout"] is not None

    def test_error_type_in_result(self):
        dec = ad.decide("auto", "timeout: connection lost")
        assert "error_type" in dec

    def test_retry_count_in_result(self):
        dec = ad.decide("auto", "timeout", retry_count=2)
        assert dec["retry_count"] == 2


class TestRateLimited:
    def test_rate_limited_patterns(self):
        patterns = [
            "429 Too Many Requests",
            "529 The server cluster is under high load",
            "rate limit exceeded",
            "too many requests",
            "请稍后重试",
        ]
        for msg in patterns:
            assert ad.classify_error(msg) == "rate_limited", f"Failed for: {msg}"

    def test_rate_limited_decides_retry(self):
        dec = ad.decide("auto", "HTTP 529 high load")
        assert dec["action"] == "retry"
        assert dec["error_type"] == "rate_limited"


class TestFallbackChain:
    def test_auto_mode_fallback(self):
        dec = ad.decide("auto", "weird error that matches nothing")
        assert dec["action"] in ("skip", "abort")

    def test_unknown_type_uses_unknown_rule(self):
        dec = ad.decide("nonexistent_type", "some error")
        assert dec["action"] == "skip"
