#!/bin/bash
set -e

# This script packages the build artifacts for a specific platform.
# It takes one argument: the platform name (linux, windows, or android).

PLATFORM=$1
VERSION=$(grep '^version =' buildozer.spec | cut -d' ' -f3)
PACKAGE_NAME=$(grep '^package.name =' buildozer.spec | cut -d' ' -f3)
PACKAGE_DIR="tmp/packages"
SRC_DIR="tmp/dist"
ANDROID_SRC_DIR="tmp/bin"

if [ -z "$PLATFORM" ]; then
    echo "Usage: $0 <platform>"
    echo "  platform: linux, windows, or android"
    exit 1
fi

# Create the packages directory if it doesn't exist
mkdir -p "$PACKAGE_DIR"

echo "Packaging for $PLATFORM version $VERSION..."

if [ "$PLATFORM" == "linux" ]; then
    # Create a tarball for the Linux build
    TARBALL_NAME="${PACKAGE_NAME}-${VERSION}-linux.tar.gz"
    echo "Creating tarball: $TARBALL_NAME"
    (
        cd "$SRC_DIR/BLEScanner" || exit
        tar -czf "../../packages/$TARBALL_NAME" .
    )
elif [ "$PLATFORM" == "windows" ]; then
    # Create a zip file for the Windows build
    ZIP_NAME="${PACKAGE_NAME}-${VERSION}-windows.zip"
    echo "Creating zip file: $ZIP_NAME"
    (
        cd "$SRC_DIR/BLEScanner" || exit
        zip -r "../../packages/$ZIP_NAME" .
    )
elif [ "$PLATFORM" == "android" ]; then
    # Copy the Android APK
    APK_NAME="${PACKAGE_NAME}-${VERSION}-android.apk"
    echo "Copying APK: $APK_NAME"
    cp "$ANDROID_SRC_DIR"/*.apk "$PACKAGE_DIR/$APK_NAME"
else
    echo "Unknown platform: $PLATFORM"
    exit 1
fi

echo "Packaging complete."
