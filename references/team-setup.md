# 团队设置指南（Team Setup，v3.1）

## 团队定义（单一事实源）
- 团队唯一清单：`references/workbuddy-experts/_index.md`（39 团队）
- agents 计数：实装 199（agents/*.md 实测） / 计划 260（11 个新建团队 stub 补齐后，未实装）

## 新增团队流程
1. 在 `references/workbuddy-experts/` 下新建 `<team>/plugin.json` + `agents/*.md`
2. 更新 `_index.md` 团队表与 README 一览表
3. 运行 `tests/test_file_health.py` 与 `tests/check_references.py` 验证

## 角色与成员约定
- 每团队默认 1 主理人 + 按需 agents；stub 团队在 `_index.md` 标注「待补充成员」

## 校验
- `python tests/run_smoke.py`；`python tests/check_references.py`
- 新增/修改后必须 UTF-8 编码、多行格式（防单行拼接损坏）
