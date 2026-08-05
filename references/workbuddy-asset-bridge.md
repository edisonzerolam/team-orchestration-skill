# WorkBuddy 资产桥接层（Asset Bridge Layer）
> **DEPRECATED（v2.5 资产桥接层设计，已废弃）**：资产权重与解析流程以 SKILL.md v3.1 + config.yaml 为准，本文档仅存档供历史参考。

> 定义 team-orchestration 技能如何动态发现、匹配并调用 WorkBuddy 的全量资产。
> 资产 = 技能(Skill) + 插件(Plugin) + MCP工具 + 连接器(Connector) + 专家/专家团(Expert/Team) + 未来类型

---

## 1. 资产全景图

| 资产类型 | 本机存量 | 发现方式 | 调用方式 | 桥接状态 |
|---------|---------|---------|---------|---------|
| **技能 (Skill)** | ~56 个 | `~/.workbuddy/skills/<name>/` 目录扫描 | 读取 SKILL.md，按指令调用 | ✅ 可实现 |
| **插件-专家团 (Expert Team)** | 28 团 / 188 agent | `~/.workbuddy/plugins/marketplaces/experts/plugins/<name>/` | `workbuddy-adaptation.md` Mode A/B | ✅ 已集成 |
| **MCP 工具集** | 7 个已连接 | `connector-states.v3.json` enabled 列表 | 当前对话上下文中有 MCP 工具可直接调用 | ✅ 可桥接 |
| **连接器 (Connector)** | 7 已连接 + 更多已装 | 连接器配置目录 + 状态文件 | 通过 MCP 协议调用各连接器暴露的工具 | ✅ 可桥接 |
| **插件-官方 (Official)** | 内置插件 | `codebuddy-plugins-official/` | 部分有对应 Skill 暴露 | ⚠️ 间接桥接 |
| **未来类型** | — | 注册制：实现 `AssetResolver` 接口 | 扩展 Asset Bridge | 🔮 预留 |

---

## 2. 资产发现引擎

### 2.1 技能发现（Skill Discovery）

```python
# 扫描 ~/.workbuddy/skills/<name>/SKILL.md 的 description 字段
# 提取能力标签与触发词
def discover_skills() -> list[Skill]:
    skills = []
    for skill_dir in glob("~/.workbuddy/skills/*/"):
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue
        # 读取 description 和 available_skills 部分
        description = extract_description(skill_md)
        trigger_keywords = extract_triggers(skill_md)
        skills.append(Skill(
            name=skill_dir.name,
            description=description,
            triggers=trigger_keywords,
            path=str(skill_dir)
        ))
    return skills
```

### 2.2 MCP 工具发现（MCP Tool Discovery）

```python
# 读取 connector-states.v3.json，获取已启用的 MCP 工具
def discover_mcp_tools() -> list[MCPTool]:
    state = json.loads(read("connector-states.v3.json"))
    mcp_config = json.loads(read("mcp.json"))
    tools = []
    for connector_name in state.get("enabled", []):
        mcp_key = f"connector:{connector_name}"
        config = mcp_config.get("mcpServers", {}).get(mcp_key, {})
        tools.append(MCPTool(
            connector_name=connector_name,
            url=config.get("url", ""),
            disabled=config.get("disabled", False),
            # 从连接器技能 SKILL.md 提取能力描述
            capabilities=extract_connector_capabilities(connector_name)
        ))
    return tools
```

### 2.3 专家团发现（Expert Team Discovery）

沿用 `references/workbuddy-adaptation.md` 的 28 团索引 + `_index.md`，
补充：读取每个团队的 `self-evolution-log.md` 获取历史表现。

### 2.4 插件发现（Plugin Discovery）

扫描 `~/.workbuddy/plugins/marketplaces/` 下的所有 `plugin.json`：

```python
def discover_plugins() -> list[Plugin]:
    for marketplace in ["experts/plugins", "codebuddy-plugins-official"]:
        for plugin_dir in glob(f"plugins/marketplaces/{marketplace}/*/"):
            pj = plugin_dir / "plugin.json"
            if not pj.exists():
                continue
            data = json.loads(pj.read_text())
            plugins.append(Plugin(
                name=data.get("name", ""),
                display_name=data.get("displayName", {}),
                category=data.get("categoryId", ""),
                expert_type=data.get("expertType", ""),
                agents=len(list(plugin_dir.glob("agents/*.md"))),
            ))
    return plugins
```

---

## 3. 资产-议题匹配策略

### 3.1 匹配流程

```
议题类型标签（如 "08-FinanceInvestment", "11-SecurityCompliance"）
    │
    ├── Skill Matcher
    │    从 ~/.workbuddy/skills/ 中筛选 triggers 匹配议题类型的技能
    │    输出：{name, match_score, usage_hint}
    │
    ├── MCP Matcher
    │    从已连接 MCP 工具中筛选 capabilities 匹配议题类型的工具
    │    输出：{connector, tools[], match_score}
    │
    ├── Expert Matcher
    │    从 workbuddy-experts/ 中用 expert-matcher.py 匹配
    │    输出：{team, agents[], match_score}
    │
    ├── Connector Matcher
    │    从已授权连接器中匹配数据服务能力
    │    输出：{connector, data_capabilities, match_score}
    │
    └── Aggregator
        综合加权排序 → ResolvedAssets
```

### 3.2 加权评分公式

```
total_score(type) = match_relevance * type_weight

type_weights:
    expert_team:  0.35  # 专家团权重最高（人设丰富度）
    mcp_tool:     0.30  # MCP 工具可直接调用
    skill:        0.20  # 技能需间接加载
    connector:    0.10  # 连接器数据能力
    plugin:       0.05  # 插件配合使用
```

### 3.3 常用议题类型 → 资产映射（启动指南）

| 议题类型 | 推荐专家团 | 推荐MCP/连接器 | 推荐Skill |
|---------|-----------|---------------|----------|
| 金融投资/股票分析 | a-share-analysis, stock-partner-team | tdx-connector, westock-mcp | akshare-stock, fund-advisor-cn |
| 法律/合规咨询 | chatlaw-team, enterprise-legal-team | — | — |
| 财税/税务 | tax-compliance-team | — | — |
| 市场营销/增长 | marketing-campaign-team, seo-content-team | — | marketing-skills |
| 软件工程 | software-company, gstack | github | — |
| 内容创作 | ai-content-creator-team, humanize-ppt-team | — | — |
| 深度研究 | gpt-researcher-team | — | deep-research |
| 销售作战 | sales-battle-team | qq-mail | — |

---

## 4. 资产调用锚点（在审判庭流程中）

### 4.1 Phase A 立案阶段

```
[资产感知] → 解析议题类型 → 调用 resolve_assets_for_issue()
    → 结果写入 docket.assets_resolved
    → 在争点清单中标注"可用资产提示"
```

### 4.2 Phase B 举证阶段

```
[资产注入] → 在子代理 prompt 中携带可用资产提示：
    "你有以下工具可用：
      - MCP 工具：通达信(查行情/财务)、腾讯自选股(查数据)
      - 连接器：QQ邮箱(收邮件)
      - 技能：deep-research(深入调研)
      - 专家团推荐：a-share-analysis(如需进一步分析)"
```

### 4.3 Phase C 质证阶段

```
[资产回溯] → 检查举证产物是否充分使用了可用资产
    → 如某项主张缺乏数据支撑，提示子代理使用对应MCP工具补充
    → 记录"本次未使用但应使用的资产"→ 写入学习记录
```

### 4.4 Phase D 终审阶段

```
[资产总结] → 终审意见书中包含"本次使用资产清单"
    → 评估各资产对终局结论的贡献度
    → 写入审判记录归档
```

---

## 5. 子代理 prompt 中的资源提示模板

```markdown
## 可用资源

### 🛠 MCP 工具
{动态列表，如：通达信(查A股行情/财务/资金流向)
                    腾讯自选股(查股票/ETF/板块数据)
                    腾讯地图(地理信息)
                    企查查(工商信息)
                    QQ邮箱(邮件发送与读取)}

### 🔌 连接器
{动态列表，已授权的外部服务}

### 📦 技能（可按需加载）
{动态列表，如：deep-research — 深度调研
                    fund-advisor-cn — 基金分析
                    marketing-skills — 营销策略}

### 👥 专家团（可对话模式调用）
{动态列表，如：a-share-analysis(金融/投资类问题)
                    enterprise-legal-team(法律合规类)}
```

---

## 6. 资产快照（启动时预生成）

首次调用 Asset Bridge 时生成 `last_asset_snapshot.md`，包含：
- 当前日期时间
- 已连接 MCP 工具清单
- 已安装技能清单（按分类）
- 可用专家团清单
- 建议的议题类型→资产映射（基于历史匹配）

用于快速判断而不必每次全量扫描。

---

## 7. 扩展指南：添加新资产类型

```python
# Step 1: 在 asset-resolver.py 中创建解析器子类
class MyNewAssetResolver(AssetResolver):
    def name(self) -> str:
        return "my_new_asset"
    
    def resolve(self, issue_type: str, docket) -> list[Asset]:
        # 实现发现逻辑
        return [...]
    
    def priority(self) -> int:
        return 30  # 在专家(10)和MCP(20)之后

# Step 2: 注册到 Registry
AssetRegistry.register(MyNewAssetResolver())

# Step 3: 定义 Asset 子类（可选，复用 Asset 基类则用 type="future"）
```
