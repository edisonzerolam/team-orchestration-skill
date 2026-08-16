#!/usr/bin/env python3
"""Expert matching engine for team-orchestration.

Matches task decomposition results against the WorkBuddy expert pool.
"""
import json, sys, os, argparse
from pathlib import Path
import sys
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# WorkBuddy 适配：改为相对于本脚本定位专家库，安装位置无关
EXPERT_DIR = Path(__file__).resolve().parent.parent / "references" / "workbuddy-experts"
SKILL_DIR = Path(__file__).resolve().parent.parent

# 聚合域路由（v3.9 · TC-20260816-5）：39 团队归入 8 大聚合域，--domain 限域召回
# 与 SKILL.md §8.1 / references/skills-pack.md 同步维护
AGGREGATE_DOMAINS = {
    "投资分析": ["investment-masters-team", "trading-agent", "stock-partner-team",
                "a-share-analysis", "equity-research"],
    "资本服务": ["pe-vc-investment", "investment-banking", "wealth-management"],
    "法律服务": ["chatlaw-team", "cn-litigation", "enterprise-legal-team", "tax-compliance-team"],
    "内容全链路": ["ai-content-creator-team", "content-distribution-team",
                  "content-monetization-team", "promo-creator-team"],
    "营销增长": ["marketing-campaign-team", "sales-battle-team", "seo-content-team",
                "social-engagement-team"],
    "工程保障": ["engineering-assurance-team", "gstack", "devtools-engineering",
                "rum-fullstack-team", "alicloud-engineering", "software-company"],
    "数据智能": ["ai-data-copilot", "huashu-data-pro"],
    "产品设计": ["product-strategy-team", "design-engine", "product-design-suite"],
}

def filter_by_domain(experts: dict, domain: str) -> dict:
    """按聚合域名过滤专家池（域内团队），未知域名返回原池（不误伤）。
    v3.9 双匹配：聚合域映射 team 名优先；兼容 plugin.json name 与目录名不一致的情况。"""
    teams = AGGREGATE_DOMAINS.get(domain)
    if not teams:
        return experts
    # 双匹配：目录名（key）或 plugin.json name 字段命中任一即算域内
    team_set = set(teams)
    return {name: info for name, info in experts.items()
            if name in team_set or info.get("name") in team_set}

def _coerce(v):
    if v.lower() in ("true", "false"):
        return v.lower() == "true"
    try:
        return int(v)
    except ValueError:
        pass
    try:
        return float(v)
    except ValueError:
        pass
    return v

def _load_yaml(path):
    """Minimal YAML: 2-space indent nested maps, scalar values. No list support."""
    tree = {}
    stack = [(-1, tree)]
    try:
        for line in open(path, encoding="utf-8"):
            s = line.rstrip("\n")
            if not s.strip() or s.strip().startswith("#"):
                continue
            indent = len(s) - len(s.lstrip(" "))
            key, _, val = s.strip().partition(":")
            key = key.strip()
            val = val.strip()
            while stack and stack[-1][0] >= indent:
                stack.pop()
            parent = stack[-1][1]
            if val == "":
                node = {}
                parent[key] = node
                stack.append((indent, node))
            else:
                parent[key] = _coerce(val)
    except FileNotFoundError:
        return {}
    return tree

_MATCHER_KEYS = ("category", "bigram", "capability", "history")
_MATCHER_DEFAULT = {"category": 0.40, "bigram": 0.35, "capability": 0.15, "history": 0.10}


def _load_matcher_config():
    cfg = _load_yaml(SKILL_DIR / "config.yaml")
    m = (cfg.get("matcher") or {})
    w = m.get("weights")
    if w is None:
        w = dict(_MATCHER_DEFAULT)  # 整块缺失才回退默认
    elif not isinstance(w, dict) or any(
        k not in w or not isinstance(w[k], (int, float)) or not 0 <= w[k] <= 1
        for k in _MATCHER_KEYS
    ):
        raise ValueError(f"matcher.weights 非法（须含四键且取值 0~1）: {w}")
    total = sum(float(w[k]) for k in _MATCHER_KEYS)
    if abs(total - 1.0) > 0.05:
        print(f"[WARN] matcher.weights 四键之和={total:.2f}，偏离 1.0，请检查 config.yaml")
    return {
        "weights": w,
        "min_score": m.get("min_score", 0.30),
        "top_k": m.get("top_k", 3),
        "history_file": m.get("history_file", "references/learning-data/expert_scores.json"),
    }

MATCHER_CFG = _load_matcher_config()

def _bigram_jaccard(text_a: str, text_b: str) -> float:
    """中文 bigram Jaccard 相似度（纯标准库）。"""
    def _bigrams(s):
        s = s.lower().replace(" ", "")
        return set(s[i:i+2] for i in range(len(s)-1)) if len(s) >= 2 else set()
    ba, bb = _bigrams(text_a), _bigrams(text_b)
    if not ba or not bb:
        return 0.0
    return len(ba & bb) / len(ba | bb)

def _extract_capabilities(plugin_dir):
    """从 agents/*.md 提取能力关键词。"""
    agents_dir = plugin_dir / "agents"
    caps = []
    if not agents_dir.exists():
        return caps
    for md in agents_dir.glob("*.md"):
        try:
            text = md.read_text(encoding="utf-8")
        except Exception:
            continue
        for line in text.splitlines()[:30]:
            if "擅长" in line or "专业" in line or "能力" in line:
                stripped = line.strip().lstrip("-# ").strip()
                if stripped and len(stripped) > 2:
                    caps.append(stripped)
    return caps

def _load_history_scores(history_file):
    p = SKILL_DIR / history_file
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if isinstance(data, dict) and "expert_scores" in data:
        return data["expert_scores"]
    return data if isinstance(data, dict) else {}

def load_all_experts():
    experts = {}
    if not EXPERT_DIR.exists():
        return experts
    for plugin_dir in sorted(EXPERT_DIR.iterdir()):
        if not plugin_dir.is_dir():
            continue
        pj = plugin_dir / "plugin.json"
        if not pj.exists():
            continue
        try:
            data = json.loads(pj.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        agents_dir = plugin_dir / "agents"
        agent_count = len(list(agents_dir.glob("*.md"))) if agents_dir.exists() else 0
        experts[data.get("name", plugin_dir.name)] = {
            "name": data.get("name", ""),
            "display_zh": data.get("displayName", {}).get("zh", ""),
            "description_zh": data.get("displayDescription", {}).get("zh", ""),
            "category_id": data.get("categoryId", ""),
            "expert_type": data.get("expertType", ""),
            "lead_name": data.get("members", [{}])[0].get("name", {}).get("zh", "") if data.get("members") else "",
            "agent_count": agent_count,
            "capabilities": data.get("capabilities", ""),
            "capabilities_list": _extract_capabilities(plugin_dir),
        }
    return experts

def match(experts: dict, domains: list, top_k: int = None, weights: dict = None, task_text: str = "", min_score: float = None) -> list:
    """P0.2: 4-dimensional weighted expert matching.

    Dimensions (weights from config.yaml):
      - category:    domain category id substring in expert category_id
      - bigram:      中文 bigram Jaccard 相似度 (description_zh + capabilities)
      - capability:  domain tokens found in expert capabilities field
      - history:     historical performance score from learning data (0..1)
    Each dim is normalized to [0,1]; total is the weighted sum, capped at 1.0.
    min_score 可覆盖（聚合域限域模式下传 0，域内全召回按分排序——TC-20260816-5）。
    """
    cfg = MATCHER_CFG
    w = weights or cfg["weights"]
    top_k = cfg["top_k"] if top_k is None else max(int(top_k), 0)
    min_score = cfg["min_score"] if min_score is None else min_score
    history = _load_history_scores(cfg["history_file"])
    # task_text: 优先使用显式传入的，否则从 domains 拼接
    if not task_text:
        task_text = " ".join(domains)
    scored = []
    for name, info in experts.items():
        s_cat = 0.0
        s_desc = 0.0
        s_cap = 0.0
        for domain in domains:
            cat_id = domain.split("-", 1)[-1].lower() if "-" in domain else domain.lower()
            tokens = [t for t in cat_id.replace("_", "-").split("-") if t]
            if cat_id and cat_id in info.get("category_id", "").lower():
                s_cat += 1.0
            desc = info.get("description_zh", "").lower()
            cap = (info.get("capabilities", "") or "").lower()
            for t in tokens:
                if t and t in desc:
                    s_desc += 1.0
                if t and t in cap:
                    s_cap += 1.0
        s_cat = min(s_cat, 1.0)
        s_desc = min(s_desc, 1.0)
        s_cap = min(s_cap, 1.0)
        # bigram Jaccard 增强
        desc_zh = info.get("description_zh", "")
        s_desc = max(s_desc, _bigram_jaccard(task_text, desc_zh))
        # capability bigram 增强
        cap_text = " ".join(info.get("capabilities_list", []))
        s_cap = max(s_cap, _bigram_jaccard(task_text, cap_text))
        hist_raw = history.get(name, 0.0)
        try:
            s_hist = float(hist_raw)
        except (TypeError, ValueError):
            s_hist = 0.0
        s_hist = min(max(s_hist, 0.0), 1.0)
        # 权重已由 _load_matcher_config 校验（四键存在），此处直取避免不一致兜底默认
        total = (w["category"] * s_cat
                 + w["bigram"] * s_desc
                 + w["capability"] * s_cap
                 + w["history"] * s_hist)
        total = min(total, 1.0)
        if total >= min_score:
            scored.append((round(total, 4), info))
    scored.sort(key=lambda x: -x[0])
    return scored[:top_k]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--domains", nargs="+", default=[])
    ap.add_argument("--domain", default="",
                    help="聚合域限域召回（v3.9 · TC-20260816-5）：投资分析|资本服务|法律服务|内容全链路|营销增长|工程保障|数据智能|产品设计")
    ap.add_argument("--task", default="")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--top-k", type=int, default=3)
    args = ap.parse_args()
    experts = load_all_experts()
    if args.domain:
        experts = filter_by_domain(experts, args.domain)
    if args.domains:
        # 聚合域限域：域内全召回按分排序（min_score=0），避免硬阈值清空域内结果
        matches = match(experts, args.domains, args.top_k, task_text=args.task,
                        min_score=0 if args.domain else None)
    else:
        # WorkBuddy 适配：task-decomposer.py 含连字符，无法用 `import` 直接导入，改用 importlib 按路径加载
        import importlib.util as _ilu
        _td_path = Path(__file__).resolve().parent / "task-decomposer.py"
        _td_spec = _ilu.spec_from_file_location("task_decomposer_mod", str(_td_path))
        _td_mod = _ilu.module_from_spec(_td_spec)
        _td_spec.loader.exec_module(_td_mod)
        result = _td_mod.decompose(args.task)
        # 聚合域限域时同样放宽阈值（min_score=0），域内全召回按分排序
        matches = match(experts, result["domains"], args.top_k, task_text=args.task,
                        min_score=0 if args.domain else None)
    if args.json:
        print(json.dumps([{"score": round(s, 2), **m} for s, m in matches], ensure_ascii=False, indent=2))
    else:
        print(f"专家池: {len(experts)} 个专家团")
        print(f"匹配结果 (Top {len(matches)}):")
        for score, info in matches:
            print(f"  [{info.get('category_id','')}] {info.get('display_zh','')} ({info.get('agent_count',0)} agents) — 匹配度: {score:.0%}")

if __name__ == "__main__":
    main()
