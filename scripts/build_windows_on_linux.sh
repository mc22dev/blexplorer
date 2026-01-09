#!/bin/bash
set -e

# --- Configuration ---
export WINEPREFIX="$PWD/tmp/.wine"
export WINEARCH=win64
PYTHON_VERSION="3.9.13"
PYTHON_INSTALLER_URL="https://www.python.org/ftp/python/$PYTHON_VERSION/python-$PYTHON_VERSION-amd64.exe"
PYTHON_INSTALLER_FILENAME="tmp/python-$PYTHON_VERSION-amd64.exe"

# Construct the Python directory name (e.g., "Python39" from "3.9.13")
PYTHON_SHORT_VERSION="${PYTHON_VERSION%.*}" # Result: 3.9
PYTHON_DIR_VERSION="${PYTHON_SHORT_VERSION/./}"   # Result: 39
WINE_PYTHON_PATH="$WINEPREFIX/drive_c/users/$USER/AppData/Local/Programs/Python/Python$PYTHON_DIR_VERSION"
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

# --- Setup Wine and Python ---

# 2. Check for Windows Python in the local Wine prefix
if [ ! -f "$WINE_PYTHON_EXE" ]; then
    echo "--- Windows Python not found in local Wine prefix. Installing... ---"

    # Download Python installer if it doesn't exist
    if [ ! -f "$PYTHON_INSTALLER_FILENAME" ]; then
        echo "--- Downloading Python $PYTHON_VERSION for Windows... ---"
        wget -O "$PYTHON_INSTALLER_FILENAME" "$PYTHON_INSTALLER_URL"
    fi

    # Create a fresh Wine prefix and run the installer
    echo "--- Creating Wine prefix at $WINEPREFIX and installing Python... ---"
    echo "This may take a few minutes..."
    wineboot --init
    wine "$PYTHON_INSTALLER_FILENAME" /quiet InstallAllUsers=0 PrependPath=1

    echo "--- Python installation complete. ---"
else
    echo "--- Found existing Windows Python installation in local Wine prefix. ---"
fi

echo "Using Python from: $WINE_PYTHON_EXE"

# --- Build Process ---

echo "--- Installing dependencies in Wine environment... ---"
wine "$WINE_PYTHON_EXE" -m pip install -r requirements.txt

echo "--- Building Windows executable with PyInstaller (via Wine)... ---"
wine "$WINE_PYINSTALLER_EXE" --workpath=tmp/build --distpath=tmp/dist blescanner.spec --noconfirm

echo "--- Build complete! ---"
echo "The executable can be found in the 'tmp/dist/BLEScanner' directory."
