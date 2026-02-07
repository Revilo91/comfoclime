#!/bin/bash
# Quick script to start Home Assistant in the dev container or locally

# Determine the project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

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
uv run python -m homeassistant -c "$CONFIG_DIR"
