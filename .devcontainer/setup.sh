#!/bin/bash
# Setup script for ComfoClime development container

set -e

echo "Setting up ComfoClime development environment..."

# Install Home Assistant container tools
container install

# Create custom_components directory in Home Assistant config
mkdir -p /config/custom_components

# Create symbolic link to our custom component
ln -sf /workspaces/comfoclime/custom_components/comfoclime /config/custom_components/comfoclime

# Copy configuration files to Home Assistant config directory
cp /workspaces/comfoclime/.devcontainer/configuration.yaml /config/configuration.yaml
cp /workspaces/comfoclime/.devcontainer/automations.yaml /config/automations.yaml
cp /workspaces/comfoclime/.devcontainer/scripts.yaml /config/scripts.yaml
cp /workspaces/comfoclime/.devcontainer/scenes.yaml /config/scenes.yaml

echo "Setup complete! You can now start Home Assistant with 'container start'"
echo "Home Assistant will be available at http://localhost:8123"
