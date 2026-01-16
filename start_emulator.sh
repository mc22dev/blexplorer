#!/bin/bash
set -e

# Find the Android SDK path
SDK_PATH="$HOME/.buildozer/android/platform/android-sdk"
if [ ! -d "$SDK_PATH" ]; then
  echo "Android SDK not found. Please run 'buildozer android debug' once to install it."
  exit 1
fi

# Find necessary tools
EMULATOR_PATH="$SDK_PATH/emulator/emulator"
if [ ! -f "$EMULATOR_PATH" ]; then
  echo "Emulator executable not found at $EMULATOR_PATH"
  exit 1
fi

# The path for cmdline-tools might vary, look for the 'latest' first
if [ -d "$SDK_PATH/cmdline-tools/latest/bin" ]; then
  SDKMANAGER_PATH="$SDK_PATH/cmdline-tools/latest/bin/sdkmanager"
  AVDMANAGER_PATH="$SDK_PATH/cmdline-tools/latest/bin/avdmanager"
# Fallback to the older 'tools' path
elif [ -f "$SDK_PATH/tools/bin/sdkmanager" ]; then
  SDKMANAGER_PATH="$SDK_PATH/tools/bin/sdkmanager"
  AVDMANAGER_PATH="$SDK_PATH/tools/bin/avdmanager"
else
  echo "Android SDK command-line tools (sdkmanager, avdmanager) not found."
  echo "Please install them via Android Studio or the 'tools' package."
  exit 1
fi

# Get the list of AVDs
AVDS=($("$EMULATOR_PATH" -list-avds))

# If no AVDs are found, create a default one
if [ ${#AVDS[@]} -eq 0 ]; then
  DEFAULT_AVD_NAME="DefaultAVD"
  # Use a recent, common, and stable system image. Android 30 (API level R) is a good choice.
  SYSTEM_IMAGE="system-images;android-30;google_apis;x86_64"
  DEVICE_DEFINITION="pixel_2" # A common default device

  echo "No AVDs found. Creating a new one named '$DEFAULT_AVD_NAME'."
  echo "This may take a few minutes..."

  # 1. Install the system image if not present. The `yes` command handles license agreement prompts.
  echo "Downloading system image: $SYSTEM_IMAGE"
  yes | "$SDKMANAGER_PATH" --install "$SYSTEM_IMAGE" > /dev/null

  # 2. Create the AVD. Piping "no" answers the question "Do you wish to create a custom hardware profile?".
  echo "Creating AVD..."
  echo "no" | "$AVDMANAGER_PATH" create avd --force --name "$DEFAULT_AVD_NAME" --package "$SYSTEM_IMAGE" --device "$DEVICE_DEFINITION"

  # Refresh the list of AVDs
  AVDS=($("$EMULATOR_PATH" -list-avds))
fi

# Use the AVD_NAME from the environment or default to the first one in the list
TARGET_AVD=${AVD_NAME:-${AVDS[0]}}

# Verify the target AVD exists before trying to start it
AVD_EXISTS=false
for avd in "${AVDS[@]}"; do
    if [[ "$avd" == "$TARGET_AVD" ]]; then
        AVD_EXISTS=true
        break
    fi
done

if ! $AVD_EXISTS; then
    echo "Error: Target AVD '$TARGET_AVD' does not exist."
    echo "Available AVDs: ${AVDS[*]}"
    exit 1
fi

# Start the emulator
echo "Starting emulator with AVD: $TARGET_AVD"
nohup "$EMULATOR_PATH" -avd "$TARGET_AVD" >/dev/null 2>&1 &
