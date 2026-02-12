#!/usr/bin/env bash
set -euo pipefail

CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
CSMH_HOME="$CODEX_HOME/csmh"
SKILLS_DIR="$CODEX_HOME/skills"
BIN_DIR="$CODEX_HOME/bin"
USER_BIN_DIR="$HOME/.local/bin"

rm -rf "$CSMH_HOME"
rm -rf "$SKILLS_DIR"/csmh-*
rm -f "$BIN_DIR/csmh"
rm -f "$USER_BIN_DIR/csmh"

echo "csmh uninstalled from $CODEX_HOME"
