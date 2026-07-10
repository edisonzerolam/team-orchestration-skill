# Team Orchestration v2.6 强化方案（P0 实施版）

基于 331 个 WorkBuddy 专家资产盘点 + 互联网调研 + 专家小组分析，产出本实施方案。

审计状态: 🔴 已过审（含条件，详见 AUDIT-REPORT.md）

---

## 一、现状诊断

| 维度 | 现状 | 问题 |
|------|------|------|
| 专家池 | 29/46 专家团(188 agents) + 6 subagent | 18 团未移植（含 openspec-doc 实际已移植），285 独立专家未利用 |
| 匹配算法 | 4 维固定权重(35/30/20/15) | 无动态调整，无冷启动，无跨领域 |
| 模板 | 15 个快速路径 | 缺口领域无模板，大团无裁剪 |
| 自愈 | L0-L3 四层防御 + 熔断器 | 缺乏专家替换链和回滚自动化 |
| 历史评分 | expert-scores.json | 冷启动问题，评分维度单一 |

## 二、核心改进

### P0-1: 动态权重匹配矩阵

**目标**: 从固定 4 维权重改为 6 种任务类型的动态权重矩阵

**6 种任务类型**:
| 类型 | 典型场景 |
|------|---------|
| analysis_judgment | 股票分析、风险评估、审计 |
| information_retrieval | 搜索、调研、数据采集 |
| creation_generation | 写作、内容生成、设计 |
| decision_execution | 代码实现、策略执行 |
| collaborative_discussion | 研讨、辩论、头脑风暴 |
| quality_verification | 测试、审查、验证 |

**权重矩阵** (任务类型 × 4 维度):
| 任务类型 | 领域 | 能力 | 历史 | 负载 |
|---------|------|------|------|------|
| analysis_judgment | 0.35 | 0.25 | 0.25 | 0.15 |
| information_retrieval | 0.40 | 0.30 | 0.15 | 0.15 |
| creation_generation | 0.25 | 0.40 | 0.20 | 0.15 |
| decision_execution | 0.30 | 0.35 | 0.20 | 0.15 |
| collaborative_discussion | 0.30 | 0.30 | 0.20 | 0.20 |
| quality_verification | 0.25 | 0.30 | 0.30 | 0.15 |

### P0-2: ε-greedy 冷启动策略

**问题**: 新引入专家无历史表现数据，performance_score = 0 导致匹配偏低

**方案**: 
- ε = 0.15 概率探索新专家
- 探索衰减: ε = max(0.02, ε × 0.95^(使用次数))
- 新专家基准分: 同类专家历史均值的 80%

**阈值调整**:
- 匹配 > 0.75 → 直调
- 0.45 ≤ 匹配 ≤ 0.75 → 推荐团队
- 匹配 < 0.45 → 退回到通用 agent + 标记「匹配不确定性高」

### P0-3: 专家资产全量归集 + 新增 3 个虚拟专家团

**归集策略（用户决策：全部归集到 skill）**:
- 28 个已有团：维持现有 `references/workbuddy-experts/` 不变
- 18 个待移植团：完整复制到 `references/workbuddy-experts/{name}/`
- 285 个独立专家：每个独立专家在 `references/workbuddy-experts/{name}/` 下创建单 Agent 目录（含 plugin.json + prompt.md）
- **总计**: skill 文件夹内管理 28+18+3 = 49 个专家团 + 285 个独立专家 = 334 个专家
- **设计文档**: `references/expert-files-organization.md`

**新增 3 个虚拟专家团（从 285 个独立专家中组合）**:

**1. game-development (游戏开发专家团)**
- 来源: 25 个游戏空间领域独立专家
- 角色: 策划/美术/程序/QA/运营各 3-5 人
- 触发: 游戏开发、游戏策划、Unity、Unreal

**2. industry-consulting (行业咨询专家团)**
- 来源: 17 个行业顾问领域独立专家
- 角色: 分析师/顾问/报告撰写各 4-6 人  
- 触发: 行业分析、市场研究、战略咨询

**3. tencent-ecosystem (腾讯生态专家团)**
- 来源: 腾讯专区 34 个独立专家 + RUM 团
- 角色: 云架构/营销/合规/技术各 5-8 人
- 触发: 腾讯云、微信生态、小程序、企业微信

### P0-4: 模板动态裁剪

**问题**: 大团队(如 investment-masters 22 人)启动消耗大量 Token，多数子 Agent 未参与

**方案**: 
- 基于子任务类型自动裁剪 40-78%
- 预留 20% 弹性容量
- 裁剪规则见 `references/team-templates/dynamic-cropping.md`

**示例**:
| 原团队 | 裁剪后 | 节省 |
|--------|--------|------|
| investment-masters (22) | 6-10 人 | 55-73% |
| trading-agent (13) | 4-7 人 | 46-69% |
| enterprise-legal (9) | 3-5 人 | 44-67% |

### P0-5: 专家评分卡 (v1)

**评分维度** (5 维, 每维 1-10):
| 维度 | 权重 | 采集方式 |
|------|------|---------|
| 任务完成率 | 30% | 自动追踪 |
| 交付质量 | 25% | reviewer 评分 |
| 响应时间 | 15% | 自动计时 |
| 用户反馈 | 20% | 用户评价 |
| 协作评分 | 10% | 队友互评 |

**存储**: `shared/expert-scores.json`（扩展 schema）

### P0-6: 三阶层次化加载 + 热/温/冷分级 + Token 预算管理

**问题**: `load_all_experts()` 每次匹配全量扫描 49 团（~300 文件 I/O, 5-10MB），实际只用 Top-3。无分级缓存，无 Token 预算上限。

**方案**: 将加载拆为三阶，匹配阶段 I/O 从 300+ 次降至 1~12 次：

| 层级 | 数据源 | 大小 | I/O | 加载时机 | 缓存 |
|------|--------|------|-----|---------|------|
| Tier 1 | `shared/teams-index.json` | ~7KB | 1 | 技能启动时 | 永不过期 |
| Tier 2 | 候选团 `plugin.json` × 5-10 | ~100KB | 5-10 | 粗筛命中时 | 5min TTL |
| Tier 3 | 选中团 `agents/*.md` × 1 | ~200KB | ~10 | orchestrator 执行前 | 用完即弃 |

**热/温/冷分级**:
- 🔥 Hot（< 7天）：全路径加载，正常匹配优先级
- 🔶 Warm（7-30天）：只加载 plugin.json，agent .md 按需懒加载
- 🔵 Cold（> 30天）：仅扫描 Tier 1 索引，不加载详情

**Token 预算管理**:
- 三级模式：turbo(150K/团) / standard(120K/团) / economy(60K/团)
- 自动降级：预算使用率 ≥ 85% → 自动切 economy
- Standby agent：不活跃 agent 只加载 ~200 tokens 元数据（vs 完整 2000-5000）
- 执行后记账：记录到 token-ledger.json

**Token 节省估算**:
| 阶段 | 当前 | 优化后 | 节省 |
|------|------|--------|------|
| 匹配 I/O | 300+ 文件 | 1~12 文件 | **96%+** |
| 匹配上下文 | 49 团全量 | 3 团精筛 | **~90%** |
| 大团执行 | 22 agent 全量 | 6-10 agent(裁剪) + standby | **40-78%** |
| 冷团匹配 | 全量加载 | 0 读取 | **100%** |

**设计文档**: `references/3-tier-hierarchical-loading.md`

## 三、可执行任务清单

### File 1: 匹配引擎重写
- [ ] `scripts/expert_matcher.py` — 改为动态权重矩阵 + ε-greedy
- [ ] `references/expert-matching.md` — 更新设计文档
- [ ] 新增 `shared/weight-matrix.json` — 权重矩阵配置文件
- [ ] 新增 `shared/exploration-log.json` — 探索日志

### File 2: 专家池扩展
- [ ] 移植 18 个待移植专家团到 `references/workbuddy-experts/`
- [ ] 新增 3 个虚拟专家团配置文件
- [ ] 更新 `references/workbuddy-experts/_index.md`
- [ ] 更新 SKILL.md 顶部可用专家池数字

### File 3: 模板动态裁剪
- [ ] 新增 `references/team-templates/dynamic-cropping.md`
- [ ] 新增 `scripts/template-cropper.py` — 裁剪计算
- [ ] 为 6 个大团队设置裁剪配置

### File 4: 专家评分卡
- [ ] 扩展 `shared/expert-scores.json` schema
- [ ] 新增 `scripts/score-collector.py` — 评分采集
- [ ] 集成到 `scripts/self-evolution/post-task-evolve.py`（子任务完成后自动触发）

### File 5: 主工作流集成
- [ ] 更新 `references/team-templates/index.md`
- [ ] 测试匹配引擎 + 裁剪 + 评分卡 + 懒加载的集成
- [ ] 更新 SKILL.md 新增内容

### File 6: 三阶层次化加载 + 分级 + Token 预算
- [ ] 预生成 `shared/teams-index.json`（Tier 1 索引）
- [ ] 新增 `load_experts_light()` — Tier 1 加载
- [ ] 新增 `load_experts_detail()` — Tier 2 按需加载
- [ ] 新增 `load_agents_lazy()` — Tier 3 延迟加载
- [ ] 新增热/温/冷分级逻辑（`shared/teams-tier.json`）
- [ ] 新增 BudgetController（`shared/budget-config.json` + `scripts/budget-controller.py`）
- [ ] 三级缓存配置（`shared/cache-config.json`）
- [ ] Token 记账（`shared/token-ledger.json`）
- [ ] 更新 `scripts/migrate-workbuddy.py` 集成索引生成

## 四、风险评估

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| 动态权重矩阵初始值不准确 | 中 | 中 | 保留回退到固定权重的开关 |
| 独立专家组合质量不稳定 | 高 | 中 | P0 只选 3 个高质量领域，逐步扩展 |
| 裁剪后团队能力不足 | 中 | 高 | 预留 20% 弹性容量 + 运行时自动增补 |
| 冷启动探索导致初期匹配差 | 中 | 低 | ε 初始 0.15，快速衰减 |
| 评分卡冷启动无历史数据 | 高 | 低 | 基准分设为同类均值的 80% |
| Tier 1 索引与团目录不同步 | 中 | 中 | `load_experts_light()` 自动检测版本号 |
| L2 缓存过期导致 Tier 2 重复 I/O | 低 | 低 | 5min TTL 已足够，手动可 --refresh-cache |
| Token 记账不准（无法精确统计模型 token） | 中 | 低 | 用字符估算 × 系数，允许 ±20% 误差 |
| Cold 团在紧急场景需要但被分级错过 | 低 | 高 | ε-greedy 可探索冷团，用户也可 `--force-team` |

## 五、验收标准

1. 匹配精度 ≥ 0.78 (基于历史数据回测)
2. 大团队 Token 消耗降低 ≥ 40%
3. 冷启动专家能在 5 次调用内达到正常匹配水平
4. 3 个虚拟团首次调用成功率 ≥ 70%
5. 现有 15 个模板 + 29 个已有团零退化
6. 匹配阶段 I/O 从 300+ 次降至 ≤ 12 次（Tier 1 × 1 + Tier 2 × 10 + Tier 3 × 0）
7. Cold 团匹配时 Zero agent .md 读取
8. Budget 自动降级阈值 85% 准确触发
