---
name: csmh-cancel
description: Stop active background CSMH mission and clean stale state.
---

# CSMH Cancel

Use when user asks to stop current CSMH execution.

## Steps

1. Run `csmh cancel`.
2. Confirm `.csmh/state/active.pid` is removed.
3. Report that background execution is stopped.

## Recovery

- If no active pid exists, report no-op.
- If mission was interrupted, inspect `.csmh/logs/active.log` and `.csmh/reports/`.
