.PHONY: all android install run-android run-local mrproper logcat windows windows-on-linux linux packages run-windows-on-linux

# Extract package metadata from the buildozer.spec file
PACKAGE_NAME := $(shell grep '^package.name =' buildozer.spec | cut -d' ' -f3)
VERSION := $(shell grep '^version =' buildozer.spec | cut -d' ' -f3)

# Build for all platforms
all: linux windows-on-linux android

# Create the packages directory
packages:
	mkdir -p tmp/packages

# Build the Android debug APK and package it
android: packages
	./scripts/build_android.sh
	cp tmp/bin/*.apk tmp/packages/$(PACKAGE_NAME)-$(VERSION)-android.apk

# Build the Windows executable (must be run on a Windows machine)
windows: packages
	./scripts/build_windows.bat
	(cd tmp/dist/BLEScanner && zip -r ../../packages/$(PACKAGE_NAME)-$(VERSION)-windows.zip . -x "*_internal*")

# Build the Windows executable on Linux using Wine and package it
windows-on-linux: packages
	./scripts/build_windows_on_linux.sh
	(cd tmp/dist/BLEScanner && zip -r ../../packages/$(PACKAGE_NAME)-$(VERSION)-windows.zip . -x "*_internal*")

# Run the Windows executable on Linux using Wine
run-windows-on-linux: windows-on-linux
	WINEPREFIX="tmp/.wine" wine tmp/dist/BLEScanner/blescanner.exe

# Build the Linux executable and package it
linux: packages
	./scripts/build_linux.sh
	(cd tmp/dist/BLEScanner && tar -czf ../../packages/$(PACKAGE_NAME)-$(VERSION)-linux.tar.gz --exclude='./_internal' .)

# Install the APK on a connected device
install: android
	. tmp/venv/bin/activate && buildozer android deploy

# Run the app on a connected device (will also install if needed)
run-android: android
	. tmp/venv/bin/activate && buildozer android run

# Set up the environment, run tests, and launch the app locally
run-local:
	./scripts/run.sh

# Clean all build artifacts and virtual environments
mrproper:
	- . tmp/venv/bin/activate && yes | buildozer distclean
	-rm -rf tmp
	-find . -type d -name "__pycache__" -exec rm -r {} +

# Show logs from the Android app
logcat:
	. tmp/venv/bin/activate && buildozer android logcat
