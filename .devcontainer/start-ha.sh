#!/bin/bash
# Quick script to start Home Assistant in the dev container or locally

# Determine the project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Ensure user's local bin is on PATH so `uv` is discoverable
export PATH="$HOME/.local/bin:$PATH"

# Check if we're in a Dev Container or local environment
if [ -d "/workspaces/comfoclime" ]; then
  WORKSPACE_ROOT="/workspaces/comfoclime"
else
  WORKSPACE_ROOT="$PROJECT_ROOT"
fi

CONFIG_DIR="$WORKSPACE_ROOT/.devcontainer/ha-config"

echo "Starting Home Assistant..."
echo "Configuration: $CONFIG_DIR"
echo "Web UI: http://localhost:8123"
echo ""
echo "Press Ctrl+C to stop Home Assistant"
echo ""

cd "$WORKSPACE_ROOT"
if ! command -v uv &> /dev/null; then
  echo "Error: 'uv' not found in PATH." >&2
  echo "Run .devcontainer/setup.sh to install dependencies or add ~/.local/bin to your PATH." >&2
  echo "If you installed via Snap/VSCode, run the env script suggested by the editor." >&2
  exit 1
fi

uv run python -m homeassistant -c "$CONFIG_DIR"
