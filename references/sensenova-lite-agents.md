# 免费池子代理路由：sensenova-6.8-flash-lite 三池（v3.9.3 · TC-20260906-3）

> 依据：商汤 SenseNova 官网 https://www.sensenova.cn/models （2026-09-06 查证）——SenseNova 6.8 Flash Lite 定位「轻量级多模态智能体模型」，官方卖点：① 多模态理解增强、端到端任务执行稳定；② 重点优化数据分析与复杂信息呈现（办公场景）；③ 轻量高效、推理快、Token 效率优（长链路任务 Token 节约约 60%）。注册参数（`<LOCAL:.zcode/v2/config.json>`）：输入 text+image / 输出 text，context 256k / output 65k，reasoning off|high（默认 high）。

## 1 三个免费池与子代理映射

同一模型注册在三个独立提供商（独立 apiKey，同 baseURL `https://token.sensenova.cn/v1`），按工作类型分派到不同池以摊薄单池配额：

| 子代理（subagent_type） | 池（frontmatter `model`） | provider uuid | 工作范围（对齐官方能力） |
|---|---|---|---|
| `sensenova-analyst` | `10c5f3ab-7a48-46d3-9ea8-55dd27243ff7/sensenova-6.8-flash-lite`（日日新池） | 10c5f3ab-7a48-46d3-9ea8-55dd27243ff7 | 数据分析与复杂信息呈现：结构化数据解读、指标计算、报表/图表规格、办公数据处理 |
| `sensenova-researcher` | `b41b3807-9e46-4977-b917-34040c3ee1a7/sensenova-6.8-flash-lite`（日日新1池） | b41b3807-9e46-4977-b917-34040c3ee1a7 | 端到端调研执行：长文档解读（256k 长上下文）、多源整合、调研分段执行、资料核实 |
| `sensenova-batch-runner` | `65253d20-7075-40d4-bf57-7d12a57014ef/sensenova-6.8-flash-lite`（日日新2池） | 65253d20-7075-40d4-bf57-7d12a57014ef | 轻量批量执行（Token 效率优）：批量文本处理、格式转换、清单核对、模板化生成 |

> **model 字段格式实证（2026-09-06 TC-20260906-4 故障定位 · 源码+运行时双证据）**：ZCode 把 frontmatter `model` 按首个 `/` 拆为 providerId/modelId（`om()` 仅 trim 不做大小写/别名规范化），再查 providers 注册表——**注册表键 = config.json `provider` 对象的键原文（uuid），name 一律不入表**。实测：`日日新2/...` 与 mini-vision 的 `OPENCODE-CHAT/mimo-v2.5` 均报 `Model provider is not configured`（mini-vision 自注册以来 name 格式一直是坏的，从未被真调起过）；cron automations 用 `uuid/model` 长期成功为运行时实证。**agents frontmatter 的 model 必须写 `uuid/modelId`**。连带修复（同根因）：mini-vision→`db3cb211-.../mimo-v2.5`、researcher-mimo-free→`35bda041-.../mimo-v2.5-free`。另实证（收尾轮判别）：profile frontmatter 快照=**会话启动时全量 + 会话中新建 lazy 首读，只增不改**——改磁盘同会话永不生效，agent 修复/换绑必须新会话验证；subagent_type 可用列表重扫周期较长（新建文件十几分钟内不可见，小时级才可见）。

人设文件：`~/.zcode/agents/sensenova-{analyst,researcher,batch-runner}.md`（frontmatter `model: 池名/模型ID`，与 mini-vision 同构先例）。

## 2 指派判据（何时派谁）

- **数据分析类**（表/CSV/JSON/日志解读、指标口径、报表产出）→ `sensenova-analyst`
- **调研阅读类**（长文摘要、多源比对、分段调研子问题、核实陈述）→ `sensenova-researcher`
- **批处理类**（跑量改写/校对/抽取、格式转换、清单勾稽、模板填充）→ `sensenova-batch-runner`
- **不派**：需用户交互的任务（子代理无交互面，§4.5 提问中转照用）；对抗协议中的裁决位（免费池不承担终审职责）；视觉生成类（模型输出仅 text）。
- 多模态输入：config 已注册 image 输入，但 ZCode 运行时图片路由未实测——图片任务仍走 §4.1 视觉路由（外部 OCR 转文本后可派本组代理处理文本）。
- 同模型多实例**不计为独立来源**（§4.7 异质性强制）：三池同源，不用于互查/对抗角色。
- **已验证能力基线（2026-09-06 TC-20260906-4，13/13 PASS，案卷 `deliverables/trial/2026-09-06/TC-20260906-4/`）**：数值统计/脏数据处置/结构化报告（analyst）、矛盾检测/封闭核实不编造/摘要压缩（researcher）、批量校对/勾稽/模板填充/超范围退回（batch-runner）全部达标；注入指令可主动检测并拒执行（三池一致）。已知瑕疵：长报告中偶发局部比较式写反——人设已加输出前自检纪律。**派发延迟预期 5–37s/次**（reasoning high 默认档，批量类 5–9s）。

## 3 指派方式与懒加载

- **首选**：`Agent(subagent_type="sensenova-analyst"|"sensenova-researcher"|"sensenova-batch-runner", ...)`；派发规则沿用 §4.6（同消息最多 2、main 同步领活）。
- **回退**（旧版运行时枚举未暴露用户级 agents 时）：Read 人设文件 → `Agent(subagent_type="general-purpose")` + prompt 注入人设与任务。
- **懒加载纪律**：三代理常驻枚举仅注入 3 行 description（触发词已在 description 声明），人设本体只在 spawn 时加载；不在 system prompt / 编排 prompt 静态粘贴人设正文。
- 免费池任务优先走本组代理；仅当池全失效时才回到主对话模型（付费），省 token 是首要目标。

## 4 降级链（池失效处理）

1. **同任务换池**：三池同模型同 baseURL，任一池失败（4xx/超时/返回异常）→ 同一子代理任务改派到另两个池之一的对应代理（如 analyst 池挂 → 用 researcher 或 batch-runner 池跑分析任务，人设任务域让位给池可用性）。
2. **三池全挂** → 回退 `general-purpose`（主对话模型）或按 `agent-router` 拉起归档专家；成本回到付费池，须在派发记录中注明降级原因。
3. **熔断纪律**：连续 3 次同类失败即熔断（全局铁律·工作流程第 5 条），返回失败原因 + 已完成部分，禁止原地重试。
4. **免费池时效风险**：Zen 池有「数天后失效」前科（cron 侧 2026-09-06 换绑记录）。换绑流程：先活体探测（参考 `<LOCAL:.zcode/workspace/default/_research/sensenova_probe.py>`，host 白名单 token.sensenova.cn）→ 确认新池可用 → 改三份人设 frontmatter `model` 字段 → 本文档表头同步 → 记忆 `zcode-cron-automations-state` 更新。

## 5 验证清单（新会话）

- 新会话系统提示的 subagent_type 枚举应出现 `sensenova-analyst` / `sensenova-researcher` / `sensenova-batch-runner`（常驻 agent 84 = 81 + 3）。
- 冒烟：`Agent(subagent_type="sensenova-batch-runner")` 派一条 3 行文本格式转换任务，回传 A3/清单即通过；若报 `Agent type not found` → 走 §3 回退路径。
- **模型绑定验证（本会话已实证格式要求）**：frontmatter 必须为 `uuid/model` 格式（§1），name 格式已确认失败（`Model provider is not configured`）。新会话调起成功即证 uuid 生效；若仍报 provider not configured，查 config.json 顶层 `provider` 键下 uuid 是否漂移（对照 §1 表）。
- 真调起端到端测试欠账：模型能力+人设约束层已由 API 直调 13/13 覆盖（TC-20260906-4）；**harness 集成层（uuid 绑定→子代理实际跑在 sensenova 上）待新会话冒烟确认**，确认后可查 `tasks-index.sqlite` tasks 表新增行的 model 字段做硬证据。
