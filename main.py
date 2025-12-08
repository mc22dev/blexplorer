import customtkinter
import platform
import subprocess
import re
import tkinter
from datetime import datetime
from tkinter import filedialog
from typing import Dict, Optional, List, Tuple, Any, Union

from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.descriptor import BleakGATTDescriptor
from bleak.exc import BleakError

from ble_manager import BLEManager
from device_cache import DeviceCache, service_to_dict
from models import CachedService
from descriptor_frame import DescriptorFrame
from characteristic_frame import CharacteristicFrame
from device_frame import DeviceFrame
from collapsible_frame import CollapsibleFrame
from gatt import GATT_SERVICES
from models import CachedCharacteristic, CachedDescriptor


class App(customtkinter.CTk):
    """The main application class for the BLE Scanner."""

    def __init__(self) -> None:
        """Initializes the main application window and widgets."""
        super().__init__()

        self.title("BLE Scanner")
        self.geometry("800x600")

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(1, weight=1)

        self._create_adapter_frame()
        self._create_devices_frame()
        self._create_right_pane()

        self.device_cache = DeviceCache()
        self.selected_device: Optional[BLEDevice] = None
        self.device_frames: Dict[str, DeviceFrame] = {}
        self.characteristic_frames: Dict[int, CharacteristicFrame] = {}
        self.diff_checker_id: Optional[str] = None

        self.ble_manager = BLEManager(
            device_discovered_callback=self._on_device_discovered,
            connection_status_callback=self._on_connection_status_changed,
            notification_callback=self.notification_handler
        )

        self.after(100, self.discover_adapters)

        # Bind mouse wheel events for cross-platform scrolling
        self.bind_all("<MouseWheel>", self._on_mouse_wheel)  # Windows
        self.bind_all("<Button-4>", self._on_mouse_wheel)    # Linux scroll up
        self.bind_all("<Button-5>", self._on_mouse_wheel)    # Linux scroll down

    def _create_adapter_frame(self) -> None:
        """Creates the top bar for controls."""
        self.adapter_frame = customtkinter.CTkFrame(self)
        self.adapter_frame.grid(row=0, column=0, columnspan=2, padx=10, pady=(10,0), sticky="ew")
        self.adapter_frame.grid_columnconfigure(1, weight=1)

        self.adapter_label = customtkinter.CTkLabel(self.adapter_frame, text="Bluetooth Adapter:")
        self.adapter_label.grid(row=0, column=0, padx=10, pady=10)

        self.adapter_combobox = customtkinter.CTkComboBox(self.adapter_frame, values=["Default"], command=self.on_adapter_selected)
        self.adapter_combobox.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        self.adapter_combobox.set("Default")

        self.refresh_adapters_button = customtkinter.CTkButton(self.adapter_frame, text="Refresh", command=self.discover_adapters)
        self.refresh_adapters_button.grid(row=0, column=2, padx=(0,5), pady=10)

        self.scan_button = customtkinter.CTkButton(self.adapter_frame, text="Scan for devices", command=self.scan_for_devices)
        self.scan_button.grid(row=0, column=3, padx=(5,5), pady=10)

        self.scan_timeout_label = customtkinter.CTkLabel(self.adapter_frame, text="Scan Timeout (s):")
        self.scan_timeout_label.grid(row=0, column=4, padx=(10, 0), pady=10)
        self.scan_timeout_entry = customtkinter.CTkEntry(self.adapter_frame, width=50)
        self.scan_timeout_entry.grid(row=0, column=5, padx=(0, 10), pady=10)
        self.scan_timeout_entry.insert(0, "5.0")

        self.disconnect_button = customtkinter.CTkButton(self.adapter_frame, text="Disconnect", command=self.disconnect_from_device, state="disabled")
        self.disconnect_button.grid(row=0, column=6, padx=(0,10), pady=10)

        self.connection_status_label = customtkinter.CTkLabel(self.adapter_frame, text="Status: Disconnected", text_color="red")
        self.connection_status_label.grid(row=0, column=7, padx=10, pady=10)

    def _create_devices_frame(self) -> None:
        """Creates the left column for devices."""
        self.devices_frame_container = customtkinter.CTkFrame(self)
        self.devices_frame_container.grid(row=1, column=0, rowspan=2, padx=10, pady=(0,10), sticky="nsew")
        self.devices_frame_container.grid_rowconfigure(1, weight=1)

        self.search_entry = customtkinter.CTkEntry(self.devices_frame_container, placeholder_text="Filter devices")
        self.search_entry.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        self.search_entry.bind("<KeyRelease>", self.filter_devices)

        self.devices_frame = customtkinter.CTkScrollableFrame(self.devices_frame_container, label_text="Nearby Devices")
        self.devices_frame.grid(row=1, column=0, padx=0, pady=0, sticky="nsew")

    def _create_right_pane(self) -> None:
        """Creates the right column for characteristics and debug."""
        self.right_paned_frame = customtkinter.CTkFrame(self)
        self.right_paned_frame.grid(row=1, column=1, rowspan=2, padx=(0, 10), pady=(0, 10), sticky="nsew")
        self.right_paned_frame.grid_rowconfigure(0, weight=2)
        self.right_paned_frame.grid_rowconfigure(1, weight=1)
        self.right_paned_frame.grid_columnconfigure(0, weight=1)

        # Characteristics on top
        self.char_frame_container = customtkinter.CTkFrame(self.right_paned_frame)
        self.char_frame_container.grid(row=0, column=0, sticky="nsew")
        self.char_frame_container.grid_rowconfigure(1, weight=1)
        self.char_frame_container.grid_columnconfigure(0, weight=1)

        self.char_toolbar = customtkinter.CTkFrame(self.char_frame_container)
        self.char_toolbar.grid(row=0, column=0, padx=0, pady=0, sticky="ew")

        self.read_all_button = customtkinter.CTkButton(self.char_toolbar, text="Read All", command=self.read_all_characteristics, state="disabled")
        self.read_all_button.pack(side="left", padx=5, pady=5)

        self.clear_log_button = customtkinter.CTkButton(self.char_toolbar, text="Clear Log", command=self.clear_log)
        self.clear_log_button.pack(side="left", padx=5, pady=5)

        self.save_log_button = customtkinter.CTkButton(self.char_toolbar, text="Save Log", command=self.save_log)
        self.save_log_button.pack(side="left", padx=5, pady=5)

        self.characteristics_frame = customtkinter.CTkScrollableFrame(self.char_frame_container, label_text="Characteristics")
        self.characteristics_frame.grid(row=1, column=0, padx=0, pady=0, sticky="nsew")

        # Bottom debug window
        self.attributes_textbox = customtkinter.CTkTextbox(self.right_paned_frame)
        self.attributes_textbox.grid(row=1, column=0, padx=0, pady=(10,0), sticky="nsew")

    def _on_mouse_wheel(self, event: tkinter.Event) -> None:
        """
        Handles mouse wheel scrolling for any CTkScrollableFrame under the cursor.
        This method is designed to be cross-platform.

        Args:
            event: The mouse wheel event.
        """
        widget = self.winfo_containing(event.x_root, event.y_root)
        scrollable_widget = None

        while widget is not None:
            if isinstance(widget, customtkinter.CTkScrollableFrame):
                scrollable_widget = widget
                break
            widget = widget.master

        if scrollable_widget:
            if event.num == 4:  # Linux scroll up
                scrollable_widget._parent_canvas.yview_scroll(-1, "units")
            elif event.num == 5:  # Linux scroll down
                scrollable_widget._parent_canvas.yview_scroll(1, "units")
            else:  # Windows and macOS
                scrollable_widget._parent_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def on_closing(self) -> None:
        """Handles the window closing event."""
        self.ble_manager.shutdown()
        self.destroy()

    def device_selected(self, frame: DeviceFrame, device: BLEDevice) -> None:
        """
        Handles the selection of a device from the list.

        Args:
            frame: The UI frame of the selected device.
            device: The selected BLEDevice object.
        """
        self.selected_device = device
        for f in self.device_frames.values():
            f.configure(fg_color=customtkinter.ThemeManager.theme["CTkFrame"]["fg_color"])
        frame.configure(fg_color="green")
        self.connect_to_selected_device()

    def scan_for_devices(self) -> None:
        """Initiates a scan for nearby BLE devices."""
        self.scan_button.configure(state="disabled", text="Scanning...")
        self.clear_frame(self.devices_frame)
        self.device_frames = {}
        self.log_with_timestamp("Scan started...")
        adapter = self.adapter_combobox.get()
        adapter = adapter if adapter != "Default" else None
        try:
            timeout = float(self.scan_timeout_entry.get())
        except ValueError:
            self.log_with_timestamp("Invalid scan timeout. Please enter a number.")
            self.scan_button.configure(state="normal", text="Scan for devices")
            return
        self.ble_manager.scan_for_devices(adapter, timeout)
        self.after(int(timeout * 1000) + 500, self.on_scan_finished)

    def clear_frame(self, frame: tkinter.Frame) -> None:
        """
        Removes all child widgets from a given frame.

        Args:
            frame: The frame to clear.
        """
        for widget in frame.winfo_children():
            widget.destroy()

    def on_scan_finished(self):
        self.log_with_timestamp("Scan stopped.")
        self.scan_button.configure(state="normal", text="Scan for devices")

    def _on_device_discovered(self, device: BLEDevice, adv_data: AdvertisementData) -> None:
        """Callback for when a device is discovered."""
        self.after(0, self._populate_device_ui, device, adv_data)

    def _populate_device_ui(self, device: BLEDevice, adv_data: AdvertisementData) -> None:
        """
        Populates the UI with a discovered BLE device.

        Args:
            device: A BLEDevice object.
            adv_data: AdvertisementData for the device.
        """
        self.log_with_timestamp(f"Found device: {device.address} ({device.name or 'Unknown'}) RSSI: {adv_data.rssi}")
        frame = DeviceFrame(self.devices_frame, device, adv_data, self.device_selected)
        frame.pack(padx=5, pady=2, fill="x")
        self.device_frames[device.address] = frame

    def connect_to_selected_device(self) -> None:
        """Connects to the currently selected device."""
        if self.selected_device:
            self.log_with_timestamp(f"Connecting to {self.selected_device.address} ({self.selected_device.name})...")
            adapter = self.adapter_combobox.get()
            adapter = adapter if adapter != "Default" else None
            self.ble_manager.connect_to_device(self.selected_device.address, adapter)

    def _on_connection_status_changed(self, is_connected: bool) -> None:
        """Callback for connection status changes."""
        self.after(0, self._update_connection_ui, is_connected)

    def _update_connection_ui(self, is_connected: bool) -> None:
        """Updates the UI based on the connection status."""
        if is_connected:
            self.log_with_timestamp("Device connected.")
            self.discover_attributes()
        else:
            self.log_with_timestamp("Device disconnected.")
            self.on_disconnect_ui_update()

    def disconnect_from_device(self) -> None:
        """Initiates a manual disconnection from the connected device."""
        self.ble_manager.disconnect_from_device()

    def on_disconnect_ui_update(self) -> None:
        """Updates the UI to reflect the disconnected state."""
        if self.diff_checker_id:
            self.after_cancel(self.diff_checker_id)
            self.diff_checker_id = None
        self.disconnect_button.configure(state="disabled")
        self.read_all_button.configure(state="disabled")
        self.clear_frame(self.characteristics_frame)
        self.characteristic_frames = {}
        self.scan_button.configure(state="normal")
        self.connection_status_label.configure(text="Status: Disconnected", text_color="red")
        for frame in self.device_frames.values():
             frame.configure(fg_color=customtkinter.ThemeManager.theme["CTkFrame"]["fg_color"])

    def discover_attributes(self) -> None:
        """Discovers and displays the services and characteristics of the connected device."""
        self.clear_frame(self.characteristics_frame)
        self.characteristic_frames = {}

        cached_services_data = None
        if self.selected_device:
            cached_services_data = self.device_cache.load_device(self.selected_device.address)
            if cached_services_data:
                self.log_with_timestamp("Loading services from cache...")
                cached_services = [CachedService(s) for s in cached_services_data]
                all_characteristics = [char for service in cached_services for char in service.characteristics]
                all_characteristics.sort(key=lambda c: (c.service_uuid, c.uuid))
                self._populate_characteristic_frame(all_characteristics, service_frames={})
                self.log_with_timestamp("Finished loading from cache.")
                self._read_all_user_descriptions()

        if self.ble_manager.client:
            self.disconnect_button.configure(state="normal")
            self.read_all_button.configure(state="normal")
            self.connection_status_label.configure(text="Status: Connected", text_color="green")
            self.scan_button.configure(state="disabled")

            # Update UI from live data if no cache was found
            if not cached_services_data:
                all_characteristics = [char for service in self.ble_manager.client.services for char in service.characteristics]
                all_characteristics.sort(key=lambda c: (c.service_uuid, c.uuid))
                self._populate_characteristic_frame(all_characteristics, service_frames={})
                self._read_all_user_descriptions()

            # Start background task to check for differences
            self.diff_checker_id = self.after(100, self._check_for_attribute_diffs, cached_services_data)

    def _populate_characteristic_frame(self, characteristics: List[Union[BleakGATTCharacteristic, CachedCharacteristic]], service_frames: Dict[str, CollapsibleFrame], index: int = 0) -> None:
        """
        Populates the UI with a single characteristic frame and schedules the next one.
        This one-by-one approach with a minimal delay prevents the UI from freezing.

        Args:
            characteristics: The list of all characteristics to display.
            service_frames: A dictionary to store and reuse service frames.
            index: The index of the characteristic to process now.
        """
        if index >= len(characteristics):
            return

        char = characteristics[index]
        service_uuid = str(char.service_uuid)

        if service_uuid not in service_frames:
            service_name = GATT_SERVICES.get(service_uuid.split("-")[0].lstrip("0").lower(), "Unknown Service")
            self.log_with_timestamp(f"Service: {service_name} ({service_uuid})")
            sf = CollapsibleFrame(self.characteristics_frame, text=f"Service: {service_name} ({service_uuid})")
            sf.pack(padx=5, pady=5, fill="x")
            service_frames[service_uuid] = sf

        # Create and pack the frame for the current characteristic
        char_frame = CharacteristicFrame(
            master=service_frames[service_uuid].content_frame,
            characteristic=char,
            description=char.description,
            read_callback=self.read_characteristic,
            write_callback=self.write_characteristic,
            subscribe_callback=self.subscribe_to_characteristic,
            unsubscribe_callback=self.unsubscribe_from_characteristic,
            read_desc_callback=self.read_descriptor,
            write_desc_callback=self.write_descriptor
        )
        char_frame.pack(padx=5, pady=2, fill="x")
        self.characteristic_frames[char.handle] = char_frame

        # Schedule the creation of the next characteristic frame
        self.after(1, self._populate_characteristic_frame, characteristics, service_frames, index + 1)

    def _read_all_user_descriptions(self) -> None:
        """Reads and displays the 'User Description' for all characteristics."""
        self.log_with_timestamp("--- Reading all user descriptions ---")
        for char_frame in self.characteristic_frames.values():
            # For cached characteristics, the user description is already part of the characteristic's data
            if isinstance(char_frame.characteristic, CachedCharacteristic):
                # Find the user description from its descriptors
                for desc in char_frame.characteristic.descriptors:
                    if desc.uuid == "00002901-0000-1000-8000-00805f9b34fb":
                        # The value is not stored in the cache, so we still need to read it
                        self.read_descriptor(desc, char_frame.user_description_label)
                        break
            else:
                for desc in char_frame.characteristic.descriptors:
                    if desc.uuid == "00002901-0000-1000-8000-00805f9b34fb":
                        self.read_descriptor(desc, char_frame.user_description_label)
                        break

    def reset_device_buttons(self) -> None:
        """Resets the visual state of all device buttons."""
        for frame in self.device_frames.values():
            frame.configure(fg_color=customtkinter.ThemeManager.theme["CTkFrame"]["fg_color"])

    def clear_log(self) -> None:
        """Clears the debug log text box."""
        self.attributes_textbox.delete("1.0", "end")

    def save_log(self) -> None:
        """Saves the content of the debug log to a file."""
        log_content = self.attributes_textbox.get("1.0", "end")
        filepath = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")], title="Save Log File")
        if filepath:
            try:
                with open(filepath, "w") as f:
                    f.write(log_content)
                self.log_with_timestamp(f"Log saved to {filepath}")
            except IOError as e:
                self.log_with_timestamp(f"Error saving log: {e}")

    def log_message(self, message: str) -> None:
        """
        Appends a message to the debug log.

        Args:
            message: The message to log.
        """
        self.attributes_textbox.insert("end", message + "\n")
        self.attributes_textbox.see("end")

    def _log_on_main_thread(self, message: str) -> None:
        """
        Schedules a message to be logged on the main GUI thread.

        Args:
            message: The message to log.
        """
        self.after(0, self.log_message, message)

    def log_with_timestamp(self, message: str) -> None:
        """
        Logs a message with a timestamp prepended.

        Args:
            message: The message to log.
        """
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self._log_on_main_thread(f"[{timestamp}] {message}")

    def read_characteristic(self, characteristic: BleakGATTCharacteristic, char_frame: CharacteristicFrame) -> None:
        """
        Initiates a read operation for a characteristic.

        Args:
            characteristic: The characteristic to read from.
            char_frame: The UI frame for the characteristic.
        """
        def on_read(value: Optional[bytes]):
            if value is not None:
                self.after(0, lambda: char_frame.update_value(value))
                self.log_with_timestamp(f"Value read from {characteristic.uuid}: {value.hex()}")
                self.after(0, lambda: char_frame.read_value_entry.configure(fg_color="green"))
                self.after(500, lambda: char_frame.read_value_entry.configure(fg_color=customtkinter.ThemeManager.theme["CTkEntry"]["fg_color"]))

        self.ble_manager.read_characteristic(characteristic.uuid, on_read)

    def write_characteristic(self, characteristic: BleakGATTCharacteristic, char_frame: CharacteristicFrame) -> None:
        """
        Initiates a write operation for a characteristic.

        Args:
            characteristic: The characteristic to write to.
            char_frame: The UI frame for the characteristic.
        """
        value_str = char_frame.write_entry.get()
        write_mode = char_frame.write_display_mode
        try:
            write_value = bytes.fromhex(value_str) if write_mode == "hex" else value_str.encode("utf-8")
        except ValueError:
            self.log_with_timestamp(f"Invalid hex value for write on {characteristic.uuid}")
            self.after(0, lambda: char_frame.set_write_status_color("light coral"))
            return

        def on_write(success: bool):
            if success:
                self.log_with_timestamp(f"Value written to {characteristic.uuid}: {write_value.hex()}")
                self.after(0, char_frame._reset_write_status_color)
                if "read" in characteristic.properties:
                    self.log_with_timestamp(f"Automatically reading back from {characteristic.uuid}")
                    self.read_characteristic(characteristic, char_frame)
            else:
                self.log_with_timestamp(f"Write Error on {characteristic.uuid}")
                self.after(0, lambda: char_frame.set_write_status_color("light coral"))

        self.ble_manager.write_characteristic(characteristic.uuid, write_value, on_write)

    def read_all_characteristics(self) -> None:
        """Initiates a read operation for all readable characteristics."""
        self.log_with_timestamp("--- Reading all readable characteristics ---")
        for char_frame in self.characteristic_frames.values():
            if "read" in char_frame.characteristic.properties:
                self.read_characteristic(char_frame.characteristic, char_frame)

    def notification_handler(self, characteristic: BleakGATTCharacteristic, data: bytes) -> None:
        """
        Handles incoming notifications from a characteristic.

        Args:
            characteristic: The characteristic sending the notification.
            data: The notification data.
        """
        self.log_with_timestamp(f"Notification from {characteristic.uuid}: {data.hex()}")
        if characteristic.handle in self.characteristic_frames:
            frame = self.characteristic_frames[characteristic.handle]
            self.after(0, lambda: frame.update_value(data))

    def subscribe_to_characteristic(self, characteristic: BleakGATTCharacteristic, char_frame: CharacteristicFrame) -> None:
        """
        Subscribes to notifications for a characteristic.

        Args:
            characteristic: The characteristic to subscribe to.
            char_frame: The UI frame for the characteristic.
        """
        self.ble_manager.subscribe_to_characteristic(characteristic.uuid)
        self.log_with_timestamp(f"Subscribed to {characteristic.uuid}")

    def unsubscribe_from_characteristic(self, characteristic: BleakGATTCharacteristic, char_frame: CharacteristicFrame) -> None:
        """
        Unsubscribes from notifications for a characteristic.

        Args:
            characteristic: The characteristic to unsubscribe from.
            char_frame: The UI frame for the characteristic.
        """
        self.ble_manager.unsubscribe_from_characteristic(characteristic.uuid)
        self.log_with_timestamp(f"Unsubscribed from {characteristic.uuid}")

    def read_descriptor(self, descriptor: BleakGATTDescriptor, desc_frame: Union['DescriptorFrame', customtkinter.CTkLabel]) -> None:
        """
        Initiates a read operation for a descriptor.

        Args:
            descriptor: The descriptor to read from.
            desc_frame: The UI frame for the descriptor.
        """
        def on_read(value: Optional[bytes]):
            if value is not None:
                if isinstance(desc_frame, customtkinter.CTkLabel):
                     self.after(0, lambda: desc_frame.configure(text=f"User Description: {value.decode('utf-8')}"))
                else:
                    self.after(0, lambda: desc_frame.update_value(value))
                self.log_with_timestamp(f"Value read from {descriptor.uuid}: {value.hex()}")

        self.ble_manager.read_descriptor(descriptor.handle, on_read)

    def write_descriptor(self, descriptor: BleakGATTDescriptor, desc_frame: DescriptorFrame) -> None:
        """
        Initiates a write operation for a descriptor.

        Args:
            descriptor: The descriptor to write to.
            desc_frame: The UI frame for the descriptor.
        """
        value_str = desc_frame.write_entry.get()
        try:
            write_value = bytes.fromhex(value_str)
        except ValueError:
            self.log_with_timestamp(f"Invalid hex value for write on {descriptor.uuid}")
            return

        def on_write(success: bool):
            if success:
                self.log_with_timestamp(f"Value written to {descriptor.uuid}: {write_value.hex()}")
                self.read_descriptor(descriptor, desc_frame)
            else:
                self.log_with_timestamp(f"Write Error on {descriptor.uuid}")

        self.ble_manager.write_descriptor(descriptor.handle, write_value, on_write)

    def _check_for_attribute_diffs(self, cached_services: Optional[List[Dict[str, Any]]]) -> None:
        """Checks for differences between cached and live attributes."""
        if self.ble_manager.client:
            self.log_with_timestamp("Checking for attribute differences in the background...")
            live_services = [service_to_dict(s) for s in self.ble_manager.client.services]

            if cached_services:
                diffs = self.device_cache.compare_services(cached_services, live_services)
                if diffs:
                    self.log_with_timestamp("Differences found between cache and live data:")
                    for diff in diffs:
                        self.log_with_timestamp(f"- {diff}")
                    self.log_with_timestamp("Refreshing UI with live data...")
                    self.discover_attributes()
                else:
                    self.log_with_timestamp("No differences found.")

            self.device_cache.save_device(self.ble_manager.client)

    def discover_adapters(self) -> None:
        """Discovers available Bluetooth adapters and populates the dropdown."""
        adapters = ["Default"]
        if platform.system() == "Linux":
            try:
                result = subprocess.run(['hciconfig'], capture_output=True, text=True, check=True)
                adapters.extend(re.findall(r'^(hci\d+)', result.stdout, re.MULTILINE))
            except (FileNotFoundError, subprocess.CalledProcessError):
                pass
        self.adapter_combobox.configure(values=adapters)
        self.adapter_combobox.set("Default")

    def on_adapter_selected(self, choice: str) -> None:
        """
        Handles the selection of a Bluetooth adapter.

        Args:
            choice: The name of the selected adapter.
        """
        self.log_with_timestamp(f"Adapter selected: {choice}")
        if platform.system() == "Linux" and choice != "Default":
            try:
                result = subprocess.run(['hciconfig', '-a', choice], capture_output=True, text=True, check=True)
                self.log_with_timestamp(f"--- Adapter Info for {choice} ---\n{result.stdout.strip()}\n--------------------")
            except (FileNotFoundError, subprocess.CalledProcessError) as e:
                self.log_with_timestamp(f"Could not get info for adapter {choice}: {e}")

    def filter_devices(self, event: Optional[tkinter.Event] = None) -> None:
        """
        Filters the device list based on the text in the search entry.

        Args:
            event: The key release event (optional).
        """
        search_term = self.search_entry.get().lower()
        for device_frame in self.device_frames.values():
            device = device_frame.device
            device_name = (device.name or "Unknown").lower()
            device_address = device.address.lower()
            if search_term in device_name or search_term in device_address:
                device_frame.pack(padx=5, pady=2, fill="x")
            else:
                device_frame.pack_forget()

if __name__ == "__main__":
    app = App()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
