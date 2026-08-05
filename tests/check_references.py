# -*- coding: utf-8 -*-
"""tests/check_references.py — team-orchestration 技能引用完整性检查器。

扫描技能目录内所有 .md 文档，解析其中声称为**本地文件**的路径引用
（references/ scripts/ tests/），验证每个引用都能解析到真实存在的文件。

解析基准（多基准，任一命中即视为有效）：
  1. 技能根目录（SKILL.md / README.md 等顶层文档的引用约定）
  2. 引用文档自身的目录
  3. 团队根目录（文档位于 references/workbuddy-experts/<team>/ 时，
     <team>/ 即团队根；团队内部文档惯用 references/X.md 指向团队内文件）

明确排除（非本机文件系统管辖，或属模板/已弃用，不产生误报）：
  - @skills/...                外部技能引用（含 @skills/X/references/Y.md 形式）
  - http(s)://... / mailto:    网络 / 邮件链接
  - 含 < > * 的 token           模板占位符 / glob 示例（如 <团队>/agents/*.md）
  - 含「弃用声明」块的文档       已弃用文档，其内部 OpenCode 残留引用不计入

退出码：
  0 = 所有本地引用解析通过
  1 = 发现无法解析的本地引用（死链 / 缺失文件）
  2 = 运行错误

用法：
  独立运行  python tests/check_references.py
  套件集成  tests/test_references.py 调用 scan() 做断言
"""
import re
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent

# 捕获 references/ scripts/ tests/ 起头的路径 token（不含 @skills，因其锚点为 skills）
_REF_RE = re.compile(r"(?P<lead>@?)(?P<base>references|scripts|tests)(?P<rest>/[^\s`)]*)")

# 非路径字符（含中英文标点），用于清洗捕获到的 token 尾部
_NON_PATH = re.compile(r"[^A-Za-z0-9_./\-一-鿿]+$")

# 外部引用前缀：不在本机文件系统管辖范围
_EXTERNAL_PREFIXES = ("@skills/", "http://", "https://", "mailto:")


def team_root_of(doc_path: Path) -> Path | None:
    """若文档位于 references/workbuddy-experts/<team>/ 下，返回 <team>/ 绝对路径。

    注意：Windows 下 Path 字符串化使用反斜杠，需先归一为正斜杠再匹配。
    """
    p = str(doc_path).replace("\\", "/")
    m = re.search(r"references/workbuddy-experts/([^/]+)", p)
    if m:
        return SKILL_ROOT / "references" / "workbuddy-experts" / m.group(1)
    return None


def resolve(token: str, doc_path: Path) -> Path | None:
    """按多基准尝试解析 token，命中返回绝对路径，否则返回 None。"""
    bases = [SKILL_ROOT, doc_path.parent]
    tr = team_root_of(doc_path)
    if tr is not None:
        bases.append(tr)
    for base in bases:
        cand = base / token
        if cand.exists():
            return cand
    return None


def scan():
    """扫描全部本地 .md，返回 (scanned_files, refs_found, broken_list)。

    broken_list 元素为 (doc_relative, token) 元组。
    """
    broken = []
    scanned_files = 0
    refs_found = 0

    for md in sorted(SKILL_ROOT.rglob("*.md")):
        # 跳过备份副本（与技能同级的 *.backup-* 目录）
        if any(".backup" in part for part in md.parts):
            continue
        text = md.read_text(encoding="utf-8-sig")
        # 跳过已弃用文档（含弃用声明块），其内部 OpenCode 残留引用不计入
        if "弃用声明" in text or "**已弃用**" in text:
            continue
        scanned_files += 1
        for m in _REF_RE.finditer(text):
            lead = m.group("lead")
            token = m.group("base") + m.group("rest")
            token = _NON_PATH.sub("", token).rstrip("-")  # 清洗尾部中英文标点与连字符
            if not token:
                continue
            # 外部引用（@skills/...）直接跳过
            if lead == "@" and token.startswith("skills/"):
                continue
            if token.startswith(_EXTERNAL_PREFIXES):
                continue
            # 模板占位符 / glob 示例（如 <团队>/agents/*.md）跳过
            if "<" in token or ">" in token or "*" in token:
                continue
            # @skills 上下文内的 references/...（如 `@skills/X/references/Y.md`）
            line_start = text.rfind("\n", 0, m.start()) + 1
            pre = text[line_start : m.start()]
            if "@skills" in pre:
                continue
            # 指向其他技能市场/绝对路径的引用（如
            # ~/.workbuddy/skills-marketplace/skills/neodata-financial-search/scripts/query.py）
            # 其 scripts/... 只是尾部，应视为外部技能引用，跳过。
            if "skills-marketplace" in pre:
                continue
            # 含模板变量（如 {SKILL_DIR}），运行时才解析，静态无法校验，跳过。
            if "{" in pre or "{" in token or "}" in token:
                continue
            refs_found += 1
            if resolve(token, md) is None:
                broken.append((str(md.relative_to(SKILL_ROOT)), token))

    return scanned_files, refs_found, broken


def main():
    try:
        scanned_files, refs_found, broken = scan()
    except Exception as e:  # noqa: BLE001
        print(f"RUN-ERROR: {e}")
        sys.exit(2)

    print(f"扫描 {scanned_files} 个 .md 文件，发现 {refs_found} 条本地引用。")
    if broken:
        print(f"\n❌ 发现 {len(broken)} 条无法解析的本地引用（死链/缺失文件）：")
        for doc, tok in broken:
            print(f"  - {doc}: {tok}")
        sys.exit(1)
    print("✅ 所有本地引用均可解析。")
    sys.exit(0)


if __name__ == "__main__":
    main()
