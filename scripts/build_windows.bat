@echo off
echo "Activating virtual environment..."
call tmp\venv\Scripts\activate.bat

echo "Building Windows executable..."
pyinstaller --workpath=tmp\build --distpath=tmp\dist blescanner.spec

echo "Build complete. The executable is in the tmp\dist\BLEScanner directory."
