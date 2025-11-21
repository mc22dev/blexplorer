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

Click the "Scan for devices" button to discover nearby BLE devices. Select a device from the list and click "Connect" to view its services and characteristics. You can then select a characteristic to read its value or write a new value to it.
