# 专家合并历史（merge-history.md · P6 版本化/血缘）

> 每次合并动作记录：{date, phase, action, scope, gate 结果, commit}。回滚 = git revert 对应 commit + registry 回退。
> 规则：合并动作必须过 eval-gate（P7）；未过即撤销并在此记录撤销。

## 2026-08-16

| commit | phase | action | scope | gate 结果 |
|--------|-------|--------|-------|----------|
| e319d7b | P1 | 占位 id 语义化（56 member-N → slug，11 团全文替换） | workbuddy-experts 11 团 agents+plugin.json | P1 三向校验 ALL PASS；check_agent_completeness 67/67；check_team_consistency ✓ |
| f3f7d62 | P0 | plugin.json 邮箱脱敏（5 处） | 5 团 plugin.json | 扫描 0 残留 |
| a7c98f2 | P2-P7 准备 | 指纹工具 + eval 门禁套件 + merge-history 建立 | scripts/tests/references | eval 基线 45%→72.7%（域限域修正后） |

## P2-P7 实施（TC-20260816-9 · 审计修正后）

| 阶段 | action | 裁决/门禁 |
|------|--------|----------|
| P3 | expert-fingerprint v2（TF-IDF cosine + 停用词）→ fingerprint-report.json | 分布校准：最高 0.80；阈值 0.5 命中 2 对 |
| P2 | 共享裁决：fundamentals-analyst 对（desc 0.80）**半共享**——_shared/ 建角色定义规范，**不物理薄壳**（正文工具链团差异大，硬薄壳损失>收益）；competitive 对（0.65）记录待定 | check-shared-refs 校验器建立；eval-gate 无回归 |
| P4 | domain-map.json（13 categoryId → 10 组，40 团全覆盖）+ _domain/ 10 入口 + SKILL.md §8.1 集成 | 覆盖核对 missing=[] extra=[] |
| P5 | matcher --domain 域限域（既有能力，eval-gate 已用） | 基线 72.7% 即为域限域模式验证 |
| P6 | 本表（merge-history）+ 回滚 SOP：git revert 对应 commit | — |
| P7 | eval-gate 套件（20 正例 + 2 负例）+ 基线 72.7%（负例 2/2 正确拒绝） | 合并前后对比，下降 >5% 撤销 |

## 待记录（后续）

- P2 若老板裁决 competitive 对共享
- 任何未来合并动作
