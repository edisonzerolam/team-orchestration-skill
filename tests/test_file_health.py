# -*- coding: utf-8 -*-
"""全包编码健康扫描（P14 防御项）：UTF-8 strict 解码 + 无 U+FFFD + 无单行超长。
纳入 pytest/run_smoke 收集（文件名 test_* 自动发现）。"""
import glob
import pathlib
import re

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

# C5.2 ? 替字检测（v3.8 · TC-20260816-4）：GBK→UTF-8 误转丢字节的半角 ? 替字
# 判据：中文相邻的半角 ?（汉字紧邻 ? 或 ? 紧邻汉字）= 字尾/标点丢失痕迹。
# 阈值 10（实测校准：46 个损坏文件中文相邻? 28-267；test-workflow/communication 等
# 含检测示例/重建说明的文件最多 4 处，gstack 英文问号前后为英文不匹配——无误报）。
_ZH_Q_RE = re.compile(r"[\u4e00-\u9fff]\?|\?[\u4e00-\u9fff]")
_ZH_Q_THRESHOLD = 10


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


def _zh_adjacent_q_count(text: str) -> int:
    """C5.2：中文相邻半角 ? 计数（? 替字密度，F5 教训 C5 判据②实装）。"""
    return len(_ZH_Q_RE.findall(text))


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
        zh_q = _zh_adjacent_q_count(text)
        if zh_q >= _ZH_Q_THRESHOLD:
            bad.append(f + f" | MOJIBAKE_PLACEHOLDER(中文相邻?x{zh_q})")
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
