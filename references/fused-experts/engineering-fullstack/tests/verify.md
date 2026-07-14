# Verify: engineering-fullstack

## must-pass (all required)

| # | Scenario | Input | Expected Mode |
|---|---------|-------|---------------|
| 1 | React data table with virtual scrolling | "Design a virtual scrolling table component" | frontend |
| 2 | Database schema for e-commerce | "Design order table schema for e-commerce" | backend |
| 3 | REST API design | "Design CRUD API for product service" | api |
| 4 | Production monitoring config | "Configure alert rules for production" | sre |
| 5 | Full-stack architecture | "Design real-time chat app architecture" | fullstack |
| 6 | Cross-layer optimization | "Home page is too slow, what to do" | fullstack |

## should-pass (>=2 required)

| # | Scenario | Expected Behavior |
|---|---------|------------------|
| 7 | Pure frontend question should not include backend deployment advice | Mode stays correct |
| 8 | Mode switching preserves context | Continuity across mode switch |
| 9 | Shared methods only output once | No duplication |

## must-not-fail (0 allowed)

| # | Degradation | Check |
|---|-------------|-------|
| 10 | Lost specific capability from source | Randomly sample 3 source instructions |
| 11 | Contradictory advice across modes | Cross-check mode constraints |
