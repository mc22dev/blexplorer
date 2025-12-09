#!/bin/bash

# Attempt to find the OpenJDK 17 installation path
JAVA_PATH=$(update-java-alternatives -l | grep 'java-17-openjdk' | awk '{print $3}')

# Check if a path was found
if [ -z "$JAVA_PATH" ]; then
  echo "Error: Could not automatically find OpenJDK 17."
  echo "Please ensure 'openjdk-17-jdk' is installed or set the JAVA_HOME environment variable manually."
  exit 1
fi

echo "Found JDK 17 at: $JAVA_PATH"
export JAVA_HOME=$JAVA_PATH

# Check for virtual environment and run the build
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "Building the Android package..."
    buildozer android debug
else
    echo "Error: Virtual environment 'venv' not found."
    echo "Please run './run.sh' first to set up the environment and install dependencies."
    exit 1
fi
