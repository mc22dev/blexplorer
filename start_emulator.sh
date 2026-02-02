#!/bin/bash
set -e

# Find the Android SDK path
SDK_PATH="$HOME/.buildozer/android/platform/android-sdk"
if [ ! -d "$SDK_PATH" ]; then
  echo "Android SDK not found. Please run 'buildozer android debug' once to install it."
  exit 1
fi

# Find the emulator executable
EMULATOR_PATH="$SDK_PATH/emulator/emulator"
if [ ! -f "$EMULATOR_PATH" ]; then
  echo "Emulator not found at $EMULATOR_PATH"
  exit 1
fi

# Get the list of AVDs
AVDS=($("$EMULATOR_PATH" -list-avds))
if [ ${#AVDS[@]} -eq 0 ]; then
  echo "No AVDs found. Please create one using Android Studio."
  exit 1
fi

# Use the AVD_NAME from the environment or default to the first one
TARGET_AVD=${AVD_NAME:-${AVDS[0]}}

# Start the emulator
echo "Starting emulator with AVD: $TARGET_AVD"
nohup "$EMULATOR_PATH" -avd "$TARGET_AVD" >/dev/null 2>&1 &
