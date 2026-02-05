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
VENV_DIR="$WORKSPACE_ROOT/.venv"

# Activate virtual environment if it exists
if [ -d "$VENV_DIR" ]; then
  echo "Activating virtual environment..."
  source "$VENV_DIR/bin/activate"
fi

echo "Starting Home Assistant..."
echo "Configuration: $CONFIG_DIR"
echo "Web UI: http://localhost:8123"
echo ""
echo "Press Ctrl+C to stop Home Assistant"
echo ""

python3 -m homeassistant -c "$CONFIG_DIR"
