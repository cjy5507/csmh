---
name: csmh-sub-agent-orchestrator
description: Coordinate complex work with dependency-aware parallel execution, integration, and verification gates using the CSMH runtime.
---

# CSMH Sub-Agent Orchestrator

Use this skill when the user asks for parallel specialists, orchestration, role-based execution, or merge+verify workflows.

## Workflow

1. Define mission contract.
- Objective
- Constraints
- Acceptance tests
- Non-goals

2. Build task graph.
- Split into atomic tasks
- Add explicit `depends_on`
- Set `writes` to avoid concurrent collisions

3. Dispatch with CSMH.
- Use `csmh run <mission.json>`
- Prefer `mode: balanced`
- Keep `max_concurrency` in 3 to 6 unless user requests otherwise

4. Integrate and verify.
- Put merge command in `integrate`
- Put checks in `verify`

5. Report outcome.
- Include passed/failed tasks
- Include unresolved risks

## Mission Template

Use this JSON skeleton:

```json
{
  "objective": "...",
  "mode": "balanced",
  "max_concurrency": 4,
  "default_timeout_sec": 300,
  "default_retries": 1,
  "tasks": [
    {
      "id": "task-id",
      "command": "shell command",
      "depends_on": [],
      "writes": ["path-or-logical-target"]
    }
  ],
  "integrate": {
    "command": "optional merge command"
  },
  "verify": {
    "command": "optional verification command"
  }
}
```

## References

- `references/prompt-templates.md`
- `references/execution-checklist.md`
