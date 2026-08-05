"""tests/run_smoke.py — 无 pytest 环境下的冒烟测试运行器。
遍历本目录下所有 test_*.py，逐个执行 test_* 函数，输出 PASS/FAIL 并汇总。
用法：python tests/run_smoke.py
"""
import importlib.util
import sys
from pathlib import Path

TESTS = Path(__file__).resolve().parent


def main():
    ok = fail = 0
    for f in sorted(TESTS.glob("test_*.py")):
        try:
            spec = importlib.util.spec_from_file_location(f.stem, str(f))
            m = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(m)
        except Exception as e:
            print(f"LOAD-FAIL {f.stem}: {e}")
            fail += 1
            continue
        for name in dir(m):
            if name.startswith("test_") and callable(getattr(m, name)):
                try:
                    getattr(m, name)()
                    print(f"PASS {f.stem}.{name}")
                    ok += 1
                except Exception as e:
                    print(f"FAIL {f.stem}.{name}: {e}")
                    fail += 1
    print(f"\n{ok} passed, {fail} failed")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
