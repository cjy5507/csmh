# CSMH (Codex Smart Multi-agent Hub)

CSMH is a Codex-native orchestration plugin pack inspired by SMH.

It provides:
- Dependency-aware parallel orchestration runtime
- Codex skill pack (`csmh-*`) for autopilot/ultrawork/swarm workflows
- Cross-machine installer for macOS/Linux and Windows

## What You Get

- Runtime engine: `csmh-orchestrator.py`
- CLI: `csmh`
- Skill pack:
  - `csmh-sub-agent-orchestrator`
  - `csmh-autopilot`
  - `csmh-ultrawork`
  - `csmh-swarm`
  - `csmh-cancel`
  - `csmh-init`
  - `csmh-verify`

## Install

### macOS / Linux

```bash
git clone https://github.com/cjy5507/csmh.git
cd csmh
bash install.sh
```

### Windows (PowerShell)

```powershell
git clone https://github.com/cjy5507/csmh.git
cd csmh
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

Installer target defaults to `$CODEX_HOME` or `~/.codex`.

## Uninstall

### macOS / Linux

```bash
bash uninstall.sh
```

### Windows

```powershell
powershell -ExecutionPolicy Bypass -File .\uninstall.ps1
```

## Quick Start

```bash
csmh version
csmh init
csmh verify parallel
```

Run a mission:

```bash
csmh run ~/.codex/csmh/templates/mission.parallel.json --report .csmh/reports/parallel.json
```

Run in background:

```bash
csmh start ~/.codex/csmh/templates/mission.parallel.json
csmh cancel
```

## Mission Format

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
      "writes": ["path-or-logical-target"],
      "timeout_sec": 120,
      "retries": 1
    }
  ],
  "integrate": { "command": "optional" },
  "verify": { "command": "optional" }
}
```

`writes` collision keys are path-normalized internally. If you need non-path lock keys, use `logical:<name>` (for example, `logical:db-users`).

## Security Model

- Mission `command` is executed with shell semantics (`shell=True`), by design.
- Treat mission files as trusted code. Do not run untrusted mission JSON.
- If sharing missions across machines, review `command` lines before execution.

## How This Maps From SMH

- Claude `Task(..., run_in_background=True)` patterns are replaced by mission graph execution in `csmh run`.
- Claude hooks are replaced by explicit Codex skills + runtime commands.
- Memory/extension layers can be added later via MCP server integration.

## Project Layout

- `scripts/`: runtime and CLI
- `skills/`: Codex skill pack
- `templates/`: starter mission JSON files
- `install.sh`, `install.ps1`: cross-machine setup

## License

MIT
