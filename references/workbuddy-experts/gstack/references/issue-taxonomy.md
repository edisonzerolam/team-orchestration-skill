# 缺陷/问题分类法（issue-taxonomy）

> 本文件为 gstack 团队的本地镜像，源自 qa skill 的缺陷分类法（references/issue-taxonomy.md）。
> 作为配套知识模板，供 QA 子智能体在 "Collect issues" 阶段对问题进行分类。

## 按类型（Type）

| 类别 | 说明 |
|------|------|
| 功能缺陷（Functional） | 需求/设计预期行为未实现或错误 |
| 性能（Performance） | 响应慢、卡顿、资源占用过高 |
| 安全（Security） | 越权、注入、敏感信息泄露 |
| 兼容性（Compatibility） | 浏览器/设备/版本适配问题 |
| 界面/UX（UI） | 布局错乱、交互不友好 |
| 数据（Data） | 数据丢失、错误、一致性 |
| 稳定性（Stability） | 崩溃、死锁、内存泄漏 |
| 文档/配置（Docs/Config） | 文档缺失、配置错误 |

## 按严重度（Severity）

| 等级 | 定义 |
|------|------|
| Blocker | 系统不可用，阻塞主线 |
| Critical | 核心功能损坏，无绕过方案 |
| Major | 主要功能量损，有勉强绕过方案 |
| Minor | 次要问题，影响体验 |
| Trivial | 文案/样式等微小瑕疵 |

## 按优先级（Priority）

- P0 立即处理 / P1 本周 / P2 下个迭代 / P3 待定

> 注：分类标准以团队实际 qa 规范为准，本模板供快速归类使用。
