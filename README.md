# BLE Scanner

This is a simple GUI application to scan for BLE devices, connect to them, and read/write their attributes.

## Installation

1. Clone this repository.
2. Install the dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

Run the application:
```
python main.py
```

Click the "Scan for devices" button to discover nearby BLE devices. Select a device from the list and click "Connect" to view its services and characteristics. You can then select a characteristic to read its value or write a new value to it.
