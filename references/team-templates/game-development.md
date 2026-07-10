# 游戏开发全流程团队 SOP
## 基本信息
- **团队名称**: game-development（游戏开发）
- **Agent 数量**: 21
- **触发词**: 游戏开发/Unity/Unreal/游戏引擎/游戏策划/游戏设计

## 团队架构
| Agent | 角色 | 职责 |
|-------|------|------|
| game-designer | 游戏策划 | 制定玩法机制、数值平衡、关卡设计 |
| narrative-designer | 叙事设计师 | 编写剧情、世界观构建、对话系统设计 |
| level-designer | 关卡设计师 | 设计关卡布局、难度曲线、玩家体验 |
| technical-artist | 技术美术 | 材质贴图、光照、渲染管线优化 |
| unity-architect | Unity 架构师 | Unity 项目架构设计、性能优化 |
| unreal-systems-engineer | Unreal 系统工程师 | Unreal 引擎系统开发、蓝图/C++ |
| blender-addon-engineer | Blender 插件工程师 | 3D 建模工具链开发、DCC 管线 |
| game-audio-engineer | 游戏音频工程师 | 音效设计、音频中间件集成 |
| roblox-experience-designer | Roblox 体验设计师 | Roblox 平台游戏开发 |
| marketing-reddit-community-builder | 社区运营 | 社群建设、玩家反馈收集 |
| quality-assurance | QA 测试 | 功能测试、性能测试、兼容性测试 |（及更多 10 名专家）

## SOP 流程

### Phase 1: 策划阶段
**输入**: 游戏需求概述
**输出**: `game-design-doc.md`
**目的**: 明确游戏定位、核心玩法、目标受众
**步骤**:
1. game-designer 分析需求，制定核心玩法循环
2. narrative-designer 构建世界观和主线剧情
3. 输出游戏设计文档

### Phase 2: 原型验证
**输入**: game-design-doc.md
**输出**: `prototype-report.md`
**目的**: 快速验证核心玩法的可行性
**步骤**:
1. technical-artist 制定美术规范
2. unity-architect 或 unreal-systems-engineer 搭建原型
3. level-designer 设计示范关卡
4. 输出原型验证报告

### Phase 3: 开发执行
**输入**: prototype-report.md
**输出**: 各模块可执行版本
**目的**: 并行开发各功能模块
**步骤**:
1. 引擎团队（Unity/Unreal）并行开发
2. 美术团队（Blender/技术美术）交付资源
3. 音频团队制作音效
4. 输出各模块构建版本

### Phase 4: 测试与发布
**输入**: 各模块构建版本
**输出**: release-candidate.md
**目的**: 确保质量和兼容性
**步骤**:
1. QA 团队执行完整测试用例
2. 社区运营准备发布材料
3. 修复关键 Bug
4. 输出发布候选版本

## 阶段关卡（Phase Gates）
| 关卡 | 通过条件 | 失败处理 |
|------|----------|----------|
| PG1-策划 | GDD 包含核心玩法、目标受众、变现模式 | 返回 Phase 1 补充 |
| PG2-原型 | 核心玩法可玩、性能达到目标帧率 | 优化或调整设计 |
| PG3-开发 | 各模块功能完整无阻断 Bug | 修复阻断 Bug |
| PG4-发布 | QA 通过率 ≥95%，性能达标 | 修复关键问题后重测 |

## 交接协议
### 产出物格式
```yaml
---
team_id: {team_id}
agent_id: game-designer
phase: design
status: done
findings: |
  核心玩法：动作 Roguelike
  目标平台：PC + Switch
  目标帧率：60fps
---
```
### 验收字段
- `phase`：当前完成阶段
- `status`：done/in_progress
- `findings`：核心产出描述
