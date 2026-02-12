---
name: csmh-verify
description: Verify CSMH runtime behavior, especially dependency-aware parallel execution.
---

# CSMH Verify

Run this skill after install or major changes.

## Command

```bash
csmh verify parallel
```

## What It Verifies

- Parallel dispatch for independent tasks
- Dependency ordering for downstream task
- Integration and verification phase execution
- JSON report generation

## Pass Conditions

- Exit code `0`
- Report status is `succeeded`
- No failed or blocked tasks
