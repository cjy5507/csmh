---
name: csmh-ultrawork
description: Maximum-throughput parallel execution mode for independent tasks using CSMH mission files.
---

# CSMH Ultrawork

Use when user asks for "fast", "parallel", "ultrawork", or mass multi-file work.

## Rules

- Decompose into independent tasks first.
- Use `mode: fast` or `mode: balanced`.
- Use `max_concurrency` 4 to 6 by default.
- Never run tasks in parallel if they share the same `writes` target.
- Run verify gates before completion.

## Execution

1. Initialize project folders with `csmh init`.
2. Build mission JSON under `.csmh/missions/`.
3. Execute: `csmh run .csmh/missions/<name>.json --report .csmh/reports/<name>.json`.
4. If long-running: `csmh start ...` and track `.csmh/logs/active.log`.

## Completion Criteria

- Report status is `succeeded`.
- `failed_or_blocked` is empty.
- Verification phase passed.
