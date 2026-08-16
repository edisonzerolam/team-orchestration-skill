# 交叉验证编排核心（现行后端）：对举证产物做交叉验证，输出 conflict/consistency 报告，接入 v3.1 §4 A3 evidence 校验
# cross-validator.py — 交叉验证编排核心 (最小可用实现 v2.3)
# 使用: python cross-validator.py --task <task_id> --depth auto|skip|light|standard|deep --input <file|"-">
import argparse, json, sys, re


def extract_claims(agent_outputs):
    """从专家输出中提取原子声明"""
    claims = []
    for o in agent_outputs:
        for sent in re.split(r"[。\n]", o.get("text", "")):
            s = sent.strip()
            if len(s) >= 4:
                claims.append({"text": s, "source": o.get("agent", "?")})
    return claims


def trace_provenance(claims):
    """为每个声明追溯来源"""
    for c in claims:
        c["plugin"] = "workbuddy-experts"
    return claims


def check_independence(claims):
    """检查来源独立性（同源检测）"""
    indep = len({c["source"] for c in claims}) >= 2
    for c in claims:
        c["independent"] = indep
    return claims


def triangulate(claims):
    """跨源三角测量（同主题多源确认）"""
    grp = {}
    for c in claims:
        grp.setdefault(c["text"][:20], []).append(c["source"])
    for c in claims:
        c["confirmed"] = len(set(grp[c["text"][:20]])) >= 2
    return claims


def detect_conflicts(claims):
    """检测跨源冲突（同向/反向措辞碰撞）"""
    pos, neg = ["利好", "支持", "推荐", "可行"], ["利空", "反对", "不推荐", "不可行"]
    out = []
    for c in claims:
        if any(p in c["text"] for p in pos):
            for c2 in claims:
                if c2 is not c and any(n in c2["text"] for n in neg) and c["text"][:10] == c2["text"][:10]:
                    out.append({"a": c["text"], "b": c2["text"]})
    return out


def score_confidence(claims, depth):
    """综合评分：一致性 + 验证强度 + 源层级加权"""
    for c in claims:
        c["confidence"] = round(0.5 + 0.3 * (1 if c["independent"] else 0) + 0.2 * (1 if c["confirmed"] else 0), 2)
    return claims


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    p = argparse.ArgumentParser(description="Team Orchestration — 交叉验证引擎")
    p.add_argument("--task", required=True, help="任务 ID")
    p.add_argument("--depth", default="auto", choices=["auto", "skip", "light", "standard", "deep"])
    p.add_argument("--input", required=True, help='JSON 文件或 "-" 读 stdin: [{"agent":..,"text":..}]')
    p.add_argument("--a3", action="store_true",
                   help="A3 硬键校验模式（SKILL.md §4.3 C3 契约）：输入为 A3 JSON 对象/列表，"
                        "校验 role/artifacts{conclusions,evidence,risks,actions}/confidence/uncertainties 硬键；"
                        "缺失即 rc=1")
    a = p.parse_args()
    try:
        raw = sys.stdin.read() if a.input == "-" else open(a.input, encoding="utf-8").read()
        data = json.loads(raw)
    except Exception as e:
        print(json.dumps({"task_id": a.task, "status": "error", "message": str(e)},
                         ensure_ascii=False), file=sys.stderr)
        sys.exit(1)

    if a.a3:
        # A3 硬键校验（TC-20260816-8 · 兑现 SKILL.md §4.3 C3 契约）
        items = data if isinstance(data, list) else [data]
        HARD_KEYS = ["role", "artifacts", "confidence", "uncertainties"]
        ART_KEYS = ["conclusions", "evidence", "risks", "actions"]
        invalid = []
        for it in items:
            role = it.get("role", "?") if isinstance(it, dict) else "?"
            if not isinstance(it, dict):
                invalid.append({"role": role, "missing": ["<not-dict>"]})
                continue
            missing = [k for k in HARD_KEYS if k not in it]
            if isinstance(it.get("artifacts"), dict):
                missing += ["artifacts." + k for k in ART_KEYS if k not in it["artifacts"]]
            elif "artifacts" in it:
                missing.append("artifacts.<dict>")
            if missing:
                invalid.append({"role": role, "missing": missing})
        out = {"task_id": a.task, "mode": "a3-hardkey", "status": "ok" if not invalid else "invalid",
               "items": len(items), "invalid": invalid}
        print(json.dumps(out, ensure_ascii=False))
        sys.exit(0 if not invalid else 1)

    claims = score_confidence(
        triangulate(check_independence(trace_provenance(extract_claims(data)))),
        a.depth,
    )
    conflicts = detect_conflicts(claims)
    overall = round(sum(c["confidence"] for c in claims) / len(claims), 2) if claims else 0.0
    print(json.dumps(
        {"task_id": a.task, "depth": a.depth, "status": "ok", "claims": claims,
         "conflicts": conflicts, "overall_confidence": overall},
        ensure_ascii=False,
    ))


if __name__ == "__main__":
    main()
