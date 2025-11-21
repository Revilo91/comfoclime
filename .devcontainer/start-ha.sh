#!/bin/bash
# Quick script to start Home Assistant in the dev container

CONFIG_DIR="/workspaces/comfoclime/.devcontainer/ha-config"

# Clean up Python bytecode cache to ensure fresh code loads
echo "Cleaning Python bytecode cache..."
find /workspaces/comfoclime -type f -name "*.pyc" -delete
find /workspaces/comfoclime -type d -name "__pycache__" -delete
echo "Cache cleaned."
echo ""

echo "Starting Home Assistant..."
echo "Configuration: $CONFIG_DIR"
echo "Web UI: http://localhost:8123"
echo ""
echo "Press Ctrl+C to stop Home Assistant"
echo ""

python3.13 -m homeassistant -c "$CONFIG_DIR"
