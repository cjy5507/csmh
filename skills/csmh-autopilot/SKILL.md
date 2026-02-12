---
name: csmh-autopilot
description: End-to-end autonomous flow: plan, execute in parallel, integrate, and verify.
---

# CSMH Autopilot

Use when user gives high-level build goals and wants minimal intervention.

## Phases

1. Expansion
- Convert request into concrete requirements and acceptance tests.

2. Planning
- Create task graph with `depends_on` and `writes`.

3. Execution
- Dispatch with CSMH runtime.

4. QA
- Run build, test, lint, and type checks in `verify`.

5. Final validation
- Ensure all acceptance tests are addressed.

## Runtime Contract

- Persist mission at `.csmh/missions/autopilot.json`.
- Run with: `csmh run .csmh/missions/autopilot.json --report .csmh/reports/autopilot.json`.
- For long cycles, use background execution and `csmh cancel` if needed.

## Guardrails

- Do not skip failed tasks.
- Do not remove tests to pass checks.
- If constraints conflict, pause and ask user.
