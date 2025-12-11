.PHONY: android install run-android run-local mrproper logcat windows

# Build the Android debug APK
android:
	./build_android.sh

# Build the Windows executable (must be run on a Windows machine)
windows:
	./build_windows.bat

# Install the APK on a connected device
install: android
	. venv/bin/activate && buildozer android deploy

# Run the app on the connected device (will also install if needed)
run-android: android
	. venv/bin/activate && buildozer android run

# Set up the environment, run tests, and launch the app locally
run-local:
	./run.sh

# Clean all build artifacts and virtual environments
mrproper:
	- . venv/bin/activate && yes | buildozer distclean
	-rm -rf venv
	-rm -rf bin
	-find . -type d -name "__pycache__" -exec rm -r {} +

# Show logs from the Android app
logcat:
	. venv/bin/activate && buildozer android logcat
