# 腾讯生态集成团队 SOP
## 基本信息
- **团队名称**: tencent-ecosystem（腾讯生态集成）
- **Agent 数量**: 15
- **触发词**: 腾讯生态/微信集成/企业微信/腾讯云/小程序开发

## 团队架构
| Agent | 角色 | 职责 |
|-------|------|------|
| engineering-wechat-mini-program-developer | 小程序开发 | 微信小程序/小游戏开发 |
| engineering-backend-architect | 后端架构师 | 后端系统设计、API 网关 |
| engineering-frontend-developer | 前端开发 | Web 端界面开发 |
| engineering-mobile-app-builder | 移动端开发 | iOS/Android 应用开发 |
| engineering-api-platform-engineer | API 平台工程师 | REST/GraphQL API 设计 |
| engineering-sre | SRE 工程师 | 系统可靠性、监控告警 |
| engineering-video-streaming-engineer | 视频流工程师 | 直播/点播技术 |
| engineering-voice-ai-integration-engineer | 语音 AI 集成 | 语音识别/TTS 集成 |
| engineering-webassembly-engineer | WebAssembly 工程师 | 高性能 Web 计算 |
| marketing-wechat-official-account | 公众号运营 | 内容运营、粉丝增长 |
| marketing-social-media-strategist | 社媒策略师 | 社交媒体营销方案 |
| marketing-content-creator | 内容创作者 | 营销内容生产 |
| legal-document-review | 法务审核 | 合同审核、合规检查 |
| security-compliance-auditor | 安全合规审计 | 数据安全、隐私合规 |
| data-privacy-officer | 数据隐私官 | 隐私保护合规 |

## SOP 流程

### Phase 1: 需求与架构规划
**输入**: 集成需求概述
**输出**: `integration-architecture.md`
**目的**: 明确集成范围和技术选型
**步骤**:
1. engineering-backend-architect 设计系统架构
2. data-privacy-officer 评估数据合规要求
3. 输出集成架构文档

### Phase 2: 开发实施
**输入**: integration-architecture.md
**输出**: 各模块开发版本
**目的**: 并行开发各集成模块
**步骤**:
1. 前端/后端/小程序团队并行开发
2. API 平台工程师设计接口规范
3. 视频/语音工程师集成多媒体能力
4. 输出各模块开发版本

### Phase 3: 合规与安全审计
**输入**: 各模块开发版本
**输出**: `compliance-report.md`
**目的**: 确保符合腾讯生态合规要求
**步骤**:
1. security-compliance-auditor 执行安全审计
2. legal-document-review 审核法律条款
3. data-privacy-officer 检查数据隐私合规
4. 输出合规报告

### Phase 4: 发布与运营
**输入**: compliance-report.md
**输出**: go-live-checklist.md
**目的**: 确保顺利上线和持续运营
**步骤**:
1. engineering-sre 配置监控告警
2. marketing-wechat-official-account 准备发布内容
3. 输出上线检查清单

## 阶段关卡（Phase Gates）
| 关卡 | 通过条件 | 失败处理 |
|------|----------|----------|
| PG1-架构 | 架构方案通过评审，合规风险已识别 | 重新设计架构 |
| PG2-开发 | 各模块单元测试通过 | 修复阻断缺陷 |
| PG3-合规 | 安全审计无高危漏洞 | 修复后复审 |
| PG4-发布 | SRE 监控就绪，运营计划确认 | 补充监控配置 |
