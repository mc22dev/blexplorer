.PHONY: android install run-android run-local mrproper logcat

# Build the Android debug APK
android:
	./build_android.sh

# Install the APK on a connected device
install: android
	buildozer android deploy

# Run the app on the connected device (will also install if needed)
run-android: android
	buildozer android run

# Set up the environment, run tests, and launch the app locally
run-local:
	./run.sh

# Clean all build artifacts and virtual environments
mrproper:
	-yes | buildozer distclean
	-rm -rf venv
	-rm -rf bin
	-find . -type d -name "__pycache__" -exec rm -r {} +

# Show logs from the Android app
logcat:
	buildozer android logcat
