#!/bin/bash
# Setup script for Homebox Backup GUI
# Creates a uv virtual environment and installs dependencies

set -e

echo "Setting up Homebox Backup GUI..."
echo

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "Error: 'uv' is not installed."
    echo "Please install uv first: https://github.com/astral-sh/uv"
    echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment with uv..."
    uv venv
    echo
fi

# Install dependencies
echo "Installing dependencies..."
uv pip install -r requirements.txt
echo

echo "Setup complete!"
echo
echo "To run the application, use:"
echo "  ./run.sh"
echo
echo "Or activate the virtual environment manually:"
echo "  source .venv/bin/activate"
echo "  python homebox_backup_gui.py"
