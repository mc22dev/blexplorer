#!/bin/bash
set -e # Exit immediately if a command exits with a non-zero status.

VENV_DIR="venv"

# Create a virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

# Install dependencies using the venv's pip
echo "Installing dependencies..."
"$VENV_DIR/bin/pip" install -r requirements.txt

# Run the application using the venv's python
echo "Launching BLE Scanner..."
"$VENV_DIR/bin/python" main.py
