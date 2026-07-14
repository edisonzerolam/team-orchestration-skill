# Verify: engineering-ai

## must-pass

| # | Scenario | Input | Expected Mode |
|---|---------|-------|---------------|
| 1 | ML model deployment | "Deploy a fine-tuned LLM to production" | ml |
| 2 | Prompt design | "Design a system prompt for customer support bot" | prompt |
| 3 | Multi-agent topology | "Design agent topology for order processing" | mas |
| 4 | A/B test framework | "Set up A/B testing for AI features" | auto-opt |
| 5 | RAG pipeline | "Build a RAG pipeline for internal docs" | ml |

## should-pass (>=3)

| # | Scenario | Expected |
|---|---------|----------|
| 6 | Voice AI should mention STT/TTS providers | voice mode accurate |
| 7 | Email discussion should include compliance | email mode accurate |
| 8 | Prompt injection defense should be mentioned | prompt mode complete |

## must-not-fail

| # | Check |
|---|-------|
| 9 | Lost MLOps knowledge from ai-engineer source |
| 10 | Lost multi-agent topology patterns from mas source |
