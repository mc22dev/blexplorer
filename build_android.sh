#!/bin/bash

# Attempt to find the OpenJDK 17 installation path
JAVA_PATH=$(update-java-alternatives -l | grep 'java-17-openjdk' | awk '{print $3}')

# Check if a path was found
if [ -z "$JAVA_PATH" ]; then
  echo "Error: Could not automatically find OpenJDK 17."
  echo "Please ensure 'openjdk-17-jdk' is installed."
  exit 1
fi

echo "Found JDK 17 at: $JAVA_PATH"
export JAVA_HOME=$JAVA_PATH
export PATH="$JAVA_HOME/bin:$PATH"

echo "JAVA_HOME set to: $JAVA_HOME"
echo "PATH has been configured to prioritize JDK 17."

# Stop any running Gradle daemons to ensure the new environment is used
# This command is allowed to fail if no daemons are running
./.buildozer/android/platform/build-arm64-v8a_armeabi-v7a/dists/blescanner/gradlew --stop 2>/dev/null || true

# Check for virtual environment, install dependencies, and run the build
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "Installing dependencies..."
    pip install -r requirements.txt
    echo "Building the Android package..."
    buildozer android debug
else
    echo "Error: Virtual environment 'venv' not found."
    echo "Please run './run.sh' first to set up the environment."
    exit 1
fi
