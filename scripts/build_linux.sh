#!/bin/bash
set -e

# Define the temporary directory for build artifacts
TMP_DIR="tmp"

# Create a temporary directory for the build, if it doesn't exist
if [ ! -d "$TMP_DIR" ]; then
    mkdir -p "$TMP_DIR"
fi

# Create a virtual environment, if it doesn't exist
if [ ! -d "$TMP_DIR/venv" ]; then
    python3 -m venv "$TMP_DIR/venv"
fi

# Activate the virtual environment
# A subshell is used to limit the scope of the activation
. "$TMP_DIR/venv/bin/activate"

# Install or upgrade dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Run PyInstaller to build the application
# The output will be in tmp/dist/BLEScanner and the intermediate files in tmp/build
pyinstaller blescanner.spec --distpath "$TMP_DIR/dist" --workpath "$TMP_DIR/build" --noconfirm

echo "Build complete. The executable is located in $TMP_DIR/dist/BLEScanner/blescanner"
