
# ClawTeam 交接协议（HandoffProtocol?
> 标准化交接文档格式，供主理人中转时使?---
## 通用交接格式
```yaml---type: handoffteam: <software
|investment|research>phase: <phase-number>source_agent: <agent-id>target_agent: <agent-id>date: <YYYY-MM-DD>run_id: <colony-run-id>---
```
### 内容区块
```
## 已完成内容摘?（≤200字，说明本阶段产出）
## 产物位置- colony/context/<run-id>/<文件>
## 验收标准（下丢阶段 agent 的验收条件：
必须包含X/Y/Z?
## 已知问题（未完成?风险?待确认事项）
## 下一步行?（对下一 agent 的明确指令）
```---
## 软件团队交接示例**PRD→架构设计交?*
```yaml---type: handoffteam: softwarephase: 2source_agent: software-product-managertarget_agent: software-architectdate: 2026-05-15run_id: abc12345---
## 已完成内容摘?PRD已完成，包含3个用户故事?个P0霢求UI流程图?
## 产物位置- colony/context/abc12345/prd.md
## 验收标准architecture.md 必须包含?- 系统架构图（mermaid?- 模块划分 ??task-list.md 必须包含?- 任务依赖关系- 优先级标?
## 已知问题- 登录模块霢确认第三方OAuth方案- 性能要求待明?
## 下一步行?按PRD实现系统架构设计，重点关注登录和核心模块边界
```---
## 投资团队交接示例**分析师信号→风险评估交接**
```yaml---type: handoffteam: investmentphase: 2source_agent: portfolio-managertarget_agent: risk-managerdate: 2026-05-15run_id: def67890---
## 已完成内容摘?19位分析师已完成信号输出，其中18位返回有效分析，1位超时未返回?
## 产物位置- colony/context/def67890/analyst-signals/oracle-of-omaha.md- colony/context/def67890/analyst-signals/charlie-munger.md- colony/context/def67890/analyst-signals/fundamentals-analyst.md- ...（共18个有效文件）
## 验收标准risk-report.md 必须包含?- 汇表（所有分析师核心判断?- 波动率评估（历史/隐含?- 朢大回撤估?- 仓位上限建议- 风险等级（低/??极高?
## 已知问题- oracle-of-omaha ?fundamentals-analyst 对估值有分歧- 消息面分析师信号较弱
## 下一步行?综合19位分析师信号，输出风险评估报告，重点标注分歧?
```---
## 研究团队交接示例**初调→大纲规划交?*
```yaml---type: handoffteam: researchphase: 2source_agent: topic-researchertarget_agent: research-plannerdate: 2026-05-15run_id: ghi11111---
## 已完成内容摘?初始调研完成，来源池15条，含学术论??媒体7?行业报告3?官方1条?
## 产物位置- colony/context/ghi11111/initial-summary.md- colony/context/ghi11111/sources-pool.md
## 验收标准outline.md 必须包含?- 章节??- 逻辑递进（无重叠?- 每章明确来源要求
## 已知问题- 某些子话题来源偏少，霢要在后续章节补充- 数据朢新待确认
## 下一步行?基于调研摘要设计研究大纲，规划章节结构和深度
```---
## 主理人铁?
| 编号 | 禁止 ||------|------|| 1 | ?跳过建立团队的正式流?|| 2 | ?自己代写成员专业产出 || 3 | ?跳过前序阶段直接进入后续阶段 || 4 | ?成员间直连信，必须经主理人中?|| 5 | ?跳过 Gated 关卡强制放行 |