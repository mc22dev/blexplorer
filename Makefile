.PHONY: all android install run-android run-android-emulator stop-android-emulator run run-windows clean logcat windows windows-on-linux linux packages run-windows-on-linux

# Extract package metadata from the buildozer.spec and _version.py files
PACKAGE_NAME := $(shell grep '^package.name =' buildozer.spec | cut -d' ' -f3)
VERSION := $(shell grep "^__version__" src/_version.py | cut -d'"' -f2)

# --- Environment Setup ---
VENV_DIR := tmp/venv
VENV_ACTIVATE_UNIX := $(VENV_DIR)/bin/activate
VENV_ACTIVATE_WIN := $(VENV_DIR)/Scripts/activate.bat

# Common setup target for Unix-like systems
setup: $(VENV_DIR)
	. $(VENV_ACTIVATE_UNIX); pip install --upgrade pip; pip install -r requirements.txt

# Windows-specific setup
setup-windows: $(VENV_DIR)
	call $(VENV_ACTIVATE_WIN) && pip install --upgrade pip && pip install -r requirements.txt

$(VENV_DIR):
	python3 -m venv $(VENV_DIR) || python -m venv $(VENV_DIR)

# --- Main Targets ---

# Build for all platforms (on Linux)
all: linux windows-on-linux android

# Run the application locally on Unix-like systems
run: setup
	. $(VENV_ACTIVATE_UNIX); pytest; PYTHONPATH=src python3 -m blescanner

# Run the application locally on Windows
run-windows: setup-windows
	call $(VENV_ACTIVATE_WIN) && pytest && set PYTHONPATH=src && python -m blescanner

# Create the packages directory if it doesn't exist
packages:
	mkdir -p tmp/packages

# --- Build Targets ---

# Build the Android debug APK and package it
android: setup packages
	. $(VENV_ACTIVATE_UNIX); \
	export JAVA_HOME="$$(dirname $$(dirname $$(readlink -f $$(which java))) | sed 's/java-[^-]*/java-17/')"; \
	buildozer android debug
	cp tmp/bin/*.apk tmp/packages/$(PACKAGE_NAME)-$(VERSION)-android.apk

# Build the Windows executable (must be run on a Windows machine)
windows: setup-windows packages
	call $(VENV_ACTIVATE_WIN) && pyinstaller blescanner.spec --distpath "tmp/dist" --workpath "tmp/build" --noconfirm
	(cd tmp/dist/BLEScanner && zip -r ../../packages/$(PACKAGE_NAME)-$(VERSION)-windows.zip . -x "*_internal*")

# Build the Windows executable on Linux using Wine and package it
windows-on-linux: setup packages
	. $(VENV_ACTIVATE_UNIX); \
	rm -rf tmp/build tmp/dist; \
	export WINEPREFIX="$(PWD)/tmp/.wine"; \
	export WINEARCH=win64; \
	PYTHON_VERSION="3.9.13"; \
	PYTHON_INSTALLER_URL="https://www.python.org/ftp/python/$${PYTHON_VERSION}/python-$${PYTHON_VERSION}-amd64.exe"; \
	PYTHON_INSTALLER_FILENAME="tmp/python-$${PYTHON_VERSION}-amd64.exe"; \
	PYTHON_SHORT_VERSION="$${PYTHON_VERSION%.*}"; \
	PYTHON_DIR_VERSION="$$(echo $$PYTHON_SHORT_VERSION | sed 's/\.//')"; \
	WINE_PYTHON_PATH="$$WINEPREFIX/drive_c/users/$$USER/AppData/Local/Programs/Python/Python$$PYTHON_DIR_VERSION"; \
	WINE_PYTHON_EXE="$$WINE_PYTHON_PATH/python.exe"; \
	WINE_PYINSTALLER_EXE="$$WINE_PYTHON_PATH/Scripts/pyinstaller.exe"; \
	if ! command -v wine > /dev/null 2>&1; then \
		echo "Error: 'wine' command not found."; \
		exit 1; \
	fi; \
	if [ ! -f "$$WINE_PYTHON_EXE" ]; then \
		if [ ! -f "$$PYTHON_INSTALLER_FILENAME" ]; then \
			wget -O "$$PYTHON_INSTALLER_FILENAME" "$$PYTHON_INSTALLER_URL"; \
		fi; \
		wineboot --init; \
		wine "$$PYTHON_INSTALLER_FILENAME" /quiet InstallAllUsers=0 PrependPath=1; \
	fi; \
	wine "$$WINE_PYTHON_EXE" -m pip install -r requirements.txt; \
	wine "$$WINE_PYINSTALLER_EXE" --workpath=tmp/build --distpath=tmp/dist blescanner.spec --noconfirm
	(cd tmp/dist/BLEScanner && zip -r ../../packages/$(PACKAGE_NAME)-$(VERSION)-windows.zip . -x "*_internal*")

# Build the Linux executable and package it
linux: setup packages
	. $(VENV_ACTIVATE_UNIX); pyinstaller blescanner.spec --distpath "tmp/dist" --workpath "tmp/build" --noconfirm
	(cd tmp/dist/BLEScanner && tar -czf ../../packages/$(PACKAGE_NAME)-$(VERSION)-linux.tar.gz --exclude='./_internal' .)

# --- Utility Targets ---

# Install the APK on a connected device
install: android
	. $(VENV_ACTIVATE_UNIX); buildozer android deploy

# Run the app on a connected device (will also install if needed)
run-android: android
	. $(VENV_ACTIVATE_UNIX); buildozer android run

# Run the app on an emulator (will also install if needed)
run-android-emulator: android
	./start_emulator.sh
	. $(VENV_ACTIVATE_UNIX); \
	export BUILDOZER_OVERRIDE_ANDROID_ADB_ARGS="-e"; \
	adb wait-for-device; \
	buildozer android run

# Run the Windows executable on Linux using Wine
run-windows-on-linux: windows-on-linux
	WINEPREFIX="$(PWD)/tmp/.wine" wine tmp/dist/BLEScanner/blescanner.exe

# Stop any running emulators
stop-android-emulator:
	. $(VENV_ACTIVATE_UNIX); \
	adb devices | grep emulator | cut -f1 | while read -r line; do adb -s $$line emu kill; done

# Clean all build artifacts and virtual environments
clean:
	- . $(VENV_ACTIVATE_UNIX); yes | buildozer distclean || true
	-rm -rf tmp
	-find . -type d -name "__pycache__" -exec rm -r {} +

# Show logs from the Android app
logcat:
	. $(VENV_ACTIVATE_UNIX); buildozer android logcat
