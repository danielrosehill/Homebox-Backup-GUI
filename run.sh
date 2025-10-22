#!/bin/bash
# Run script for Homebox Backup GUI
# Activates the virtual environment and runs the application

set -e

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Virtual environment not found!"
    echo "Please run setup first:"
    echo "  ./setup.sh"
    exit 1
fi

# Activate virtual environment and run the application
echo "Starting Homebox Backup GUI..."
source .venv/bin/activate
python homebox_backup_gui.py
