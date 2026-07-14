# 专家文件组织规范（全部归集到 skill）

版本: v2.6
决策: 用户选择「全部归集到 skill」— 所有 335 个专家资产的 prompt 文件完整归入 skill 文件夹

---

## 一、目录结构

```
references/workbuddy-experts/
├── _index.md                           # 主索引（所有 335 个专家资产）
│
├── {team-name}/                        # 团队型专家（已有 28 团 + 移植 18 团 + 新建 3 团 = 49 团）
│   ├── _index.md                       # 团描述 + agent 列表
│   ├── plugin.json                     # 团配置（categoryId, displayName, agents[]）
│   └── agents/
│       ├── {agent-1}.md                # 完整 agent prompt
│       ├── {agent-2}.md
│       └── ...
│
├── {expert-name}/                      # 独立型专家（271 人，每人一个目录——单 Agent 团）
│   ├── _index.md                       # same 格式，但 agents = [{name,description}]
│   ├── plugin.json                     # single-agent 配置
│   └── agents/
│       └── expert.md                   # 完整 prompt（从 WorkBuddy 源复制）
│
└── groups/                             # 虚拟分组（非目录，通过 group_id 逻辑关联）
    └── README.md                       # 分组映射说明（哪些 expert 属于哪个虚拟团）
```

## 二、独立专家目录规范

每个独立专家目录结构：
```
{expert-name}/
├── _index.md
│   content: |
│     # {expert-display-name}
│     type: single-agent
│     group_id: game-development | industry-consulting | tencent-ecosystem | ungrouped
│     original_path: WorkBuddy/.../source-path  # 原始来源路径（供追踪）
│     
├── plugin.json
│   {
│     "categoryId": "07-GameSpace",
│     "displayName": "游戏策划专家",
│     "description": "擅长游戏策划...",
│     "agents": [{"name": "expert", "description": "..."}],
│     "agent_count": 1
│   }
│
└── agents/
    └── expert.md                       # 完整 prompt，从原始 WorkBuddy prompt 文件复制
```

## 三、虚拟团 vs 独立专家关系

| 虚拟团 | 包含独立专家数 | 角色分配 |
|--------|--------------|---------|
| game-development | 25 人 | 策划4/美术4/程序5/QA3/运营3+备用6 |
| industry-consulting | 17 人 | 分析师5/顾问5/报告撰写4+备用3 |
| tencent-ecosystem | 34 人 | 云架构6/营销5/合规4/技术6+备用13 |
| ungrouped | 209 人 | 暂未分组，通过 `groups/README.md` 追踪 |

**匹配策略**: 
- match() 匹配时优先匹配虚拟团
- 虚拟团内 agents 不够时自动从 group 内未分配专家中增补
- 独立专家也可以单独匹配（通过 Tier 1 索引）

## 四、空间估算

| 类型 | 数量 | 平均大小 | 总计 |
|------|------|---------|------|
| 已有团 | 29 | ~15KB | 435KB |
| 移植团 | 18 | ~15KB | 270KB |
| 虚拟团 | 3 | ~10KB | 30KB |
| 独立专家 | 271 | ~3KB | 813KB |
| 索引+配置 | ~5 | ~20KB | 20KB |
| **总计** | **335** | | **~1.6MB** |

## 五、与三阶加载的兼容

- **Tier 1** `shared/teams-index.json`: 所有 335 个专家资产的最小元数据（含独立专家和团队）
- **Tier 2** `plugin.json`: 31 团的 plugin.json；独立专家和 fused agent 的 plugin.json 按需加载
- **Tier 3** `agent .md`: 只加载最终选中专家（无论是团内 agent 还是独立专家）
- 独立专家调用：单 Agent 模式下 load_agents_lazy() 只读 1 个 .md 文件
