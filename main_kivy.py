import platform
import subprocess
import re
from datetime import datetime
from functools import partial

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.properties import ListProperty, StringProperty

from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

from ble_manager import BLEManager
from device_frame_kivy import DeviceFrameKivy
from characteristic_frame_kivy import CharacteristicFrameKivy
from collapsible_frame_kivy import CollapsibleFrameKivy
from gatt import GATT_SERVICES

# Load the kv files for the custom widgets
Builder.load_file('deviceframekivy.kv')
Builder.load_file('characteristicframekivy.kv')
Builder.load_file('collapsibleframekivy.kv')


class MainLayout(BoxLayout):
    pass


class BLEScannerApp(App):
    adapters = ListProperty(["Default"])
    log_text = StringProperty("")

    def build(self):
        self.ble_manager = BLEManager(
            device_discovered_callback=self._on_device_discovered,
            connection_status_callback=self._on_connection_status_changed,
            notification_callback=self.notification_handler
        )
        self.characteristic_frames = {}
        # Kivy automatically loads the kv file that matches the App class name
        # (BLEScannerApp -> blescanner.kv).
        # We just need to return the root widget.
        return MainLayout()

    def on_start(self):
        self.discover_adapters()
        self.root.ids.scan_button.bind(on_release=self.scan_for_devices)
        self.root.ids.disconnect_button.bind(on_release=self.disconnect_from_device)

    def on_stop(self):
        self.ble_manager.shutdown()

    def discover_adapters(self):
        """Discovers available Bluetooth adapters and populates the dropdown."""
        adapters = ["Default"]
        if platform.system() == "Linux":
            try:
                result = subprocess.run(['hciconfig'], capture_output=True, text=True, check=True)
                adapters.extend(re.findall(r'^(hci\d+)', result.stdout, re.MULTILINE))
            except (FileNotFoundError, subprocess.CalledProcessError):
                self.log_with_timestamp("hciconfig not found. Could not list Bluetooth adapters.")
        else:
            self.log_with_timestamp("Adapter discovery is currently only supported on Linux.")
        self.root.ids.adapter_spinner.values = adapters

    def scan_for_devices(self, *args):
        """Initiates a scan for nearby BLE devices."""
        self.root.ids.scan_button.disabled = True
        self.root.ids.scan_button.text = "Scanning..."
        self.root.ids.device_list.clear_widgets()
        self.log_with_timestamp("Scan started...")
        adapter = self.root.ids.adapter_spinner.text
        adapter = adapter if adapter != "Default" else None

        timeout = 5.0

        self.ble_manager.scan_for_devices(adapter, timeout)
        Clock.schedule_once(self.on_scan_finished, timeout + 0.5)

    def on_scan_finished(self, *args):
        self.log_with_timestamp("Scan stopped.")
        self.root.ids.scan_button.disabled = False
        self.root.ids.scan_button.text = "Scan for devices"

    def _on_device_discovered(self, device: BLEDevice, adv_data: AdvertisementData):
        """Callback for when a device is discovered."""
        Clock.schedule_once(lambda dt: self._populate_device_ui(device, adv_data))

    def _populate_device_ui(self, device: BLEDevice, adv_data: AdvertisementData):
        """
        Populates the UI with a discovered BLE device.
        """
        self.log_with_timestamp(f"Found device: {device.address} ({device.name or 'Unknown'}) RSSI: {adv_data.rssi}")
        frame = DeviceFrameKivy(device=device, adv_data=adv_data)
        self.root.ids.device_list.add_widget(frame)

    def connect_to_device(self, device: BLEDevice):
        """Connects to the selected device."""
        self.log_with_timestamp(f"Connecting to {device.address} ({device.name})...")
        adapter = self.root.ids.adapter_spinner.text
        adapter = adapter if adapter != "Default" else None
        self.ble_manager.connect_to_device(device.address, adapter)

    def disconnect_from_device(self, *args):
        """Initiates a manual disconnection from the connected device."""
        self.ble_manager.disconnect_from_device()

    def _on_connection_status_changed(self, is_connected: bool):
        """Callback for connection status changes."""
        Clock.schedule_once(lambda dt: self._update_connection_ui(is_connected))

    def _update_connection_ui(self, is_connected: bool):
        """Updates the UI based on the connection status."""
        if is_connected:
            self.log_with_timestamp("Device connected.")
            self.root.ids.disconnect_button.disabled = False
            self.discover_attributes()
        else:
            self.log_with_timestamp("Device disconnected.")
            self.root.ids.disconnect_button.disabled = True
            self.root.ids.characteristic_list.clear_widgets()
            self.characteristic_frames = {}

    def discover_attributes(self):
        """Discovers and displays the services and characteristics of the connected device."""
        self.root.ids.characteristic_list.clear_widgets()
        self.characteristic_frames = {}

        if not self.ble_manager.client:
            return

        all_characteristics = [char for service in self.ble_manager.client.services for char in service.characteristics]
        all_characteristics.sort(key=lambda c: (c.service_uuid, c.uuid))

        service_frames = {}
        for char in all_characteristics:
            service_uuid = str(char.service_uuid)
            if service_uuid not in service_frames:
                service_name = GATT_SERVICES.get(service_uuid.split("-")[0].lstrip("0").lower(), "Unknown Service")
                sf = CollapsibleFrameKivy(title=f"Service: {service_name} ({service_uuid})")
                self.root.ids.characteristic_list.add_widget(sf)
                service_frames[service_uuid] = sf

            char_frame = CharacteristicFrameKivy(characteristic=char)
            self.characteristic_frames[char.uuid] = char_frame
            service_frames[service_uuid].add_content(char_frame)

            # Bind the buttons
            char_frame.ids.read_button.bind(on_release=partial(self.read_characteristic, char, char_frame))
            char_frame.ids.write_button.bind(on_release=partial(self.write_characteristic, char, char_frame))
            char_frame.ids.subscribe_button.bind(on_state=partial(self.toggle_subscription, char, char_frame))


    def read_characteristic(self, characteristic, char_frame, *args):
        self.ble_manager.read_characteristic(characteristic.uuid, lambda value: Clock.schedule_once(lambda dt: self.on_characteristic_read(char_frame, value)))

    def on_characteristic_read(self, char_frame, value):
        if value is not None:
            char_frame.char_value = value.hex()
            self.log_with_timestamp(f"Value read from {char_frame.char_uuid}: {value.hex()}")
        else:
            self.log_with_timestamp(f"Failed to read from {char_frame.char_uuid}")

    def write_characteristic(self, characteristic, char_frame, *args):
        value_str = char_frame.ids.value_input.text
        try:
            # Reset color on new write attempt
            char_frame.ids.value_input.background_color = (1, 1, 1, 1) # Default color
            write_value = bytes.fromhex(value_str)
        except ValueError:
            self.log_with_timestamp(f"Invalid hex value for write on {characteristic.uuid}")
            char_frame.ids.value_input.background_color = (1, 0.6, 0.6, 1) # Light red for error
            return

        self.ble_manager.write_characteristic(characteristic.uuid, write_value, lambda success: Clock.schedule_once(lambda dt: self.on_characteristic_write(char_frame, success)))

    def on_characteristic_write(self, char_frame, success):
        if success:
            self.log_with_timestamp(f"Value written to {char_frame.char_uuid}")
        else:
            self.log_with_timestamp(f"Write Error on {char_frame.char_uuid}")
            char_frame.ids.value_input.background_color = (1, 0.6, 0.6, 1) # Light red for error

    def toggle_subscription(self, characteristic, char_frame, widget, state):
        if state == 'down':
            self.ble_manager.subscribe_to_characteristic(characteristic.uuid)
            self.log_with_timestamp(f"Subscribed to {characteristic.uuid}")
        else:
            self.ble_manager.unsubscribe_from_characteristic(characteristic.uuid)
            self.log_with_timestamp(f"Unsubscribed from {characteristic.uuid}")

    def notification_handler(self, characteristic, data):
        """Handles incoming notifications."""
        Clock.schedule_once(lambda dt: self.on_notification(characteristic, data))

    def on_notification(self, characteristic, data):
        self.log_with_timestamp(f"Notification from {characteristic.uuid}: {data.hex()}")
        if characteristic.uuid in self.characteristic_frames:
            self.characteristic_frames[characteristic.uuid].char_value = data.hex()

    def log_with_timestamp(self, message: str):
        """Logs a message with a timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        log_message = f"[{timestamp}] {message}\n"
        self.root.ids.log_view.text += log_message


if __name__ == '__main__':
    BLEScannerApp().run()
