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

## Building for Windows

To build a standalone executable for Windows, run the following script:

```
build_windows.bat
```

This will create a `dist/BLEScanner` directory containing the executable and all its dependencies.

## Choosing a Bluetooth Adapter

You can choose a specific Bluetooth adapter (dongle) using the dropdown menu at the top of the application.

*   On **Linux**, the application will automatically populate this- dropdown with a list of available `hciX` devices. You can click the "Refresh" button to rescan for adapters.
*   On **Windows and macOS**, automatic discovery is not supported. The dropdown will show "Default", but you can type in the identifier of your adapter if you know it (e.g., the MAC address on Windows).

If "Default" is selected, the system's default Bluetooth adapter will be used.

Click the "Scan for devices" button to discover nearby BLE devices. Click on a device name in the list to connect to it. Once connected, its services and characteristics will be displayed. You can then interact with each characteristic using the controls directly next to its UUID.
