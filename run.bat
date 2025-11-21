@echo off

REM Create a virtual environment if it doesn't exist
IF NOT EXIST venv (
    echo "Creating virtual environment..."
    python -m venv venv
)

REM Install dependencies
echo "Installing dependencies..."
venv\\Scripts\\pip.exe install -r requirements.txt

REM Run the application
echo "Launching BLE Scanner..."
venv\\Scripts\\python.exe main.py
