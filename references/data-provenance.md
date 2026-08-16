# 数据来源可靠性矩阵（Data Provenance）

> v3.9 · TC-20260816-6 补强 · 技能全部记录与外部来源数据的可靠性分层与查证方式
> 配套契约：SKILL.md §9.5 外部数据查证纪律

## 一、自身执行记录（来源=本技能运行产物 · 可靠性高）

| 数据 | 生成者 | 查证方式 | 备注 |
|---|---|---|---|
| docket-*.json（10） | trial-court-orchestrator | 案卷 deliverables/trial/ 重放对照 | 完整归档 |
| trial-count.json | init/归档计数 | 重算 | — |
| expert_scores.json | 归档写端 | 重算 | ⚠️ 0.55 为冷启动缺省值，非实测命中率 |
| cases/facts/strategies/experiences/patterns/strategy.json | 自学习（knowledge-merger 等） | 重放 | 量少（experiences 2 条） |

## 二、官方文档来源（可查证 · 有保鲜机制）

| 数据 | 官方来源 | 保鲜 | 更新方式 |
|---|---|---|---|
| concurrency-data.json | DeepSeek rate_limit 页（api-docs.deepseek.com） | 14 天 | stale → 派子代理查官方 → update 写回；失败 → max_spawned+1 试探 |

## 三、本机扫描数据（可再生成 · 缺保鲜提示）

| 数据 | 生成者 | 过期风险 | 建议 |
|---|---|---|---|
| last-asset-snapshot.json（69KB） | asset-resolver --snapshot | 快照即过期（记录扫描时状态） | 使用时核对 snapshot_at，>30 天提示重新生成 |
| asset-issue-map.md | 同上 | 同上 | 同上 |

## 四、市场导入数据（provenance 保留）

| 数据 | 来源 | 复核能力 |
|---|---|---|
| workbuddy-experts/（40 团队 plugin.json + agents） | WorkBuddy/QoderWork 市场（_source/_enhancedWith 字段） | ⚠️ 上游已证损坏（TC-20260816-4），无法复核——如实标注 |

## 五、推断/补全数据（knowledge/*.md 修复值）

| 类别 | 示例 | 查证 |
|---|---|---|
| 可查证（已核实） | 滞纳金万分之五/专利 20-10-15 年/LPR4 倍/FCPA 25万-200万 等（TC-20260816-4 互联网核实 16 类+修正 8 处） | web_search ✅ 可行可靠 |
| 不可查证（须标注） | 做空跌幅 -50%/GDP 5.2%/抖音流量池阈值/架构评分 8/10 等（修复员上下文推断，原始字节丢失） | ❌ 无权威源——**标注"推断值"，不作权威依据** |

## 六、查证纪律（SKILL.md §9.5 落地）

**能查官方查官方 → 能再生成就保鲜 → 查不到就如实标注**——禁止把推断值当事实使用。
