#!/usr/bin/env python3
"""Expert matching engine v2 — 完整4维度加权匹配算法

根据第一性原理拆解结果，从 WorkBuddy 专家池匹配最合适的专家/团队。

评分公式:
  Score(T, E_i) =
    α × domain_match(T, E_i)        # 领域匹配度 (0.35)
    + β × capability_match(T, E_i)  # 能力匹配度 (0.30)
    + γ × performance_score(E_i)     # 历史表现分 (0.20)
    - δ × current_load(E_i)         # 当前负载惩罚 (0.15)

匹配策略:
  Score > 0.8  → 直调（单专家即可）
  0.5 < Score ≤ 0.8 → 推荐团队（多专家协作）
  Score ≤ 0.5 → 退回到通用 agent

Usage:
  python3 expert_matcher.py --domains "08-FinanceInvestment" "04-DataAI"
  python3 expert_matcher.py --task "帮我分析腾讯股票" --json
"""
import json
import sys
import argparse
import functools
import time
from pathlib import Path

SKILL_DIR = Path.home() / ".config" / "opencode" / "skills" / "team-orchestration"
EXPERT_DIR = SKILL_DIR / "references" / "workbuddy-experts"
SCORES_FILE = SKILL_DIR / "shared" / "expert-scores.json"

# PI 类型中文→英文能力映射
PI_TYPE_EN_MAP = {
    "信息检索型": ["research", "information_retrieval", "search"],
    "分析判断型": ["analysis", "judgment", "evaluation"],
    "创作生成型": ["creation", "generation", "writing"],
    "决策执行型": ["decision", "execution", "action"],
    "协作讨论型": ["collaboration", "discussion", "brainstorm"],
    "质量验证型": ["verification", "quality", "testing", "audit"],
}

# 缓存（60s TTL）
_cache = {"experts": None, "experts_ts": 0, "scores": None, "scores_ts": 0}
CACHE_TTL = 60

# 三阶缓存：L1(永不过期) / L2(300s TTL) / L3(用完即弃)
_TIER_CACHE = {"l1": {}, "l2": {}, "l2_ts": 0}
L2_TTL = 300

TEAMS_INDEX_PATH = SKILL_DIR / "shared" / "teams-index.json"
TEAMS_TIER_PATH = SKILL_DIR / "shared" / "teams-tier.json"
WEIGHT_MATRIX_PATH = SKILL_DIR / "shared" / "weight-matrix.json"
EXPLORATION_LOG_PATH = SKILL_DIR / "shared" / "exploration-log.json"


def _load_team_tier_state() -> dict:
    if TEAMS_TIER_PATH.exists():
        try:
            return json.loads(TEAMS_TIER_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {}
    return {}


def _save_team_tier_state(state: dict):
    TEAMS_TIER_PATH.parent.mkdir(parents=True, exist_ok=True)
    from scripts.file_utils import atomic_write
    atomic_write(TEAMS_TIER_PATH, state)


def get_team_tier(team_name: str) -> str:
    """返回 hot/warm/cold"""
    import time
    state = _load_team_tier_state()
    record = state.get(team_name)
    if record is None:
        return "cold"
    last_used = record.get("last_used", 0)
    now = time.time()
    days = (now - last_used) / 86400
    if days < 7:
        return "hot"
    elif days < 30:
        return "warm"
    return "cold"


def is_cold_team(team_name: str) -> bool:
    return get_team_tier(team_name) == "cold"


def _update_team_tier_state(team_name: str, action: str = "used"):
    import time
    state = _load_team_tier_state()
    now = time.time()
    if team_name not in state:
        state[team_name] = {"first_used": now, "use_count": 0}
    state[team_name]["last_used"] = now
    state[team_name]["use_count"] = state[team_name].get("use_count", 0) + 1
    state[team_name]["last_action"] = action
    _save_team_tier_state(state)


def load_experts_light() -> dict:
    """Tier 1: 只读 teams-index.json，永不过期缓存"""
    if _TIER_CACHE["l1"]:
        return _TIER_CACHE["l1"]

    if TEAMS_INDEX_PATH.exists():
        try:
            data = json.loads(TEAMS_INDEX_PATH.read_text(encoding="utf-8"))
            teams = {}
            for t in data.get("teams", []):
                teams[t["n"]] = {
                    "name": t["n"],
                    "display_zh": t.get("dN", ""),
                    "description_zh": t.get("dD", ""),
                    "category_id": t.get("cId", ""),
                    "expert_type": t.get("eT", ""),
                    "lead_name": t.get("lN", ""),
                    "agent_count": t.get("aC", 0),
                }
            _TIER_CACHE["l1"] = teams
            return teams
        except (json.JSONDecodeError, KeyError, UnicodeDecodeError) as e:
            print(f"[WARN] teams-index.json 解析失败: {e}", file=sys.stderr)

    print("[WARN] teams-index.json 不存在，回退 load_all_experts()", file=sys.stderr)
    fallback = load_all_experts()
    _TIER_CACHE["l1"] = fallback
    return fallback


def _cache_get_tier2(key: str):
    now = time.time()
    if key in _TIER_CACHE["l2"] and now - _TIER_CACHE["l2_ts"] < L2_TTL:
        return _TIER_CACHE["l2"][key]
    return None


def _cache_set_tier2(key: str, val):
    _TIER_CACHE["l2"][key] = val
    _TIER_CACHE["l2_ts"] = time.time()


def _cache_clear_tier2():
    _TIER_CACHE["l2"].clear()
    _TIER_CACHE["l2_ts"] = 0


def load_experts_detail(team_names: list) -> dict:
    """Tier 2: 只读指定团的 plugin.json，L2 缓存 300s"""
    if not team_names:
        return {}

    # 构建缓存 key
    cache_key = "detail:" + ":".join(sorted(team_names))
    cached = _cache_get_tier2(cache_key)
    if cached is not None:
        return cached

    result = {}
    for name in team_names:
        pj = EXPERT_DIR / name / "plugin.json"
        if not pj.exists():
            continue
        try:
            data = json.loads(pj.read_text(encoding="utf-8"))
            agents_dir = EXPERT_DIR / name / "agents"
            agent_files = sorted(agents_dir.glob("*.md")) if agents_dir.exists() else []
            result[name] = {
                "name": name,
                "display_zh": data.get("displayName", {}).get("zh", ""),
                "description_zh": data.get("displayDescription", {}).get("zh", ""),
                "category_id": data.get("categoryId", ""),
                "expert_type": data.get("expertType", ""),
                "lead_name": data.get("members", [{}])[0].get("name", {}).get("zh", "") if data.get("members") else "",
                "agent_count": len(agent_files),
                "agent_names": [f.stem for f in agent_files],
                "profession_zh": data.get("profession", {}).get("zh", ""),
                "members": [
                    {"id": m["id"], "name_zh": m.get("name", {}).get("zh", ""), "role": m.get("role", "")}
                    for m in data.get("members", [])
                ],
            }
        except (json.JSONDecodeError, UnicodeDecodeError, KeyError) as e:
            print(f"[WARN] load_experts_detail: 跳过 {name}: {e}", file=sys.stderr)
            continue

    _cache_set_tier2(cache_key, result)
    return result


def load_agents_lazy(team_name: str) -> dict:
    """Tier 3: 读指定团的 agents/*.md，不缓存（用完即弃）"""
    agents_dir = EXPERT_DIR / team_name / "agents"
    if not agents_dir.exists():
        return {}

    result = {}
    for af in sorted(agents_dir.glob("*.md")):
        try:
            content = af.read_text(encoding="utf-8", errors="replace")
            agent_id = af.stem
            # 从 frontmatter 提取 description
            description = ""
            content_length = len(content)
            for line in content.split("\n"):
                if line.startswith("description:"):
                    description = line.split(":", 1)[1].strip().strip('"')
                    break
            result[agent_id] = {
                "agent_id": agent_id,
                "description": description,
                "content_length": content_length,
                "token_estimate": content_length // 2,
            }
        except OSError as e:
            print(f"[WARN] load_agents_lazy: 跳过 {af.name}: {e}", file=sys.stderr)
            continue

    return result


# 权重配置 — 从 weight-matrix.json 加载
_DEFAULT_WEIGHTS = {"domain": 0.35, "capability": 0.30, "performance": 0.20, "load": 0.15}


def load_weight_matrix(task_type: str = None) -> dict:
    """从 weight-matrix.json 加载权重，无匹配 task_type 时返回 fallback"""
    if WEIGHT_MATRIX_PATH.exists():
        try:
            data = json.loads(WEIGHT_MATRIX_PATH.read_text(encoding="utf-8"))
            if task_type and task_type in data.get("task_types", {}):
                return data["task_types"][task_type]
            return data.get("fallback", _DEFAULT_WEIGHTS)
        except (json.JSONDecodeError, UnicodeDecodeError, KeyError):
            pass
    return dict(_DEFAULT_WEIGHTS)


# 向后兼容引用（从 weight-matrix 读取）
_WEIGHT_MATRIX_CACHE = {}

def _get_weights(task_type: str = None) -> dict:
    cache_key = task_type or "__fallback__"
    if cache_key not in _WEIGHT_MATRIX_CACHE:
        _WEIGHT_MATRIX_CACHE[cache_key] = load_weight_matrix(task_type)
    return _WEIGHT_MATRIX_CACHE[cache_key]


WEIGHTS = _get_weights(None)

# 匹配策略阈值
THRESHOLDS = {
    "direct_call": 0.75,
    "team_recommend": 0.45,
}

# ε-greedy 冷启动配置
_EPSILON_INIT = 0.15
_EPSILON_FLOOR = 0.02
_EPSILON_DECAY = 0.95
_GRADUATE_THRESHOLD = 5

_exploration_cache = None
_exploration_cache_dirty = False


def _get_exploration_log() -> dict:
    global _exploration_cache
    if _exploration_cache is not None:
        return _exploration_cache
    if EXPLORATION_LOG_PATH.exists():
        try:
            _exploration_cache = json.loads(EXPLORATION_LOG_PATH.read_text(encoding="utf-8"))
            return _exploration_cache
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {"version": "1.0", "experts": {}}
    return {"version": "1.0", "experts": {}}


def _save_exploration_log(log: dict):
    global _exploration_cache, _exploration_cache_dirty
    _exploration_cache = log
    _exploration_cache_dirty = True
    EXPLORATION_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    from scripts.file_utils import atomic_write
    atomic_write(EXPLORATION_LOG_PATH, log)


def _get_epsilon(team_name: str) -> float:
    """返回该团的探索概率 ε，随使用次数衰减"""
    log = _get_exploration_log()
    record = log.get("experts", {}).get(team_name)
    if record is None:
        return _EPSILON_INIT
    use_count = record.get("exploration_count", 0)
    epsilon = _EPSILON_INIT * (_EPSILON_DECAY ** use_count)
    return max(epsilon, _EPSILON_FLOOR)


def _should_explore(team_name: str) -> bool:
    """ε-greedy 是否应探索该团"""
    import random
    epsilon = _get_epsilon(team_name)
    # 新专家（无历史分）自动进入探索池
    scores = load_performance_scores()
    if team_name not in scores:
        return True
    return random.random() < epsilon


def _get_exploration_baseline(task_type: str = None) -> float:
    """新专家基准分 = 同类专家历史均值 × 0.8"""
    scores = load_performance_scores()
    if not scores:
        return 0.40
    values = [v.get("score", 0.5) for k, v in scores.items()
              if isinstance(v, dict) and "score" in v and v["score"] > 0]
    if not values:
        return 0.40
    return round(sum(values) / len(values) * 0.8, 4)


def _log_exploration(team_name: str, task_type: str = None, result: str = "explored"):
    """记录一次探索事件到 exploration-log.json"""
    log = _get_exploration_log()
    experts = log.setdefault("experts", {})
    if team_name not in experts:
        experts[team_name] = {"exploration_count": 0, "status": "exploring", "entries": []}
    import time
    experts[team_name]["exploration_count"] += 1
    experts[team_name]["entries"].append({
        "timestamp": time.time(),
        "task_type": task_type or "unknown",
        "result": result,
    })
    if experts[team_name]["exploration_count"] >= _GRADUATE_THRESHOLD:
        experts[team_name]["status"] = "graduated"
    _save_exploration_log(log)


def _cache_get(key):
    now = time.time()
    val, ts = _cache.get(key), _cache.get(f"{key}_ts", 0)
    if val is not None and now - ts < CACHE_TTL:
        return val
    return None


def _cache_set(key, val):
    _cache[key] = val
    _cache[f"{key}_ts"] = time.time()


def load_all_experts() -> dict:
    cached = _cache_get("experts")
    if cached is not None:
        return cached
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

        # 构建专家团元数据
        agents_dir = plugin_dir / "agents"
        agent_files = sorted(agents_dir.glob("*.md")) if agents_dir.exists() else []
        agent_names = [f.stem for f in agent_files]

        # 从 Agent MD 中提取能力关键词
        capabilities = set()
        for af in agent_files:
            try:
                content = af.read_text(encoding="utf-8")
                # 从 frontmatter 提取 description
                for line in content.split("\n"):
                    if line.startswith("description:"):
                        capabilities.add(line.split(":", 1)[1].strip().strip('"'))
                        break
            except (UnicodeDecodeError, OSError):
                continue

        experts[plugin_dir.name] = {
            "name": plugin_dir.name,
            "display_zh": data.get("displayName", {}).get("zh", ""),
            "description_zh": data.get("displayDescription", {}).get("zh", ""),
            "category_id": data.get("categoryId", ""),
            "expert_type": data.get("expertType", ""),
            "lead_name": data.get("members", [{}])[0].get("name", {}).get("zh", "") if data.get("members") else "",
            "agent_count": len(agent_files),
            "agent_names": agent_names,
            "capabilities": list(capabilities),
        }
    _cache_set("experts", experts)
    return experts


def load_performance_scores() -> dict:
    cached = _cache_get("scores")
    if cached is not None:
        return cached
    result = {}
    if SCORES_FILE.exists():
        try:
            result = json.loads(SCORES_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            result = {}
    _cache_set("scores", result)
    return result


def domain_match(task_domains: list, expert: dict) -> float:
    """领域匹配度 (α=0.35) — 基于 categoryId + description 的余弦相似度"""
    if not task_domains:
        return 0.0

    cat_id = expert.get("category_id", "").lower()
    desc = (expert.get("description_zh", "") + expert.get("display_zh", "")).lower()
    expert_text = f"{cat_id} {desc}"

    matched = 0
    for domain in task_domains:
        domain_lower = domain.lower()
        # 精确匹配 categoryId
        if domain_lower in cat_id or cat_id in domain_lower:
            matched += 1
        # 模糊匹配描述
        elif any(word in expert_text for word in domain_lower.replace("-", " ").split()):
            matched += 0.5

    return min(matched / len(task_domains), 1.0)


def capability_match(task_abilities: list, expert: dict) -> float:
    """能力匹配度 (β=0.30) — 基于 Agent MD 能力关键词的交集评分"""
    if not task_abilities:
        return 0.5  # 无能力需求时给中等分

    caps = set(w.lower() for w in expert.get("capabilities", []))
    agent_names = set(w.lower() for w in expert.get("agent_names", []))

    matched = 0
    for ability in task_abilities:
        ab_lower = ability.lower()
        # 检查能力描述
        if any(ab_lower in cap for cap in caps):
            matched += 1
        # 检查 agent 名称
        elif any(ab_lower in an for an in agent_names):
            matched += 0.5

    return min(matched / len(task_abilities), 1.0)


def performance_score(expert_name: str, scores: dict) -> float:
    """历史表现分 (γ=0.20) — 基于 expert-scores.json"""
    record = scores.get(expert_name)
    if record is None:
        return 0.5  # 新专家给默认分
    return min(record.get("score", 0.5), 1.0)


def current_load(expert_name: str, active_experts: list) -> float:
    """当前负载惩罚 (δ=0.15) — 活跃会话中已分配的专家数"""
    count = active_experts.count(expert_name) if active_experts else 0
    # 超过 3 个活跃任务开始惩罚
    return min(count / 5.0, 1.0) if count > 3 else 0.0


def _score_team(name: str, info: dict, weights: dict, task_domains: list,
                task_abilities: list, scores: dict, active_experts: list,
                task_type: str, no_explore: bool) -> dict | None:
    """对单个专家团执行四维评分，返回评分记录或 None"""
    d = domain_match(task_domains, info)
    c = capability_match(task_abilities, info)

    is_new = name not in scores
    if not no_explore and _should_explore(name):
        p = _get_exploration_baseline(task_type)
        l = 0.0
        _log_exploration(name, task_type, "explored")
    else:
        p = performance_score(name, scores)
        l = current_load(name, active_experts)

    total = (weights["domain"] * d +
             weights["capability"] * c +
             weights["performance"] * p -
             weights["load"] * l)
    total = max(0.0, min(total, 1.0))

    if total <= 0.1:
        return None
    return {
        "score": round(total, 4),
        "domain_score": round(d, 4),
        "capability_score": round(c, 4),
        "performance_score": round(p, 4),
        "load_penalty": round(l, 4),
        "strategy": _recommend_strategy(total),
        "weights_used": task_type or "fallback",
        "explored": is_new and not no_explore,
        **info,
    }


def match(task_domains: list, task_abilities: list = None,
          active_experts: list = None, top_k: int = 3,
          task_type: str = None, force_team: str = None,
          no_explore: bool = False) -> list:
    """执行完整4维度加权匹配（支持 task-type 权重）

    D1: 三阶加载管道:
      Tier 1 — teams-index.json 粗筛（domain 预过滤）
      Tier 2 — plugin.json 精筛（加 agent_names 能力匹配）
      Tier 3 — agent .md 懒加载（orchestrator 执行前）
      回退: load_all_experts() 当 teams-index.json 不存在时

    Args:
        task_domains: 知识域列表
        task_abilities: 能力需求列表
        active_experts: 当前活跃专家列表
        top_k: 返回前 K 个
        task_type: 任务类型（从 weight-matrix.json 选择权重）
        force_team: 跳过匹配，直接返回指定团队
        no_explore: 禁用 ε-greedy 探索（测试用）
    """
    if force_team:
        experts = load_all_experts()
        if force_team in experts:
            info = experts[force_team]
            return [{
                "score": 1.0, "domain_score": 1.0, "capability_score": 1.0,
                "performance_score": 0.5, "load_penalty": 0.0,
                "strategy": "direct_call", "forced": True,
                **info,
            }]
        return []

    weights = _get_weights(task_type)
    scores = load_performance_scores()
    active_experts = active_experts or []
    task_abilities = task_abilities or []

    # 中文 PI 类型→英文能力转换
    _converted = []
    for ab in task_abilities:
        if ab in PI_TYPE_EN_MAP:
            _converted.extend(PI_TYPE_EN_MAP[ab])
        else:
            _converted.append(ab)
    task_abilities = _converted

    # D1: 三阶加载管道
    light_experts = load_experts_light()
    first = next(iter(light_experts.values()), {})
    is_full = "capabilities" in first or "agent_names" in first

    if is_full:
        # 回退路径：light 已 fallback 到 load_all_experts
        scored = []
        for name, info in light_experts.items():
            rec = _score_team(name, info, weights, task_domains, task_abilities,
                              scores, active_experts, task_type, no_explore)
            if rec:
                scored.append(rec)
        scored.sort(key=lambda x: -x["score"])
        for m in scored[:top_k]:
            _update_team_tier_state(m["name"], "matched")
        return scored[:top_k]

    # Tier 1: domain 预过滤（light 数据无 agent_names/capabilities）
    # 冷团在 Tier 1 提前跳过，避免进入 Tier 2 的 plugin.json 加载
    pre_scored = []
    if not task_domains:
        # 无领域需求时，所有非冷团队进入 Tier 2
        for name in light_experts:
            if is_cold_team(name) and not no_explore and not _should_explore(name):
                continue
            pre_scored.append({"name": name, "score": 0.25})
    else:
        for name, info in light_experts.items():
            if is_cold_team(name) and not no_explore and not _should_explore(name):
                continue
            d = domain_match(task_domains, info)
            t = weights["domain"] * d
            if t > 0.05:
                pre_scored.append({"name": name, "score": round(t, 4)})

    pre_scored.sort(key=lambda x: -x["score"])
    top_candidates = [m["name"] for m in pre_scored[:15]]

    # Tier 2: plugin.json 精筛（冷团已在 Tier 1 跳过）
    detail_experts = load_experts_detail(top_candidates)
    merged = {n: detail_experts.get(n, light_experts.get(n)) for n in top_candidates}

    scored = []
    for name, info in merged.items():
        rec = _score_team(name, info, weights, task_domains, task_abilities,
                          scores, active_experts, task_type, no_explore)
        if rec:
            scored.append(rec)

    scored.sort(key=lambda x: -x["score"])
    for m in scored[:top_k]:
        _update_team_tier_state(m["name"], "matched")
    return scored[:top_k]


def _recommend_strategy(score: float) -> str:
    if score > THRESHOLDS["direct_call"]:
        return "direct_call"
    elif score > THRESHOLDS["team_recommend"]:
        return "team_recommend"
    else:
        return "fallback"


def main():
    ap = argparse.ArgumentParser(description="专家匹配引擎 v2")
    ap.add_argument("--domains", nargs="+", default=[], help="知识域列表")
    ap.add_argument("--abilities", nargs="+", default=[], help="能力需求列表")
    ap.add_argument("--task", default="", help="任务描述（自动拆解）")
    ap.add_argument("--task-type", default=None,
                    choices=["analysis_judgment", "information_retrieval", "creation_generation",
                             "decision_execution", "collaborative_discussion", "quality_verification"],
                    help="任务类型（从 weight-matrix 选权重）")
    ap.add_argument("--force-team", default=None, help="跳过匹配，直接指定团队")
    ap.add_argument("--json", action="store_true", help="JSON 格式输出")
    ap.add_argument("--no-explore", action="store_true", help="禁用 ε-greedy 探索")
    ap.add_argument("--top-k", type=int, default=3, help="返回前 K 个匹配")
    args = ap.parse_args()

    domains = args.domains
    abilities = args.abilities

    # 如果提供了 task 但没提供 domains，自动拆解
    if args.task and not domains:
        import importlib.util
        td_path = Path(__file__).parent / "task_decomposer.py"
        td_spec = importlib.util.spec_from_file_location("td_mod", str(td_path))
        td_mod = importlib.util.module_from_spec(td_spec)
        td_spec.loader.exec_module(td_mod)
        result = td_mod.decompose(args.task)
        domains = result["domains"]
        # B2: match() 内部会自动转换中文 PI 类型→英文能力，直接传入 pi_types
        abilities = result.get("pi_types", [])

    matches = match(domains, abilities, top_k=args.top_k,
                    task_type=args.task_type, force_team=args.force_team,
                    no_explore=args.no_explore)

    if args.json:
        print(json.dumps(matches, ensure_ascii=False, indent=2))
    else:
        experts = load_all_experts()
        weights = _get_weights(args.task_type)
        print(f"专家池: {len(experts)} 个专家团")
        print(f"权重 (task_type={args.task_type or 'default'}): "
              f"domain={weights['domain']} capability={weights['capability']} "
              f"performance={weights['performance']} load={weights['load']}")
        print(f"匹配结果 (Top {len(matches)}):")
        print()
        for m in matches:
            print(f"  [{m.get('category_id','')}] {m.get('display_zh','')} "
                  f"({m.get('agent_count',0)} agents)")
            print(f"      综合评分: {m['score']:.1%} | "
                  f"领域 {m['domain_score']:.1%} + "
                  f"能力 {m['capability_score']:.1%} + "
                  f"历史 {m['performance_score']:.1%} - "
                  f"负载 {m['load_penalty']:.1%}")
            strat_label = {"direct_call": "直调", "team_recommend": "推荐团队", "fallback": "退回到通用agent"}
            extra = " [强制指定]" if m.get("forced") else (" [探索]" if m.get("explored") else "")
            print(f"      策略: {strat_label.get(m['strategy'], m['strategy'])}{extra}")
            print()


if __name__ == "__main__":
    main()
