# prime-agent 吸收：A/B/C 改进方案（TC-20260816-10）

## 目标与验收条件

### A 执行核心不可变契约
- 目标：SKILL.md 执行核心区（§1-§7.3）改为不可变基准，改进走 references/ 增量
- 验收：1) §0 新增“执行核心区界定 + 改动三前置”条款 2) merge-history.md 记录 A 契约本身 3) 任一核心区改动可验证过三前置

### B 质量门语义边界
- 目标：明文 eval-gate / token_budget 通过≠方案正确/交付达标
- 验收：§7 新增 gate 语义边界条款；eval-gate 文档标注“只验证召回未退化”

### C 成员状态写权限
- 目标：子代理可落盘产物，但案卷元状态仅 main 写入
- 验收：§4.0 新增状态写权限条款

## 同类技能调研节

### Claude Code CLAUDE.md 版本治理
- 三级层次：项目根→用户主→企业级，核心指令锚定在项目根 CLAUDE.md（不可下级覆盖）
- 扩展通过 @commands 或独立 .md 文件叠加，不改写基线

### 多框架状态所有权
- LangGraph：Central + Reducer 模式（专家意见可作 update 合并到共享 State）
- CrewAI：checkpoint/resume（Crew.from_checkpoint继续）
- AutoGen：Hybrid（Team 共享 + Agent 自持）

### 自改进实践
- 不可变基线 + 增量补丁合范
- checkpoint 快照自动保存+复呼（无需手动 git tag）

### 质量门三层分离
- 准入门（blocking）：格式/token/角色检查
- 质量门（non-blocking）：论证逻辑/8bc1据充分性
- 完成门（judgment）：用户需求满足度评估

### 启示
- A：核心可不变与早期 Claude Code 三级收敛式治理对形
- B：质量门三层分离提供精确语义：观察到 eval/eval-gate 未显式声明边界是一个真实缺口
## 实施顺序
A§0 → B§7 → C§4.0 → merge-history → eval-gate 验证 → 提交
