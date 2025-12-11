#!/bin/bash
set -e

# --- Configuration ---
# This script assumes you have installed a Windows version of Python 3.9
# into the default location in your default Wine prefix.
# You may need to adjust this path if your setup is different.
WINE_PYTHON_PATH="$HOME/.wine/drive_c/users/$USER/AppData/Local/Programs/Python/Python39"
WINE_PYTHON_EXE="$WINE_PYTHON_PATH/python.exe"
WINE_PYINSTALLER_EXE="$WINE_PYTHON_PATH/Scripts/pyinstaller.exe"

# --- Prerequisite Checks ---

# 1. Check for Wine
if ! command -v wine &> /dev/null; then
    echo "Error: 'wine' command not found."
    echo "Please install Wine for your Linux distribution."
    echo "e.g., on Debian/Ubuntu: sudo apt install wine"
    exit 1
fi

# 2. Check for Windows Python in Wine
if [ ! -f "$WINE_PYTHON_EXE" ]; then
    echo "Error: Windows Python executable not found at '$WINE_PYTHON_EXE'."
    echo "Please download the official Python installer for Windows (e.g., Python 3.9) and run it with Wine:"
    echo "  wine python-3.9.X-amd64.exe"
    echo "Ensure you install it for the current user to the default location."
    exit 1
fi

echo "--- Found Wine and Windows Python installation. ---"
echo "Using Python from: $WINE_PYTHON_EXE"

# --- Build Process ---

echo "--- Installing dependencies in Wine environment... ---"
wine "$WINE_PYTHON_EXE" -m pip install -r requirements.txt

echo "--- Building Windows executable with PyInstaller (via Wine)... ---"
wine "$WINE_PYINSTALLER_EXE" blescanner.spec --noconfirm

echo "--- Build complete! ---"
echo "The executable can be found in the 'dist/BLEScanner' directory."
