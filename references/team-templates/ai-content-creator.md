
# AI 内容创作团队 SOP
## 基本信息- **团队名称**：
ai-content-creator（AI内容创作?- **Agent 数量**?- **触发?*：
AI内容创作/多模态内?视频生成/内容创作
## 团队架构
| Agent | 角色 | 职责 ||-------|------|------|| content-director | 内容总监 | 制定内容计划、协调各环节、把关质?|| scriptwriter | 脚本撰写 | 撰写视频/图文脚本，规划叙事结?|| visual-artist | 视觉艺术?| 生成图像、设计视觉元?|| video-editor | 视频剪辑?| 将素材剪辑成片，做配处理 || platform-adapter | 平台适配 | 根据平台特调整内容格式和风格 |
## SOP 流程
### Phase 1：
内容计?**输入**：
用户需求描?**输出**：
`content-plan.md`**目的**：
明确内容方向目标受众平台择**步骤**?1. content-director 分析用户霢?2. 确定内容类型（视?图文/多模态）3. 选定目标平台（抖?小红?YouTube 等）4. 编写内容计划文档
### Phase 2：
素材生?**输入**：
content-plan.md**输出**：
脚?+ 视觉素材**目的**：
生成完整的创作素材**步骤**?1. scriptwriter 撰写完整脚本2. visual-artist 生成配套图像3. 素材汇到 artifacts/{team_id}/
### Phase 3：
制作剪?**输入**：
素?**输出**：
粗剪版?**目的**：
完成内容主体制?**步骤**?1. video-editor 将素材剪辑成?2. 加入转场、音效字?3. 输出粗剪版本供审?
### Phase 4：
平台配**输入**：
粗剪版?**输出**：
各平台朢终版?**目的**：
配不同平台的格式要?**步骤**?1. platform-adapter 分析各平台特?2. 调整时长、比例封?3. 生成各平台最终版?
## 阶段关卡（Phase Gates?
| 关卡 | 通过条件 | 失败处理 ||------|----------|----------|| PG1-内容计划 | content-plan.md 包含完整的类?受众/平台信息 | 返回 Phase 1 重新规划 || PG2-素材生成 | 脚本已定稿，视觉素材至少 3 个可用版?| 补充素材或调整方?|| PG3-制作剪辑 | 粗剪版本时长误差 <10%，叙事完?| 重剪或修改脚?|| PG4-平台适配 | 各平台版本格式符合要?| 调整格式参数 |
## 交接协议
### 产出物格?
```yaml---team_id: {team_id}agent_id: content-directorrole: 内容总监phase: planningstatus: donefindings: |  内容类型：
短视频  目标平台：
抖音小红书  目标受众?8-25岁女?---
```
### 验收字段- `phase`：
当前完成的阶段- `status`：
done/in_progress- `findings`：
核心产出描