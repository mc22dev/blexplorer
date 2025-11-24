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

## Choosing a Bluetooth Adapter

If you have multiple Bluetooth adapters (dongles) connected to your system, you can specify which one to use by entering its identifier in the "Bluetooth Adapter" field at the top of the window. If you leave this field empty, the system's default adapter will be used.

Here's how to find your adapter's identifier on different operating systems:

*   **Linux:** Run the command `hciconfig` in your terminal. The identifier will be listed as `hciX` (e.g., `hci0`).
*   **Windows:** The adapter identifier is typically the MAC address of the Bluetooth radio. You can find this in Device Manager under your Bluetooth adapter's properties.
*   **macOS:** On macOS, you cannot choose the adapter; the system default is always used.

Click the "Scan for devices" button to discover nearby BLE devices. Select a device from the list and click "Connect" to view its services and characteristics. You can then select a characteristic to read its value or write a new value to it.
