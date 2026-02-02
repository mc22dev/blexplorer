# BLE Scanner

This is a simple GUI application to scan for BLE devices, connect to them, and read/write their attributes.

## Usage

1.  Clone this repository.
2.  Run the appropriate script for your operating system:

    **For Linux and macOS:**
    ```bash
    ./run.sh
    ```

    **For Windows:**
    ```bat
    run.bat
    ```

This will create a virtual environment (if it doesn't exist), install the dependencies, run the test suite, and launch the application.

## Building

This project uses a `Makefile` to automate the build process for all supported platforms.

### Building for Linux

**Prerequisites:**

You must install the development headers for Kivy's dependencies. On Debian-based systems (like Ubuntu), you can do this by running:
```bash
sudo apt-get install -y libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev libglew-dev
```

To build a standalone executable for Linux, run the following command:
```bash
make linux
```

This will create a `tmp/dist/BLEScanner` directory containing the executable (`blescanner`) and all its dependencies. A packaged `.tar.gz` archive will be placed in `tmp/packages`.

### Building for Windows

#### On a Windows Machine

To build a standalone executable for Windows, run the following command (requires `make` to be installed, e.g., via [Chocolatey](https://chocolatey.org/) or Git Bash):
```bash
make windows
```

This will create a `tmp/dist/BLEScanner` directory containing the executable (`blescanner.exe`) and all its dependencies. A packaged `.zip` archive will be placed in `tmp/packages`.

#### On a Linux Machine (using Wine)

It is possible to build the Windows executable on a Linux machine using [Wine](https://www.winehq.org/), a compatibility layer for running Windows applications.

**Prerequisites:**

*   **Wine:** You must have Wine installed on your system (e.g., `sudo apt install wine`).

The build process is automated. On the first run, the `Makefile` will:
1.  Create a local Wine prefix in `tmp/.wine/` to avoid interfering with your system's Wine configuration.
2.  Download the official Windows installer for Python.
3.  Install Python into the local Wine prefix.

Once the setup is complete, you can build the application by running:
```bash
make windows-on-linux
```

This will create a `tmp/dist/BLEScanner` directory containing the executable (`blescanner.exe`) and all its dependencies. A packaged `.zip` archive will be placed in `tmp/packages`.

### Building for Android

To build the Android APK, run:
```bash
make android
```
The resulting `.apk` file will be placed in `tmp/packages`.

## Choosing a Bluetooth Adapter

You can choose a specific Bluetooth adapter (dongle) using the dropdown menu at the top of the application.

*   On **Linux**, the application will automatically populate this dropdown with a list of available `hciX` devices. You can click the "Refresh" button to rescan for adapters.
*   On **Windows and macOS**, automatic discovery is not supported. The dropdown will show "Default", but you can type in the identifier of your adapter if you know it (e.g., the MAC address on Windows).

If "Default" is selected, the system's default Bluetooth adapter will be used.

Click the "Scan for devices" button to discover nearby BLE devices. Click on a device name in the list to connect to it. Once connected, its services and characteristics will be displayed. You can then interact with each characteristic using the controls directly next to its UUID.
