#!/bin/bash
# Setup script for ComfoClime development container

set -e

echo "Setting up ComfoClime development environment..."

# Install system dependencies
echo "Installing system dependencies..."
sudo apt-get update -qq
sudo apt-get install -y libpcap-dev

# Determine config directory
if [ -d "/config" ]; then
  CONFIG_DIR="/config"
else
  # Use workspace-local config directory for non-HA containers
  CONFIG_DIR="/workspaces/comfoclime/.devcontainer/ha-config"
  mkdir -p "$CONFIG_DIR"
  echo "Using local config directory: $CONFIG_DIR"
fi

# Create custom_components directory in Home Assistant config
mkdir -p "$CONFIG_DIR/custom_components"

# Create symbolic link to our custom component
ln -sf /workspaces/comfoclime/custom_components/comfoclime "$CONFIG_DIR/custom_components/comfoclime"

# Copy configuration files to Home Assistant config directory
cp /workspaces/comfoclime/.devcontainer/configuration.yaml "$CONFIG_DIR/configuration.yaml"
cp /workspaces/comfoclime/.devcontainer/automations.yaml "$CONFIG_DIR/automations.yaml"
cp /workspaces/comfoclime/.devcontainer/scripts.yaml "$CONFIG_DIR/scripts.yaml"
cp /workspaces/comfoclime/.devcontainer/scenes.yaml "$CONFIG_DIR/scenes.yaml"

# Install Home Assistant if not already present
if ! command -v hass &> /dev/null; then
  echo "Installing Home Assistant Core..."
  python3.13 -m pip install --upgrade homeassistant
else
  echo "Home Assistant already installed: $(hass --version 2>/dev/null || echo 'version unknown')"
fi

echo ""
echo "Setup complete!"
echo "Configuration directory: $CONFIG_DIR"
echo ""
echo "To start Home Assistant, run:"
echo "  hass -c $CONFIG_DIR"
echo ""
echo "Home Assistant will be available at http://localhost:8123"
