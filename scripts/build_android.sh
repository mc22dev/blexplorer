#!/bin/bash

# Find the Java installation path robustly
export JAVA_HOME=$(dirname $(dirname $(readlink -f $(which java))))

echo "JAVA_HOME set to: $JAVA_HOME"

# Check for virtual environment, install dependencies, and run the build
if [ -d "tmp/venv" ]; then
    source tmp/venv/bin/activate
    echo "Installing dependencies..."
    pip install -r requirements.txt
    echo "Building the Android package..."
    buildozer android debug
else
    echo "Error: Virtual environment 'tmp/venv' not found."
    echo "Please run './run.sh' first to set up the environment."
    exit 1
fi
