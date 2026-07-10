# Handoff 规范

## SELF_CHECK Schema

```json
{
  "task_id": "string (必填)",
  "result": "PASS | PARTIAL | FAIL (必填)",
  "confidence": "number 0.0-1.0 (必填)",
  "criteria_results": [
    {"criterion": "string", "met": true, "evidence": "string"}
  ],
  "summary": "string"
}
```

## 传递字段
- task_id / from / to / phase
- 交付物（最终输出）+ SELF_CHECK
- 验收标准达成情况

## 不传递字段（隐藏推理链）
- ❌ Builder 的中间推理过程
- ❌ Builder 遇到的困难或排除的方案
