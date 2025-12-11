@echo off
echo "Activating virtual environment..."
call venv\Scripts\activate.bat

echo "Building Windows executable..."
pyinstaller blescanner.spec

echo "Build complete. The executable is in the dist/BLEScanner directory."
