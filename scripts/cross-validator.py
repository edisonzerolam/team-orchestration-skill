# cross-validator.py — 交叉验证编排核心
# v2.3: 声明提取 → 来源追溯 → 独立性检查 → 三角测量 → 冲突检测 → 置信度校准
# 使用: python3 cross-validator.py --task <task_id> --depth auto|skip|light|standard|deep

import argparse
import json
import re
import sys
from pathlib import Path


def extract_claims(agent_outputs: list) -> list:
    """从专家输出中提取原子声明"""
    claims = []
    for output in agent_outputs:
        text = output.get("text") or output.get("output") or str(output)
        sentences = re.split(r'[。！？\n\.]', text)
        for i, sent in enumerate(sentences):
            sent = sent.strip()
            if len(sent) < 10:
                continue
            claims.append({
                "claim_id": f"{output.get('agent','?')}_{i}",
                "text": sent,
                "source_agent": output.get("agent", "unknown"),
                "source_task": output.get("task_id", ""),
            })
    return claims


def trace_provenance(claims: list) -> list:
    """为每个声明追溯来源"""
    for c in claims:
        text = c.get("text", "")
        sources = []
        urls = re.findall(r'https?://[^\s\)\]>"]+', text)
        for u in urls:
            sources.append({"type": "url", "value": u})
        file_refs = re.findall(r'[\w/]+\.\w{2,4}(?::\d+)?', text)
        for f in file_refs:
            if any(f.endswith(ext) for ext in ['.md','.py','.json','.csv','.txt']):
                sources.append({"type": "file", "value": f})
        c["provenance"] = sources if sources else [{"type": "inferred"}]
    return claims


def check_independence(sources: list) -> list:
    """检查来源独立性（同源检测）"""
    issues = []
    seen = {}
    for src in sources:
        key = (src.get("type", ""), src.get("value", ""))
        if key in seen:
            issues.append({"source": key, "issue": "同源依赖",
                           "agents": [seen[key], src.get("source_agent", "?")],
                           "severity": "medium"})
        seen[key] = src.get("source_agent", "?")
    return issues


def _tokenize(text: str) -> set:
    """将文本拆分为有意义的 token（中文二元组 + 英文单词）"""
    import re as _re
    tokens = set()
    # 中文：提取所有连续中文字符，生成二元组
    chinese_chunks = _re.findall(r'[\u4e00-\u9fff]+', text)
    for chunk in chinese_chunks:
        tokens.update(chunk[i:i+2] for i in range(len(chunk) - 1))
    # 英文/数字：按空格切词
    eng_tokens = _re.findall(r'[a-zA-Z0-9]+', text)
    tokens.update(t.lower() for t in eng_tokens)
    if not tokens:
        tokens = set(text)
    return tokens


def triangulate(claims: list) -> list:
    """跨源三角测量（一致性检查）—— 基于 token（中文二元组+英文单词）的 Jaccard 相似度"""
    results = []
    for i, a in enumerate(claims):
        for j, b in enumerate(claims):
            if i >= j or a["source_agent"] == b["source_agent"]:
                continue
            a_text = a.get("text", "")
            b_text = b.get("text", "")
            a_tokens = _tokenize(a_text)
            b_tokens = _tokenize(b_text)
            common = a_tokens & b_tokens
            overlap = len(common) / max(len(a_tokens | b_tokens), 1)
            if overlap > 0.6:
                results.append({
                    "claim_a": a["claim_id"],
                    "claim_b": b["claim_id"],
                    "overlap": round(overlap, 2),
                    "verdict": "convergent",
                })
    return results


def detect_conflicts(claims: list) -> list:
    """检测跨源冲突"""
    conflicts = []
    for i, a in enumerate(claims):
        for j, b in enumerate(claims):
            if i >= j or a["source_agent"] == b["source_agent"]:
                continue
            a_text = a.get("text", "")
            b_text = b.get("text", "")
            if not a_text or not b_text:
                continue
            pos_pairs = [("利好", "利空"), ("增长", "下降"), ("买入", "卖出"),
                         ("看涨", "看跌"), ("高估", "低估"), ("推荐", "不推荐")]
            for pos, neg in pos_pairs:
                if pos in a_text and neg in b_text:
                    conflicts.append({
                        "claim_a": a["claim_id"],
                        "claim_b": b["claim_id"],
                        "pattern": f"{pos} vs {neg}",
                        "severity": "high",
                    })
                    break
    return conflicts


def score_confidence(claims: list, depth: str = "standard") -> dict:
    """综合评分：一致性 + 验证强度 + 源层级加权"""
    if not claims:
        return {"score": 0.5, "details": {"reason": "无声明"}}
    n_agents = len(set(c.get("source_agent", "?") for c in claims))
    n_sourced = sum(1 for c in claims if c.get("provenance", [{"type":"inferred"}])[0]["type"] != "inferred")
    triangulations = triangulate(claims)
    conflicts = detect_conflicts(claims)

    diversity = min(1.0, n_agents / 3.0)
    evidential = min(1.0, n_sourced / max(len(claims), 1))
    consistency = max(0.0, 1.0 - len(conflicts) / max(len(claims), 1))

    if depth == "deep":
        score = diversity * 0.3 + evidential * 0.4 + consistency * 0.3
    elif depth == "light":
        score = consistency
    else:
        score = diversity * 0.25 + evidential * 0.35 + consistency * 0.4

    return {
        "score": round(score, 3),
        "details": {
            "agent_diversity": round(diversity, 2),
            "evidential_strength": round(evidential, 2),
            "consistency": round(consistency, 2),
            "sourced_claims": n_sourced,
            "triangulation_pairs": len(triangulations),
            "conflicts_found": len(conflicts),
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Team Orchestration — 交叉验证引擎")
    parser.add_argument("--task", required=True, help="任务 ID")
    parser.add_argument("--depth", default="auto",
                        choices=["auto", "skip", "light", "standard", "deep"])
    parser.add_argument("--input", default=None, help="输入 JSON 文件路径（agent outputs）")
    args = parser.parse_args()

    if args.input:
        input_path = Path(args.input)
        if input_path.exists():
            agent_outputs = json.loads(input_path.read_text(encoding="utf-8"))
            claims = extract_claims(agent_outputs)
            claims = trace_provenance(claims)
            sources = [p for c in claims for p in c.get("provenance", [])]
            independence = check_independence(sources)
            confidence = score_confidence(claims, args.depth)

            result = {
                "task_id": args.task,
                "depth": args.depth,
                "status": "completed",
                "claims_count": len(claims),
                "independence_issues": len(independence),
                "confidence": confidence,
            }
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return

    result = {"task_id": args.task, "depth": args.depth,
              "status": "completed", "note": "无输入文件，跳过详细验证"}
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
