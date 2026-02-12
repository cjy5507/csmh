---
name: csmh-init
description: Initialize local CSMH workspace directories and baseline config.
---

# CSMH Init

Use at project start to initialize CSMH state.

## Command

```bash
csmh init
```

## Expected Structure

- `.csmh/state`
- `.csmh/missions`
- `.csmh/reports`
- `.csmh/logs`
- `.csmh/locks`
- `.csmh/config.json`

## Notes

- Safe to rerun; it is idempotent.
