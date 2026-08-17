# Team Orchestration Skill — Multi-Agent Adversarial Orchestration Engine

> The expert pool draws on expert capabilities from WorkBuddy and QoderWork.

> [中文版 / Chinese README](./README.md)

## Overview

This is a **DSH (DeepSeek Harness) Skill** providing **multi-agent adversarial orchestration** — the core is the **Five-Phase Adversarial Protocol (Two-Instance Final Adjudication)**: for complex topics, organize multi-perspective expert subagents through evidence → cross-examination → first instance → second-instance final adjudication to converge on high-quality conclusions.

```
Task → Case Filing (complexity/division/concurrency) → Parallel Evidence (N subagents) → Cross-Examination (feed-back & revise)
     → First Instance (verdict + 1 fixed revision round) → Second-Instance Final (no re-feed) → Delivery + Archive
```

## Core Features (v3.9.0-dsh)

### ⚖️ Five-Phase Adversarial Protocol (Two-Instance Final Adjudication)
Case filing (5W2H clarification + issue decomposition) → parallel evidence (2-6 subagents independently gather evidence) → cross-examination (feed other parties' output, revise item by item; 1 round default, max 2) → first instance (verdict + 1 fixed revision round) → **second-instance final adjudication** (final ruling, no new arguments allowed). Includes **final-adjudication pre-gate** (echoes from all subagents must be collected), BATNA degradation, and independent review (§7.3, prefers the General Critics team).

### 🧭 Aggregate-Domain Routing
40 expert teams are organized into **8 aggregate domains** (Investment Analysis / Capital Services / Legal Services / Content Pipeline / Marketing Growth / Engineering Assurance / Data Intelligence / Product Design). Teams are **composed on demand across domains** (agent-hypernetwork idea: 257-agent component pool activated per task, directories physically preserved with zero breakage). Script-level support: `expert-matcher.py --domain 投资分析 --task "..."` for domain-restricted recall.

### 📦 Task-Level Skill Packaging (Agent Skills idea)
5 high-frequency tasks packaged as reusable skills (trigger words + team composition + workflow + output contract): **Investment Analysis / Legal Consultation / Content Production / Technical Review / Deep Research** (`references/skills-pack.md`) — a task-capability unit one level above tools and one level below full agents.

### 🧠 General Critics (general-critics)
`general-critic` (adversarial review lead: hypothesis testing / bias detection / five-dimension rubric) + `devil-advocate` (strongest counter-arguments / extreme scenarios / consensus stress tests) — balance the blind spots of vertical experts, serving cross-examination and final quality gates.

### 🎛 Dynamic Dispatch Mechanism
No more guesswork on subagent count: `task-decomposer --concurrency N` outputs `suggested_subagents{value, range, rationale}` — **N = complexity base × division bonus × model-concurrency cap × budget hard constraint C(N,q)=N×(2+q)**. L1 straight-through / L2 straight-through signal / L3+ clamp[2, min(concurrency, tier cap)]; the suggested value is not mandatory — main can override with rationale.

### 🗄 Data Governance
- **Concurrency reference data freshness** (`concurrency-data.json`): official model concurrency from vendor docs (DeepSeek v4-flash=2500, account-level), **14-day freshness window** — stale data triggers a subagent to refresh from official docs; on failure, probe with `max_spawned+1`; every actual dispatch is force-recorded (`record --n N` after B-phase spawn)
- **Data provenance discipline** (`references/data-provenance.md` + SKILL.md §9.5): official source when available → freshness refresh when regenerable → honest labeling when unverifiable; never treat inferred values as facts

### 🛡 Quality Gates
- **40/40 tests green** (run_smoke: script smoke / reference integrity / encoding health / expert-pool consistency / dynamic dispatch / concurrency data)
- **Encoding gate**: whole-package UTF-8 strict scan + C5.2 `?` placeholder detection (root cure for 46 historically corrupted files)
- Dual-encoding regression (GBK console + UTF-8)

## Expert Pool (40 Teams / 257 Agents)

### 8 Aggregate Domains

| Domain | Teams | Trigger scenarios |
|---|---|---|
| Investment Analysis | investment-masters + trading-agent + stock-partner + a-share-analysis + equity-research | stocks/valuation/long-short/buy advice |
| Capital Services | pe-vc-investment + investment-banking + wealth-management | financing/IPO/family office |
| Legal Services | chatlaw-team + cn-litigation + enterprise-legal-team + tax-compliance-team | contracts/litigation/compliance/tax |
| Content Pipeline | ai-content-creator + content-distribution + content-monetization + promo-creator | video/copy/distribution/monetization |
| Marketing Growth | marketing-campaign + sales-battle + seo-content + social-engagement | ads/leads/SEO/social |
| Engineering Assurance | engineering-assurance + gstack + devtools-engineering + rum-fullstack + alicloud-engineering + software-company | architecture review/code review/QA/cloud |
| Data Intelligence | ai-data-copilot + huashu-data-pro | SQL/data analysis |
| Product Design | product-strategy + design-engine + product-design-suite | PRD/UX/design system |

### General Adversarial Layer
- `gpt-researcher-team` (deep-research fallback)
- `general-critics` (adversarial review + devil's advocate)

> Full index: `references/workbuddy-experts/_index.md` (40 teams / 257 agents, disk and declaration consistent).

## Installation (DSH)

```powershell
# Copy to the user-level skills root (DSH scans ~/.agents/skills/, zero build, hot-loaded)
$src = "C:\path\to\team-orchestration"
$dst = "$env:USERPROFILE\.agents\skills\team-orchestration"
if (Test-Path $dst) { Remove-Item $dst -Recurse -Force }
Copy-Item $src $dst -Recurse

# Smoke test
python "$dst\scripts\task-decomposer.py" --task "帮我分析宁德时代" --json
python "$dst\scripts\expert-matcher.py" --domain 投资分析 --task "帮我分析宁德时代" --json
```

> This skill is a **prompt-level orchestration methodology + pure-stdlib Python decision scripts**; DSH ships all required runtime primitives (`subagent`/`send_message` parallel & feed-back, `ask_user_question` clarification, `goal`/`todo` checkpoints, `pwsh` script execution). See `references/dsh-adaptation.md`.

## Quick Start

```bash
# 1. Case filing: decompose + dynamic dispatch (complexity × division × concurrency)
python scripts/task-decomposer.py --task "帮我分析宁德时代的基本面" --concurrency 6 --json
#    → complexity: L3-复杂, suggested_subagents: {value:4, range:[2,6], rationale:...}

# 2. Domain-restricted expert recall (aggregate-domain routing)
python scripts/expert-matcher.py --domain 投资分析 --task "帮我分析宁德时代" --top-k 3 --json

# 3. Concurrency reference-data check (14-day freshness, stale → auto-update hint)
python scripts/concurrency_check.py check

# 4. Run the five-phase adversarial protocol (see SKILL.md §3)
```

## Testing & Verification

```bash
python tests/run_smoke.py                  # 40/40 full smoke
python tests/check_references.py           # reference integrity (zero dead links)
python tests/test_file_health.py           # UTF-8 health + C5.2 ? placeholder gate
python scripts/check_team_consistency.py   # expert pool declaration == assets
python scripts/check_agent_completeness.py # agent template completeness
```

## File Structure

```
team-orchestration/
├── SKILL.md                           # Main contract (v3.9.0-dsh)
├── references/
│   ├── skills-pack.md                 # Task-level Skill packaging (5 skills)
│   ├── data-provenance.md             # Data provenance matrix (verification discipline)
│   ├── concurrency-data.json          # Model concurrency reference data (14-day freshness)
│   ├── trial-court-protocol.md        # Five-phase protocol detailed spec
│   ├── dsh-adaptation.md              # DSH adaptation guide
│   ├── workbuddy-experts/             # 40 imported expert teams
│   │   ├── _index.md                  # Category index (8 aggregate domains + general layer)
│   │   ├── general-critics/           # General Critics team (v3.9 self-built)
│   │   └── {team}/                    # Per team: plugin.json + agents/*.md
│   ├── knowledge/                     # 42 domain knowledge files
│   └── team-templates/                # Team templates
├── scripts/                           # 19 .py (16 top-level + 3 self-evolution)
│   ├── task-decomposer.py             # Decompose + dynamic dispatch (--concurrency)
│   ├── expert-matcher.py              # Aggregate-domain routing (--domain)
│   ├── concurrency_check.py           # Concurrency data check (check/record/update)
│   ├── trial-court-orchestrator.py    # Docket/archive/self-learning backend
│   └── self-evolution/                # Self-evolution trio
├── tests/                             # 40 test cases
└── README.md                          # Chinese README
```

## Expert Pool Origin

The 40 expert teams in this skill **draw on expert capabilities from WorkBuddy and QoderWork**, adapted for the DSH environment (relative script paths, bilingual plugin.json metadata preserved, integrated with the five-phase adversarial protocol).

## License

MIT License
