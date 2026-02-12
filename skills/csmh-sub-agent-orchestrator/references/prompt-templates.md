# Prompt Templates

## Coordinator Kickoff

```text
Role: Coordinator
Mission:
Constraints:
Deadline:
Acceptance tests:
Non-goals:

Shared context:
- ...

Task graph:
- id:
  role:
  objective:
  depends_on:
  outputs:
  done_criteria:

Mode: fast | balanced | strict
Max parallel branches:
Escalation rule:
```

## Specialist Task

```text
Role: Specialist
Task id:
Objective:
Allowed inputs:
Required output schema:
Done criteria:
Timebox:

Rules:
- Work only on this task.
- Do not modify out-of-scope artifacts.
- Report assumptions and confidence (0.0-1.0).
- If blocked, return a concise blocker report.
```

## Integrator Gate

```text
Role: Integrator
Inputs:
- Branch outputs by task id

Merge goal:
Conflict resolution precedence:
1) User constraints
2) Architecture and safety constraints
3) Branch evidence

Output format:
- Merged artifact
- Conflict log
- Assumptions
```

## Verifier Gate

```text
Role: Verifier
Artifact under test:
Acceptance tests:
Regression checks:
Policy checks:

Return:
- PASS or FAIL
- Failing sections only
- Minimal fix instructions
```
