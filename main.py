import customtkinter
import bleak
import asyncio
import threading
import platform
import subprocess
import re
import tkinter
from datetime import datetime
from tkinter import filedialog
from typing import Dict, Optional, List, Tuple, Any, Coroutine

from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.descriptor import BleakGATTDescriptor
from bleak.exc import BleakError

from descriptor_frame import DescriptorFrame
from characteristic_frame import CharacteristicFrame
from device_frame import DeviceFrame
from collapsible_frame import CollapsibleFrame


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

        # Top bar for controls
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

        # Left column for devices
        self.devices_frame_container = customtkinter.CTkFrame(self)
        self.devices_frame_container.grid(row=1, column=0, rowspan=2, padx=10, pady=(0,10), sticky="nsew")
        self.devices_frame_container.grid_rowconfigure(1, weight=1)

        self.search_entry = customtkinter.CTkEntry(self.devices_frame_container, placeholder_text="Filter devices")
        self.search_entry.grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        self.search_entry.bind("<KeyRelease>", self.filter_devices)

        self.devices_frame = customtkinter.CTkScrollableFrame(self.devices_frame_container, label_text="Nearby Devices")
        self.devices_frame.grid(row=1, column=0, padx=0, pady=0, sticky="nsew")

        # Right column for characteristics and debug
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

        self.client: Optional[bleak.BleakClient] = None
        self.selected_device: Optional[BLEDevice] = None
        self.device_frames: Dict[str, DeviceFrame] = {}
        self.characteristic_frames: Dict[int, CharacteristicFrame] = {}

        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.run_async_loop, daemon=True)
        self.thread.start()

        self.after(100, self.discover_adapters)

        self.bind_all("<MouseWheel>", self._on_mouse_wheel)

    def _on_mouse_wheel(self, event: tkinter.Event) -> None:
        """
        Handles mouse wheel scrolling for any CTkScrollableFrame under the cursor.

        Args:
            event: The mouse wheel event.
        """
        widget = self.winfo_containing(event.x_root, event.y_root)
        while widget is not None:
            if isinstance(widget, customtkinter.CTkScrollableFrame):
                widget._parent_canvas.yview_scroll(-1 * int(event.delta/120), "units")
                break
            widget = widget.master

    def on_closing(self) -> None:
        """Handles the window closing event."""
        if self.client and self.client.is_connected:
            future = asyncio.run_coroutine_threadsafe(self.client.disconnect(), self.loop)
            try:
                future.result(timeout=2.0)
            except (asyncio.TimeoutError, BleakError):
                pass
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.thread.join()
        self.destroy()

    def run_async_loop(self) -> None:
        """Runs the asyncio event loop in a separate thread."""
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

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
        adapter = self.adapter_combobox.get()
        try:
            timeout = float(self.scan_timeout_entry.get())
        except ValueError:
            self.log_with_timestamp("Invalid scan timeout. Please enter a number.")
            self.scan_button.configure(state="normal", text="Scan for devices")
            return
        asyncio.run_coroutine_threadsafe(self.discover_devices(adapter, timeout), self.loop)

    def clear_frame(self, frame: tkinter.Frame) -> None:
        """
        Removes all child widgets from a given frame.

        Args:
            frame: The frame to clear.
        """
        for widget in frame.winfo_children():
            widget.destroy()

    async def discover_devices(self, adapter_name: str, timeout: float) -> None:
        """
        Scans for BLE devices and populates the UI with the results.

        Args:
            adapter_name: The name of the Bluetooth adapter to use.
            timeout: The duration of the scan in seconds.
        """
        self.after(0, lambda: self.clear_frame(self.devices_frame))
        self.device_frames = {}
        self.log_with_timestamp("Scan started...")

        adapter = adapter_name if adapter_name != "Default" else None
        scanner_kwargs = {"adapter": adapter} if adapter else {}

        try:
            discovered_devices_dict = await bleak.BleakScanner.discover(timeout=timeout, return_adv=True, **scanner_kwargs)
            sorted_devices = sorted(discovered_devices_dict.values(), key=lambda item: item[1].rssi, reverse=True)
            self.after(0, self._populate_devices_ui, sorted_devices)
        except BleakError as e:
            self.log_with_timestamp(f"Scanning Error: {e}")

        self.log_with_timestamp("Scan stopped.")
        self.after(0, lambda: self.scan_button.configure(state="normal", text="Scan for devices"))

    def _populate_devices_ui(self, devices: List[Tuple[BLEDevice, AdvertisementData]]) -> None:
        """
        Populates the UI with the discovered BLE devices.

        Args:
            devices: A list of tuples containing BLEDevice and AdvertisementData.
        """
        for device, adv_data in devices:
            self.log_with_timestamp(f"Found device: {device.address} ({device.name or 'Unknown'}) RSSI: {adv_data.rssi}")
            frame = DeviceFrame(self.devices_frame, device, adv_data, self.device_selected)
            frame.pack(padx=5, pady=2, fill="x")
            self.device_frames[device.address] = frame

    def connect_to_selected_device(self) -> None:
        """Connects to the currently selected device."""
        if self.selected_device:
            asyncio.run_coroutine_threadsafe(self._manage_connection(), self.loop)

    async def _manage_connection(self) -> None:
        """Manages the connection to the selected device, including disconnection and reconnection."""
        self.log_with_timestamp(f"Connecting to {self.selected_device.name}...")

        if self.client and self.client.is_connected:
            await self.client.disconnect()

        adapter = self.adapter_combobox.get()
        adapter = adapter if adapter != "Default" else None
        client_kwargs = {"adapter": adapter} if adapter else {}
        self.client = bleak.BleakClient(self.selected_device, disconnected_callback=self._on_disconnect, **client_kwargs)

        await self.discover_attributes()

    def _on_disconnect(self, client: bleak.BleakClient) -> None:
        """
        Handles the device disconnection event.

        Args:
            client: The BleakClient instance that disconnected.
        """
        self.log_with_timestamp("Device disconnected.")
        self.after(0, self.on_disconnect_ui_update)
        if self.selected_device:
            self.log_with_timestamp("Attempting to reconnect...")
            asyncio.run_coroutine_threadsafe(self._manage_connection(), self.loop)

    def disconnect_from_device(self) -> None:
        """Initiates a manual disconnection from the connected device."""
        if self.client:
            asyncio.run_coroutine_threadsafe(self.disconnect(), self.loop)

    async def disconnect(self) -> None:
        """The core disconnection logic."""
        if self.client:
            await self.client.disconnect()
        self.after(0, self.on_disconnect_ui_update)

    def on_disconnect_ui_update(self) -> None:
        """Updates the UI to reflect the disconnected state."""
        self.disconnect_button.configure(state="disabled")
        self.read_all_button.configure(state="disabled")
        self.clear_frame(self.characteristics_frame)
        self.characteristic_frames = {}
        self.scan_button.configure(state="normal")
        self.connection_status_label.configure(text="Status: Disconnected", text_color="red")
        for frame in self.device_frames.values():
             frame.configure(fg_color=customtkinter.ThemeManager.theme["CTkFrame"]["fg_color"])

    async def discover_attributes(self) -> None:
        """Discovers and displays the services and characteristics of the connected device."""
        self.after(0, lambda: self.clear_frame(self.characteristics_frame))
        self.characteristic_frames = {}

        try:
            if self.client:
                await self.client.connect()
                self.after(0, lambda: self.disconnect_button.configure(state="normal"))
                self.after(0, lambda: self.read_all_button.configure(state="normal"))
                self.after(0, lambda: self.connection_status_label.configure(text="Status: Connected", text_color="green"))
                self.after(0, lambda: self.scan_button.configure(state="disabled"))

                all_characteristics = [char for service in self.client.services for char in service.characteristics]
                all_characteristics.sort(key=lambda c: (c.service_uuid, c.uuid))

                self.after(0, self._populate_characteristics_in_batches, all_characteristics)
                asyncio.run_coroutine_threadsafe(self._read_all_user_descriptions(), self.loop)
        except BleakError as e:
            self.log_with_timestamp(f"Connection Error: {e}")
            self.after(0, self.reset_device_buttons)
            self.after(0, lambda: self.scan_button.configure(state="normal"))
        except asyncio.TimeoutError:
            self.log_with_timestamp("Connection timed out.")
            self.after(0, self.reset_device_buttons)
            self.after(0, lambda: self.scan_button.configure(state="normal"))
        except Exception as e:
            self.log_with_timestamp(f"An unexpected error occurred: {e}")
            self.after(0, self.reset_device_buttons)
            self.after(0, lambda: self.scan_button.configure(state="normal"))

    def _populate_characteristics_in_batches(self, characteristics: List[BleakGATTCharacteristic], index: int = 0, batch_size: int = 10, service_frames: Optional[Dict[str, CollapsibleFrame]] = None) -> None:
        """
        Populates the UI with characteristics in batches to avoid freezing the GUI.

        Args:
            characteristics: The list of characteristics to display.
            index: The starting index for the current batch.
            batch_size: The number of characteristics to process in each batch.
            service_frames: A dictionary to store service frames.
        """
        if service_frames is None:
            service_frames = {}
        if index >= len(characteristics):
            return

        batch = characteristics[index : index + batch_size]
        for char in batch:
            service_uuid = str(char.service_uuid)
            if service_uuid not in service_frames:
                self.log_with_timestamp(f"Service: {service_uuid}")
                sf = CollapsibleFrame(self.characteristics_frame, text=f"Service: {service_uuid}")
                sf.pack(padx=5, pady=5, fill="x")
                service_frames[service_uuid] = sf

            char_frame = CharacteristicFrame(service_frames[service_uuid].content_frame, char, char.description, self.read_characteristic, self.write_characteristic, self.subscribe_to_characteristic, self.unsubscribe_from_characteristic, self.read_descriptor, self.write_descriptor)
            char_frame.pack(padx=5, pady=2, fill="x")
            self.characteristic_frames[char.handle] = char_frame

        next_index = index + batch_size
        if next_index < len(characteristics):
            self.after(50, self._populate_characteristics_in_batches, characteristics, next_index, batch_size, service_frames)

    async def _read_all_user_descriptions(self) -> None:
        """Reads and displays the 'User Description' for all characteristics."""
        self.log_with_timestamp("--- Reading all user descriptions ---")
        for char_frame in self.characteristic_frames.values():
            char = char_frame.characteristic
            try:
                for desc in char.descriptors:
                    if desc.uuid == "00002901-0000-1000-8000-00805f9b34fb":
                        if self.client:
                            value = await self.client.read_gatt_descriptor(desc.handle)
                            desc_text = value.decode('utf-8')
                            self.after(0, lambda cf=char_frame, d=desc_text: cf.user_description_label.configure(text=f"User Description: {d}"))
                            self.log_with_timestamp(f"Read User Description for {char.uuid}: {desc_text}")
                            break
            except BleakError as e:
                self.log_with_timestamp(f"Error reading user description for {char.uuid}: {e}")
            except Exception as e:
                self.log_with_timestamp(f"Unexpected error reading user description for {char.uuid}: {e}")

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
        if self.client:
            asyncio.run_coroutine_threadsafe(self.read_char(characteristic, char_frame), self.loop)

    async def read_char(self, characteristic: BleakGATTCharacteristic, char_frame: CharacteristicFrame) -> None:
        """
        The core logic for reading a characteristic's value.

        Args:
            characteristic: The characteristic to read from.
            char_frame: The UI frame for the characteristic.
        """
        try:
            if self.client:
                value = await self.client.read_gatt_char(characteristic.uuid)
                self.after(0, lambda: char_frame.update_value(value))
                self.log_with_timestamp(f"Value read from {characteristic.uuid}: {value.hex()}")
                self.after(0, lambda: char_frame.read_value_entry.configure(fg_color="green"))
                self.after(500, lambda: char_frame.read_value_entry.configure(fg_color=customtkinter.ThemeManager.theme["CTkEntry"]["fg_color"]))
        except BleakError as e:
            self.log_with_timestamp(f"Read Error on {characteristic.uuid}: {e}")
        except Exception as e:
            self.log_with_timestamp(f"Unexpected read error on {characteristic.uuid}: {e}")

    def write_characteristic(self, characteristic: BleakGATTCharacteristic, char_frame: CharacteristicFrame) -> None:
        """
        Initiates a write operation for a characteristic.

        Args:
            characteristic: The characteristic to write to.
            char_frame: The UI frame for the characteristic.
        """
        if self.client:
            value = char_frame.write_entry.get()
            write_mode = char_frame.write_display_mode
            asyncio.run_coroutine_threadsafe(self.write_char(characteristic, value, write_mode, char_frame), self.loop)

    def read_all_characteristics(self) -> None:
        """Initiates a read operation for all readable characteristics."""
        self.log_with_timestamp("--- Reading all readable characteristics ---")
        for char_frame in self.characteristic_frames.values():
            if "read" in char_frame.characteristic.properties:
                self.read_characteristic(char_frame.characteristic, char_frame)

    async def write_char(self, characteristic: BleakGATTCharacteristic, value: str, mode: str, char_frame: CharacteristicFrame) -> None:
        """
        The core logic for writing a characteristic's value.

        Args:
            characteristic: The characteristic to write to.
            value: The value to write, as a string.
            mode: The format of the value ("hex" or "ascii").
            char_frame: The UI frame for the characteristic.
        """
        try:
            write_value = bytes.fromhex(value) if mode == "hex" else value.encode("utf-8")
            if self.client:
                await self.client.write_gatt_char(characteristic.uuid, write_value)
                self.log_with_timestamp(f"Value written to {characteristic.uuid}: {write_value.hex()}")
                self.after(0, char_frame._reset_write_status_color)
                if "read" in characteristic.properties:
                    self.log_with_timestamp(f"Automatically reading back from {characteristic.uuid}")
                    await self.read_char(characteristic, char_frame)
        except ValueError:
            self.log_with_timestamp(f"Invalid hex value for write on {characteristic.uuid}")
            self.after(0, lambda: char_frame.set_write_status_color("light coral"))
        except BleakError as e:
            self.log_with_timestamp(f"Write Error on {characteristic.uuid}: {e}")
            self.after(0, lambda: char_frame.set_write_status_color("light coral"))
        except Exception as e:
            self.log_with_timestamp(f"Unexpected write error on {characteristic.uuid}: {e}")
            self.after(0, lambda: char_frame.set_write_status_color("light coral"))

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
        if self.client:
            asyncio.run_coroutine_threadsafe(self.client.start_notify(characteristic.uuid, self.notification_handler), self.loop)
            self.log_with_timestamp(f"Subscribed to {characteristic.uuid}")

    def unsubscribe_from_characteristic(self, characteristic: BleakGATTCharacteristic, char_frame: CharacteristicFrame) -> None:
        """
        Unsubscribes from notifications for a characteristic.

        Args:
            characteristic: The characteristic to unsubscribe from.
            char_frame: The UI frame for the characteristic.
        """
        if self.client:
            asyncio.run_coroutine_threadsafe(self.client.stop_notify(characteristic.uuid), self.loop)
            self.log_with_timestamp(f"Unsubscribed from {characteristic.uuid}")

    def read_descriptor(self, descriptor: BleakGATTDescriptor, desc_frame: DescriptorFrame) -> None:
        """
        Initiates a read operation for a descriptor.

        Args:
            descriptor: The descriptor to read from.
            desc_frame: The UI frame for the descriptor.
        """
        if self.client:
            asyncio.run_coroutine_threadsafe(self.read_desc(descriptor, desc_frame), self.loop)

    async def read_desc(self, descriptor: BleakGATTDescriptor, desc_frame: DescriptorFrame) -> None:
        """
        The core logic for reading a descriptor's value.

        Args:
            descriptor: The descriptor to read from.
            desc_frame: The UI frame for the descriptor.
        """
        try:
            if self.client:
                value = await self.client.read_gatt_descriptor(descriptor.handle)
                self.after(0, lambda: desc_frame.update_value(value))
                self.log_with_timestamp(f"Value read from {descriptor.uuid}: {value.hex()}")
        except BleakError as e:
            self.log_with_timestamp(f"Read Error on {descriptor.uuid}: {e}")
        except Exception as e:
            self.log_with_timestamp(f"Unexpected read error on {descriptor.uuid}: {e}")

    def write_descriptor(self, descriptor: BleakGATTDescriptor, desc_frame: DescriptorFrame) -> None:
        """
        Initiates a write operation for a descriptor.

        Args:
            descriptor: The descriptor to write to.
            desc_frame: The UI frame for the descriptor.
        """
        if self.client:
            value = desc_frame.write_entry.get()
            asyncio.run_coroutine_threadsafe(self.write_desc(descriptor, value, desc_frame), self.loop)

    async def write_desc(self, descriptor: BleakGATTDescriptor, value: str, desc_frame: DescriptorFrame) -> None:
        """
        The core logic for writing a descriptor's value.

        Args:
            descriptor: The descriptor to write to.
            value: The value to write, as a hex string.
            desc_frame: The UI frame for the descriptor.
        """
        try:
            write_value = bytes.fromhex(value)
            if self.client:
                await self.client.write_gatt_descriptor(descriptor.handle, write_value)
                self.log_with_timestamp(f"Value written to {descriptor.uuid}: {write_value.hex()}")
                await self.read_desc(descriptor, desc_frame)
        except ValueError:
            self.log_with_timestamp(f"Invalid hex value for write on {descriptor.uuid}")
        except BleakError as e:
            self.log_with_timestamp(f"Write Error on {descriptor.uuid}: {e}")
        except Exception as e:
            self.log_with_timestamp(f"Unexpected write error on {descriptor.uuid}: {e}")

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
