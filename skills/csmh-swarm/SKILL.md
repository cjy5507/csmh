---
name: csmh-swarm
description: Shared-task-pool parallel mode for large sets of similar independent tasks.
---

# CSMH Swarm

Use when there are many similar tasks (for example, fixing many lint errors).

## Protocol

1. Build a task pool mission where each task is independent.
2. Use `max_concurrency` 4 to 6.
3. Keep each task small and file-scoped.
4. Add a final integration and verification step.

## Example

- Task IDs: `fix-001`, `fix-002`, `fix-003`...
- Each task writes only one file path in `writes`.
- Run with `csmh run` and monitor report.

## Exit Criteria

- All swarm tasks succeeded.
- Verify phase succeeded.
- No blocked tasks due to write collisions.
