#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-parallel}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -f "$SCRIPT_DIR/csmh-orchestrator.py" ]]; then
  RUNTIME_ROOT="$SCRIPT_DIR"
elif [[ -f "$SCRIPT_DIR/../scripts/csmh-orchestrator.py" ]]; then
  RUNTIME_ROOT="$(cd "$SCRIPT_DIR/../scripts" && pwd)"
else
  echo "could not locate csmh-orchestrator.py"
  exit 1
fi

if [[ -f "$SCRIPT_DIR/../templates/mission.parallel.json" ]]; then
  TEMPLATE_FILE="$(cd "$SCRIPT_DIR/../templates" && pwd)/mission.parallel.json"
elif [[ -f "$RUNTIME_ROOT/templates/mission.parallel.json" ]]; then
  TEMPLATE_FILE="$RUNTIME_ROOT/templates/mission.parallel.json"
else
  TEMPLATE_FILE=""
fi

if [[ "$MODE" != "parallel" ]]; then
  echo "unsupported verify mode: $MODE"
  echo "supported: parallel"
  exit 2
fi

if [[ -z "$TEMPLATE_FILE" || ! -f "$TEMPLATE_FILE" ]]; then
  echo "missing template mission.parallel.json"
  exit 1
fi

echo "== CSMH parallel verification =="
mkdir -p ".csmh/reports"

REPORT=".csmh/reports/verify-report.json"
/usr/bin/time -p python3 "$RUNTIME_ROOT/csmh-orchestrator.py" \
  "$TEMPLATE_FILE" \
  --report "$REPORT"

echo "== summary =="
python3 - "$REPORT" << 'PY'
import json
import sys
from pathlib import Path

report_path = Path(sys.argv[1])
report = json.loads(report_path.read_text())
status = report["status"]
duration = report["duration_sec"]
print(f"status={status}")
print(f"duration_sec={duration}")
print(f"failed_or_blocked={report['failed_or_blocked']}")
PY

echo "verification complete"
