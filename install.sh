#!/usr/bin/env bash
set -euo pipefail

REPO_URL="https://github.com/cjy5507/csmh.git"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
CSMH_HOME="$CODEX_HOME/csmh"
SKILLS_DIR="$CODEX_HOME/skills"
BIN_DIR="$CODEX_HOME/bin"
USER_BIN_DIR="${HOME}/.local/bin"

print_step() {
  echo "[csmh] $1"
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "error: required command not found: $1"
    exit 1
  fi
}

resolve_source() {
  if [[ -f "$SCRIPT_DIR/scripts/csmh" && -d "$SCRIPT_DIR/skills" ]]; then
    echo "$SCRIPT_DIR"
    return 0
  fi

  require_cmd git
  local tmp
  tmp="$(mktemp -d)"
  print_step "cloning $REPO_URL"
  git clone --depth 1 "$REPO_URL" "$tmp/csmh" >/dev/null 2>&1
  echo "$tmp/csmh"
}

main() {
  require_cmd bash
  require_cmd python3

  local src
  src="$(resolve_source)"

  print_step "install target: $CODEX_HOME"
  mkdir -p "$CSMH_HOME" "$SKILLS_DIR" "$BIN_DIR" "$USER_BIN_DIR"

  print_step "installing runtime"
  cp -f "$src/scripts/csmh-orchestrator.py" "$CSMH_HOME/csmh-orchestrator.py"
  cp -f "$src/scripts/csmh-verify.sh" "$CSMH_HOME/csmh-verify.sh"
  cp -f "$src/scripts/csmh.py" "$CSMH_HOME/csmh.py"
  cp -f "$src/VERSION" "$CSMH_HOME/VERSION"
  chmod +x "$CSMH_HOME/csmh-orchestrator.py" "$CSMH_HOME/csmh-verify.sh" "$CSMH_HOME/csmh.py"

  print_step "installing templates"
  mkdir -p "$CSMH_HOME/templates"
  cp -f "$src/templates/"*.json "$CSMH_HOME/templates/"

  print_step "installing skills"
  find "$src/skills" -mindepth 1 -maxdepth 1 -type d | while read -r skill_dir; do
    skill_name="$(basename "$skill_dir")"
    target="$SKILLS_DIR/$skill_name"
    mkdir -p "$target"
    cp -R "$skill_dir/"* "$target/"
  done

  print_step "installing csmh command"
  cat > "$BIN_DIR/csmh" <<EOF
#!/usr/bin/env bash
set -euo pipefail
exec python3 "$CSMH_HOME/csmh.py" "\$@"
EOF
  chmod +x "$BIN_DIR/csmh"
  ln -sf "$BIN_DIR/csmh" "$USER_BIN_DIR/csmh"

  print_step "done"
  echo "- command: $USER_BIN_DIR/csmh"
  echo "- skills: $SKILLS_DIR/csmh-*"
  echo "- runtime: $CSMH_HOME"
  echo ""
  if ! echo "$PATH" | tr ':' '\n' | grep -qx "$USER_BIN_DIR"; then
    echo "add to PATH if needed:"
    echo "  export PATH=\"$USER_BIN_DIR:\$PATH\""
  fi

  echo "quick check:"
  echo "  csmh version"
  echo "  csmh init"
  echo "  csmh verify parallel"
}

main "$@"
