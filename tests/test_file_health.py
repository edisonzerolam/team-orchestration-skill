# -*- coding: utf-8 -*-
"""全包编码健康扫描（P14 防御项）：UTF-8 strict 解码 + 无 U+FFFD + 无单行超长。
纳入 pytest/run_smoke 收集（文件名 test_* 自动发现）。"""
import glob
import pathlib

SKILL_DIR = pathlib.Path(__file__).resolve().parent.parent
NL = chr(10)


# 运行态产物（与 .gitignore 一致）：不参与源文件健康扫描
_RUNTIME_PATTERNS = (
    "scripts/output/",
    "references/last-asset-snapshot.json",
    "references/asset-issue-map.md",
    "references/learning-data/docket-",
    "references/learning-data/trial-count.json",
    "references/learning-data/learning-init.json",
    "references/learning-data/expert_scores.json",
)


def _is_runtime(f: str) -> bool:
    rel = f.replace("\\", "/")
    return any(pat in rel for pat in _RUNTIME_PATTERNS)


# 常见汉字集合：用于 mojibake 检测（正常中文必含高频字，乱码文本几乎不含）
_COMMON_HAN = "的是一不了有就人在和中与我为对之等我们你他这那"


def _is_mojibake(text: str) -> bool:
    """检测 GB18030/UTF-8 双编码错位乱码（UTF-8 字节被按 GB18030/GBK 解码）：
    判据：GB18030 roundtrip（无损可逆）还原原始 UTF-8 字节后常见汉字命中显著增多。
    GB18030 覆盖全部 Unicode 且完全可逆，能捕获任何形态的编码错位乱码。"""
    if len(text) < 50:
        return False
    try:
        restored = text.encode("gb18030").decode("utf-8", errors="ignore")
    except Exception:
        return False
    if restored == text:
        return False
    orig_hits = sum(1 for ch in _COMMON_HAN if ch in text)
    rest_hits = sum(1 for ch in _COMMON_HAN if ch in restored)
    return (rest_hits - orig_hits) >= 3


def _scan() -> list:
    files = (glob.glob(str(SKILL_DIR / "**" / "*.md"), recursive=True)
             + glob.glob(str(SKILL_DIR / "**" / "*.py"), recursive=True)
             + glob.glob(str(SKILL_DIR / "**" / "*.json"), recursive=True))
    bad = []
    for f in files:
        if _is_runtime(f):
            continue
        raw = open(f, "rb").read()
        try:
            text = raw.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            bad.append(f + " | DECODE_ERR")
            continue
        if chr(0xFFFD) in text:
            bad.append(f + " | U+FFFD")
        if len(text.splitlines()) == 1 and len(text) > 500:
            bad.append(f + " | SINGLE_LINE_LONG")
        if _is_mojibake(text):
            bad.append(f + " | MOJIBAKE")
    return bad


def test_all_files_utf8_healthy():
    bad = _scan()
    assert not bad, NL.join(bad[:50])


if __name__ == "__main__":
    bad = _scan()
    total = len(glob.glob(str(SKILL_DIR / "**" / "*.md"), recursive=True)) + len(
        glob.glob(str(SKILL_DIR / "**" / "*.py"), recursive=True)) + len(
        glob.glob(str(SKILL_DIR / "**" / "*.json"), recursive=True))
    if bad:
        print("FAIL:", NL.join(bad[:50]))
        raise SystemExit(1)
    print("PASS: 全包 UTF-8 健康，扫描 " + str(total) + " 个文件")
