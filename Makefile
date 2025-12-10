.PHONY: android install run-android run-local

# Build the Android debug APK
android:
	./build_android.sh

# Install the APK on a connected device
install: android
	adb install -r bin/blescanner-0.1-arm64-v8a_armeabi-v7a-debug.apk

# Run the app on the connected device
run-android: install
	adb shell am start -n org.kivy.blescanner/org.kivy.android.PythonActivity

# Set up the environment, run tests, and launch the app locally
run-local:
	./run.sh
