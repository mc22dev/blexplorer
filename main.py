import customtkinter
import bleak
import asyncio
import threading
import platform
import subprocess
import re
from datetime import datetime
from tkinter import filedialog
from descriptor_frame import DescriptorFrame
from characteristic_frame import CharacteristicFrame
from device_frame import DeviceFrame
from collapsible_frame import CollapsibleFrame
import struct




class App(customtkinter.CTk):
    def __init__(self):
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

        self.disconnect_button = customtkinter.CTkButton(self.adapter_frame, text="Disconnect", command=self.disconnect_from_device, state="disabled")
        self.disconnect_button.grid(row=0, column=4, padx=(0,10), pady=10)

        self.connection_status_label = customtkinter.CTkLabel(self.adapter_frame, text="Status: Disconnected", text_color="red")
        self.connection_status_label.grid(row=0, column=5, padx=10, pady=10)

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

        self.client = None
        self.selected_device = None
        self.device_frames = {}
        self.characteristic_frames = {}

        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.run_async_loop, daemon=True)
        self.thread.start()

        self.after(100, self.discover_adapters)

        self.bind_all("<MouseWheel>", self._on_mouse_wheel)

    def _on_mouse_wheel(self, event):
        # This is a bit of a hack to scroll the scrollable frame under the mouse pointer
        # It works by finding the widget under the pointer and then finding its scrollable parent
        widget = self.winfo_containing(event.x_root, event.y_root)
        while widget is not None:
            if isinstance(widget, customtkinter.CTkScrollableFrame):
                widget._parent_canvas.yview_scroll(-1 * int(event.delta/120), "units")
                break
            widget = widget.master

    def on_closing(self):
        if self.client and self.client.is_connected:
            future = asyncio.run_coroutine_threadsafe(self.client.disconnect(), self.loop)
            try:
                future.result(timeout=2.0)
            except (asyncio.TimeoutError, bleak.exc.BleakError):
                pass
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.thread.join()
        self.destroy()

    def run_async_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def device_selected(self, device, frame):
        self.selected_device = device
        for f in self.device_frames.values():
            f.configure(fg_color=customtkinter.ThemeManager.theme["CTkFrame"]["fg_color"])
        frame.configure(fg_color="green")

        self.connect_to_selected_device()

    def scan_for_devices(self):
        self.scan_button.configure(state="disabled", text="Scanning...")
        adapter = self.adapter_combobox.get()
        asyncio.run_coroutine_threadsafe(self.discover_devices(adapter), self.loop)

    def clear_frame(self, frame):
        for widget in frame.winfo_children():
            widget.destroy()

    async def discover_devices(self, adapter_name):
        self.after(0, lambda: self.clear_frame(self.devices_frame))
        self.device_frames = {}
        self.log_with_timestamp("Scan started...")

        adapter = adapter_name if adapter_name != "Default" else None
        scanner_kwargs = {"adapter": adapter} if adapter else {}

        try:
            discovered_devices_dict = await bleak.BleakScanner.discover(timeout=5.0, return_adv=True, **scanner_kwargs)
            # Sort devices by RSSI (strongest signal first)
            sorted_devices = sorted(discovered_devices_dict.values(), key=lambda item: item[1].rssi, reverse=True)
            self.after(0, self._populate_devices_ui, sorted_devices)
        except bleak.exc.BleakError as e:
            self.log_with_timestamp(f"Scanning Error: {e}")

        self.log_with_timestamp("Scan stopped.")
        self.after(0, lambda: self.scan_button.configure(state="normal", text="Scan for devices"))

    def _populate_devices_ui(self, devices):
        for device, adv_data in devices:
            self.log_with_timestamp(f"Found device: {device.address} ({device.name or 'Unknown'}) RSSI: {adv_data.rssi}")
            frame = DeviceFrame(self.devices_frame, device, adv_data, self.device_selected)
            frame.pack(padx=5, pady=2, fill="x")
            self.device_frames[device.address] = frame

    def connect_to_selected_device(self):
        if self.selected_device:
            asyncio.run_coroutine_threadsafe(self._manage_connection(), self.loop)

    async def _manage_connection(self):
        self.log_with_timestamp(f"Connecting to {self.selected_device.name}...")

        if self.client and self.client.is_connected:
            await self.client.disconnect()

        adapter = self.adapter_combobox.get()
        if adapter == "Default":
            adapter = None
        client_kwargs = {"adapter": adapter} if adapter else {}
        self.client = bleak.BleakClient(self.selected_device, disconnected_callback=self._on_disconnect, **client_kwargs)

        await self.discover_attributes()

    def _on_disconnect(self, client):
        self.log_with_timestamp("Device disconnected.")
        self.after(0, self.on_disconnect_ui_update)
        # Attempt to reconnect
        if self.selected_device:
            self.log_with_timestamp("Attempting to reconnect...")
            asyncio.run_coroutine_threadsafe(self._manage_connection(), self.loop)

    def disconnect_from_device(self):
        if self.client:
            asyncio.run_coroutine_threadsafe(self.disconnect(), self.loop)

    async def disconnect(self):
        await self.client.disconnect()
        self.after(0, self.on_disconnect_ui_update)

    def on_disconnect_ui_update(self):
        self.disconnect_button.configure(state="disabled")
        self.read_all_button.configure(state="disabled")
        self.clear_frame(self.characteristics_frame)
        self.characteristic_frames = {}
        self.scan_button.configure(state="normal")
        self.connection_status_label.configure(text="Status: Disconnected", text_color="red")
        for frame in self.device_frames.values():
             frame.configure(fg_color=customtkinter.ThemeManager.theme["CTkFrame"]["fg_color"])

    async def discover_attributes(self):
        self.after(0, lambda: self.clear_frame(self.characteristics_frame))
        self.characteristic_frames = {}

        try:
            await self.client.connect()
            self.after(0, lambda: self.disconnect_button.configure(state="normal"))
            self.after(0, lambda: self.read_all_button.configure(state="normal"))
            self.after(0, lambda: self.connection_status_label.configure(text="Status: Connected", text_color="green"))
            self.after(0, lambda: self.scan_button.configure(state="disabled"))

            # Instead of creating all widgets at once, gather them and process in batches
            all_characteristics = []
            for service in self.client.services:
                all_characteristics.extend(service.characteristics)

            # Sort all characteristics by service UUID, then characteristic UUID
            all_characteristics.sort(key=lambda c: (c.service_uuid, c.uuid))

            self.after(0, self._populate_characteristics_in_batches, all_characteristics)

            # Asynchronously read all user descriptions
            asyncio.run_coroutine_threadsafe(self._read_all_user_descriptions(), self.loop)

        except Exception as e:
            self.log_with_timestamp(f"Connection Error: {e}")
            self.after(0, self.reset_device_buttons)
            self.after(0, lambda: self.scan_button.configure(state="normal"))

    def _populate_characteristics_in_batches(self, characteristics, index=0, batch_size=10, service_frames=None):
        if service_frames is None:
            service_frames = {}

        if index >= len(characteristics):
            return

        batch = characteristics[index : index + batch_size]

        for characteristic in batch:
            service_uuid = characteristic.service_uuid
            if service_uuid not in service_frames:
                self.log_with_timestamp(f"Service: {service_uuid}")
                service_frame = CollapsibleFrame(self.characteristics_frame, text=f"Service: {service_uuid}")
                service_frame.pack(padx=5, pady=5, fill="x")
                service_frames[service_uuid] = service_frame
            else:
                service_frame = service_frames[service_uuid]

            char_frame = CharacteristicFrame(service_frame.content_frame, characteristic, characteristic.description, self.read_characteristic, self.write_characteristic, self.subscribe_to_characteristic, self.unsubscribe_from_characteristic, self.read_descriptor, self.write_descriptor)
            char_frame.pack(padx=5, pady=2, fill="x")
            self.characteristic_frames[characteristic.handle] = char_frame

        # Schedule the next batch
        next_index = index + batch_size
        if next_index < len(characteristics):
            self.after(50, self._populate_characteristics_in_batches, characteristics, next_index, batch_size, service_frames)

    async def _read_all_user_descriptions(self):
        self.log_with_timestamp("--- Reading all user descriptions ---")
        for char_frame in self.characteristic_frames.values():
            characteristic = char_frame.characteristic
            try:
                for descriptor in characteristic.descriptors:
                    if descriptor.uuid == "00002901-0000-1000-8000-00805f9b34fb":
                        descriptor_value = await self.client.read_gatt_descriptor(descriptor.handle)
                        user_description = descriptor_value.decode('utf-8')
                        self.after(0, lambda cf=char_frame, desc=user_description: cf.user_description_label.configure(text=f"User Description: {desc}"))
                        self.log_with_timestamp(f"Read User Description for {characteristic.uuid}: {user_description}")
                        break
            except Exception as e:
                self.log_with_timestamp(f"Error reading user description for {characteristic.uuid}: {e}")

    def reset_device_buttons(self):
        for frame in self.device_frames.values():
            frame.configure(fg_color=None)

    def clear_log(self):
        self.attributes_textbox.delete("1.0", "end")

    def save_log(self):
        log_content = self.attributes_textbox.get("1.0", "end")
        filepath = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
            title="Save Log File"
        )
        if filepath:
            try:
                with open(filepath, "w") as f:
                    f.write(log_content)
                self.log_with_timestamp(f"Log saved to {filepath}")
            except Exception as e:
                self.log_with_timestamp(f"Error saving log: {e}")

    def log_message(self, message):
        self.attributes_textbox.insert("end", message + "\n")
        self.attributes_textbox.see("end")

    def _log_on_main_thread(self, message):
        self.after(0, self.log_message, message)

    def log_with_timestamp(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self._log_on_main_thread(f"[{timestamp}] {message}")

    def read_characteristic(self, characteristic, char_frame):
        if self.client:
            asyncio.run_coroutine_threadsafe(self.read_char(characteristic, char_frame), self.loop)

    async def read_char(self, characteristic, char_frame):
        try:
            value = await self.client.read_gatt_char(characteristic.uuid)
            self.after(0, lambda: char_frame.update_value(value))
            self.log_with_timestamp(f"Value read from {characteristic.uuid}: {value.hex()}")
            # Brief highlight on successful read
            self.after(0, lambda: char_frame.read_value_entry.configure(fg_color="green"))
            self.after(500, lambda: char_frame.read_value_entry.configure(fg_color=customtkinter.ThemeManager.theme["CTkEntry"]["fg_color"]))

        except Exception as e:
            self.log_with_timestamp(f"Read Error on {characteristic.uuid}: {e}")

    def write_characteristic(self, characteristic, char_frame):
        if self.client:
            value = char_frame.write_entry.get()
            write_mode = char_frame.write_display_mode
            asyncio.run_coroutine_threadsafe(self.write_char(characteristic, value, write_mode, char_frame), self.loop)

    def read_all_characteristics(self):
        self.log_with_timestamp("--- Reading all readable characteristics ---")
        for char_frame in self.characteristic_frames.values():
            if "read" in char_frame.characteristic.properties:
                self.read_characteristic(char_frame.characteristic, char_frame)

    async def write_char(self, characteristic, value, mode, char_frame):
        try:
            if mode == "hex":
                write_value = bytes.fromhex(value)
            else:  # ascii
                write_value = value.encode("utf-8")

            await self.client.write_gatt_char(characteristic.uuid, write_value)
            self.log_with_timestamp(f"Value written to {characteristic.uuid}: {write_value.hex()}")
            self.after(0, char_frame._reset_write_status_color)

            if "read" in characteristic.properties:
                self.log_with_timestamp(f"Automatically reading back from {characteristic.uuid}")
                await self.read_char(characteristic, char_frame)
        except Exception as e:
            self.log_with_timestamp(f"Write Error on {characteristic.uuid}: {e}")
            self.after(0, lambda: char_frame.set_write_status_color("light coral"))

    def notification_handler(self, characteristic, data):
        self.log_with_timestamp(f"Notification from {characteristic.uuid}: {data.hex()}")

        # Find the corresponding frame and update its value
        if characteristic.handle in self.characteristic_frames:
            frame = self.characteristic_frames[characteristic.handle]
            self.after(0, lambda: frame.update_value(data))

    def subscribe_to_characteristic(self, characteristic, char_frame):
        if self.client:
            asyncio.run_coroutine_threadsafe(self.client.start_notify(characteristic.uuid, self.notification_handler), self.loop)
            self.log_with_timestamp(f"Subscribed to {characteristic.uuid}")

    def unsubscribe_from_characteristic(self, characteristic, char_frame):
        if self.client:
            asyncio.run_coroutine_threadsafe(self.client.stop_notify(characteristic.uuid), self.loop)
            self.log_with_timestamp(f"Unsubscribed from {characteristic.uuid}")

    def read_descriptor(self, descriptor, desc_frame):
        if self.client:
            asyncio.run_coroutine_threadsafe(self.read_desc(descriptor, desc_frame), self.loop)

    async def read_desc(self, descriptor, desc_frame):
        try:
            value = await self.client.read_gatt_descriptor(descriptor.handle)
            self.after(0, lambda: desc_frame.update_value(value))
            self.log_with_timestamp(f"Value read from {descriptor.uuid}: {value.hex()}")
        except Exception as e:
            self.log_with_timestamp(f"Read Error on {descriptor.uuid}: {e}")

    def write_descriptor(self, descriptor, desc_frame):
        if self.client:
            value = desc_frame.write_entry.get()
            asyncio.run_coroutine_threadsafe(self.write_desc(descriptor, value, desc_frame), self.loop)

    async def write_desc(self, descriptor, value, desc_frame):
        try:
            write_value = bytes.fromhex(value)
            await self.client.write_gatt_descriptor(descriptor.handle, write_value)
            self.log_with_timestamp(f"Value written to {descriptor.uuid}: {write_value.hex()}")
            await self.read_desc(descriptor, desc_frame)
        except Exception as e:
            self.log_with_timestamp(f"Write Error on {descriptor.uuid}: {e}")

    def discover_adapters(self):
        adapters = ["Default"]
        if platform.system() == "Linux":
            try:
                result = subprocess.run(['hciconfig'], capture_output=True, text=True, check=True)
                adapters.extend(re.findall(r'^(hci\d+)', result.stdout, re.MULTILINE))
            except (FileNotFoundError, subprocess.CalledProcessError):
                pass
        self.adapter_combobox.configure(values=adapters)
        self.adapter_combobox.set("Default")

    def on_adapter_selected(self, choice):
        self.log_with_timestamp(f"Adapter selected: {choice}")
        if platform.system() == "Linux" and choice != "Default":
            try:
                result = subprocess.run(['hciconfig', '-a', choice], capture_output=True, text=True, check=True)
                self.log_with_timestamp(f"--- Adapter Info for {choice} ---\n{result.stdout.strip()}\n--------------------")
            except (FileNotFoundError, subprocess.CalledProcessError) as e:
                self.log_with_timestamp(f"Could not get info for adapter {choice}: {e}")

    def filter_devices(self, event=None):
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
