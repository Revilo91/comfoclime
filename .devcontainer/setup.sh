#!/bin/bash
# Setup script for ComfoClime development container and local development

set -e

echo "Setting up ComfoClime development environment..."

# Determine the project root directory (works in both Dev Container and local)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "Project root: $PROJECT_ROOT"

# Check if we're in a Dev Container or local environment
if [ -d "/workspaces/comfoclime" ]; then
  WORKSPACE_ROOT="/workspaces/comfoclime"
else
  WORKSPACE_ROOT="$PROJECT_ROOT"
fi

echo "Workspace root: $WORKSPACE_ROOT"

# Ensure user's local bin is on PATH so tools like `uv` are discoverable
export PATH="$HOME/.local/bin:$PATH"

# Skip system dependencies installation if not needed or in local environment
if command -v apt-get &> /dev/null && [ -w /etc ]; then
  echo "Installing system dependencies..."
  sudo apt-get update -qq
  sudo apt-get install -y build-essential python3 python3-dev libpcap-dev
else
  echo "Skipping system dependencies (not running as root or apt not available)"
fi

# Install uv if not already available
if ! command -v uv &> /dev/null; then
  echo "Installing uv..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
fi

echo "uv version: $(uv --version)"

# Create virtual environment and install dependencies
cd "$WORKSPACE_ROOT"
echo "Syncing dependencies with uv..."

# Verify presence of Python C headers required for building some dependencies
check_python_headers() {
  if python3 - <<'PY' 2>/dev/null
import sysconfig, os
inc = sysconfig.get_paths().get("include")
print(os.path.exists(os.path.join(inc or "", "Python.h")))
PY
  then
    return 0
  fi
  echo "\nERROR: Python C headers not found (Python.h)." >&2
  if command -v apt-get &> /dev/null; then
    if [ "$(id -u)" -eq 0 ]; then
      echo "Attempting to install build dependencies (apt)..."
      apt-get update -qq
      apt-get install -y build-essential python3-dev || true
      # Re-check
      if python3 - <<'PY' 2>/dev/null
import sysconfig, os
inc = sysconfig.get_paths().get("include")
print(os.path.exists(os.path.join(inc or "", "Python.h")))
PY
      then
        return 0
      fi
    else
      echo "Please install the Python development headers and build tools." >&2
      echo "On Debian/Ubuntu run:" >&2
      echo "  sudo apt-get update && sudo apt-get install -y build-essential python3-dev" >&2
      exit 1
    fi
  else
    echo "Unable to automatically install build dependencies on this system." >&2
    echo "Install the Python dev headers and a C compiler for your distribution." >&2
    exit 1
  fi
}

check_python_headers

uv sync

VENV_DIR="$WORKSPACE_ROOT/.venv"

# Determine config directory
if [ -d "/config" ]; then
  CONFIG_DIR="/config"
else
  # Use workspace-local config directory for non-HA containers and local dev
  CONFIG_DIR="$WORKSPACE_ROOT/.devcontainer/ha-config"
  mkdir -p "$CONFIG_DIR"
  echo "Using local config directory: $CONFIG_DIR"
fi

# Create custom_components directory in Home Assistant config
mkdir -p "$CONFIG_DIR/custom_components"

# Remove existing symlink if present to avoid recursion
rm -f "$CONFIG_DIR/custom_components/comfoclime"

# Create symbolic link to our custom component
ln -s "$WORKSPACE_ROOT/custom_components/comfoclime" "$CONFIG_DIR/custom_components/comfoclime"

# Copy configuration files to Home Assistant config directory
cp "$WORKSPACE_ROOT/.devcontainer/configuration.yaml" "$CONFIG_DIR/configuration.yaml"
cp "$WORKSPACE_ROOT/.devcontainer/automations.yaml" "$CONFIG_DIR/automations.yaml"
cp "$WORKSPACE_ROOT/.devcontainer/scripts.yaml" "$CONFIG_DIR/scripts.yaml"
cp "$WORKSPACE_ROOT/.devcontainer/scenes.yaml" "$CONFIG_DIR/scenes.yaml"

# Verify Home Assistant is installed
HA_VERSION=$(uv run python -c "from importlib.metadata import version; print(version('homeassistant'))" 2>/dev/null || echo "")
if [ -n "$HA_VERSION" ]; then
  echo "Home Assistant installed: $HA_VERSION"
else
  echo "Warning: Home Assistant not found. Run 'uv sync' to install dependencies."
fi

echo ""
echo "=========================================="
echo "Setup complete!"
echo "=========================================="
echo "Configuration directory: $CONFIG_DIR"
echo "Virtual environment: $VENV_DIR"
echo ""
echo "To start Home Assistant, run:"
echo "  source $VENV_DIR/bin/activate"
echo "  python3 -m homeassistant -c $CONFIG_DIR"
echo ""
echo "Or use the start script:"
echo "  $WORKSPACE_ROOT/.devcontainer/start-ha.sh"
echo ""
echo "Home Assistant will be available at http://localhost:8123"
