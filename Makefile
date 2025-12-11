.PHONY: all android install run-android run-local mrproper logcat windows windows-on-linux linux packages

# Build for all platforms
all: linux windows-on-linux android

# Create the packages directory
packages:
	mkdir -p tmp/packages

# Build the Android debug APK and package it
android: packages
	./scripts/build_android.sh
	./scripts/package.sh android

# Build the Windows executable (must be run on a Windows machine)
windows: packages
	./scripts/build_windows.bat
	./scripts/package.sh windows

# Build the Windows executable on Linux using Wine and package it
windows-on-linux: packages
	./scripts/build_windows_on_linux.sh
	./scripts/package.sh windows

# Build the Linux executable and package it
linux: packages
	./scripts/build_linux.sh
	./scripts/package.sh linux

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
