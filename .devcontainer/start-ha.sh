#!/bin/bash
# Quick script to start Home Assistant in the dev container

CONFIG_DIR="/workspaces/comfoclime/.devcontainer/ha-config"

echo "Starting Home Assistant..."
echo "Configuration: $CONFIG_DIR"
echo "Web UI: http://localhost:8123"
echo ""
echo "Press Ctrl+C to stop Home Assistant"
echo ""

python3.13 -m homeassistant -c "$CONFIG_DIR"
