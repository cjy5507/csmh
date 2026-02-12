# Execution Checklist

## 1) Intake

- Confirm objective and success criteria.
- Confirm constraints and boundaries.
- Confirm stop condition.

## 2) Decomposition

- Build atomic tasks with ownership.
- Define `depends_on` for each task.
- Define `writes` for collision prevention.
- Set max concurrency.

## 3) Dispatch

- Start dependency-free tasks first.
- Track pending/running/completed states.
- Enforce timebox and retry policy.

## 4) Integration

- Normalize task outputs.
- Merge with precedence rules.
- Record unresolved conflicts.

## 5) Verification

- Run acceptance tests.
- Run regression checks.
- Route only failures for rework.

## 6) Delivery

- Provide final artifact.
- Summarize key changes.
- List open risks and deferred items.
