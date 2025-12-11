# BLE Scanner

This is a simple GUI application to scan for BLE devices, connect to them, and read/write their attributes.

## Usage

1. Clone this repository.
2. Run the appropriate script for your operating system:

   **For Linux and macOS:**
   ```
   ./run.sh
   ```

   **For Windows:**
   ```
   run.bat
   ```

This will create a virtual environment (if it doesn't exist), install the dependencies, and launch the application.

## Building for Linux

**Prerequisites:**

You must install the development headers for Kivy's dependencies. On Debian-based systems (like Ubuntu), you can do this by running:
```
sudo apt-get install -y libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev libglew-dev
```

To build a standalone executable for Linux, run the following script:

```
./scripts/build_linux.sh
```

Alternatively, you can use the `make` target:

```
make linux
```

This will create a `tmp/dist/BLEScanner` directory containing the executable (`blescanner`) and all its dependencies.

## Building for Windows

### On a Windows Machine

To build a standalone executable for Windows, run the following script:

```
build_windows.bat
```

Alternatively, if you have `make` installed on your Windows environment (e.g., through Git Bash), you can run:

```
make windows
```

This will create a `tmp/dist/BLEScanner` directory containing the executable (`blescanner.exe`) and all its dependencies.

### On a Linux Machine (using Wine)

It is possible to build the Windows executable on a Linux machine using [Wine](https://www.winehq.org/), a compatibility layer for running Windows applications.

**Prerequisites:**

*   **Wine:** You must have Wine installed on your system (e.g., `sudo apt install wine`).

The build script automates the rest of the setup. On its first run, it will:
1.  Create a local Wine prefix in a `.wine/` directory to avoid interfering with your system's Wine configuration.
2.  Download the official Windows installer for Python.
3.  Install Python into the local Wine prefix.

Once the setup is complete, you can build the application by running the following script:

```
./build_windows_on_linux.sh
```

Alternatively, you can use the `make` target:

```
make windows-on-linux
```

This will create a `tmp/dist/BLEScanner` directory containing the executable (`blescanner.exe`) and all its dependencies.

## Choosing a Bluetooth Adapter

You can choose a specific Bluetooth adapter (dongle) using the dropdown menu at the top of the application.

*   On **Linux**, the application will automatically populate this dropdown with a list of available `hciX` devices. You can click the "Refresh" button to rescan for adapters.
*   On **Windows and macOS**, automatic discovery is not supported. The dropdown will show "Default", but you can type in the identifier of your adapter if you know it (e.g., the MAC address on Windows).

If "Default" is selected, the system's default Bluetooth adapter will be used.

Click the "Scan for devices" button to discover nearby BLE devices. Click on a device name in the list to connect to it. Once connected, its services and characteristics will be displayed. You can then interact with each characteristic using the controls directly next to its UUID.
