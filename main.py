import customtkinter
import bleak
import asyncio
import threading
import platform
import subprocess
import re

class CharacteristicFrame(customtkinter.CTkFrame):
    def __init__(self, master, characteristic, description, read_callback, write_callback):
        super().__init__(master)
        self.characteristic = characteristic
        self.read_callback = read_callback
        self.write_callback = write_callback

        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(3, weight=1)

        self.uuid_label = customtkinter.CTkLabel(self, text=str(characteristic.uuid), wraplength=200, justify="left")
        self.uuid_label.grid(row=0, column=0, rowspan=2, padx=5, pady=5, sticky="w")

        self.description_label = customtkinter.CTkLabel(self, text=description, wraplength=200, justify="left", font=("Arial", 10))
        self.description_label.grid(row=2, column=0, columnspan=4, padx=5, pady=(0,5), sticky="w")

        self.read_button = customtkinter.CTkButton(self, text="Read", command=self.read_pressed, width=50)
        if "read" not in self.characteristic.properties:
            self.read_button.configure(state="disabled")
        self.read_button.grid(row=0, column=2, padx=5, pady=5, sticky="e")

        self.read_value_entry = customtkinter.CTkEntry(self)
        self.read_value_entry.grid(row=0, column=3, padx=5, pady=5, sticky="ew")

        self.read_ascii_label = customtkinter.CTkLabel(self, text="", wraplength=200, justify="left")
        self.read_ascii_label.grid(row=0, column=4, padx=5, pady=5, sticky="w")

        self.write_entry = customtkinter.CTkEntry(self)
        self.write_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        self.write_button = customtkinter.CTkButton(self, text="Write", command=self.write_pressed, width=50)
        if "write" not in self.characteristic.properties and "write-without-response" not in self.characteristic.properties:
            self.write_button.configure(state="disabled")
        self.write_button.grid(row=1, column=2, padx=5, pady=5, sticky="e")

        self.properties_label = customtkinter.CTkLabel(self, text=f"({', '.join(self.characteristic.properties)})", font=("Arial", 10))
        self.properties_label.grid(row=1, column=3, padx=5, pady=(0,5), sticky="w")


    def read_pressed(self):
        self.read_callback(self.characteristic, self)

    def write_pressed(self):
        self.write_callback(self.characteristic, self)

class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        self.title("BLE Scanner")
        self.geometry("800x600")

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=1)

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

        # Left column for devices
        self.devices_frame = customtkinter.CTkScrollableFrame(self, label_text="Nearby Devices")
        self.devices_frame.grid(row=1, column=0, rowspan=1, padx=10, pady=(0,10), sticky="nsew")

        # Right column for characteristics
        self.right_frame = customtkinter.CTkFrame(self)
        self.right_frame.grid(row=1, column=1, padx=(0, 10), pady=(0, 10), sticky="nsew")
        self.right_frame.grid_rowconfigure(1, weight=1)
        self.right_frame.grid_columnconfigure(0, weight=1)

        self.char_toolbar = customtkinter.CTkFrame(self.right_frame)
        self.char_toolbar.grid(row=0, column=0, padx=0, pady=0, sticky="ew")

        self.read_all_button = customtkinter.CTkButton(self.char_toolbar, text="Read All", command=self.read_all_characteristics, state="disabled")
        self.read_all_button.pack(side="left", padx=5, pady=5)

        self.characteristics_frame = customtkinter.CTkScrollableFrame(self.right_frame, label_text="Characteristics")
        self.characteristics_frame.grid(row=1, column=0, padx=0, pady=0, sticky="nsew")

        # Bottom debug window
        self.attributes_textbox = customtkinter.CTkTextbox(self)
        self.attributes_textbox.grid(row=2, column=0, columnspan=2, padx=10, pady=(0,10), sticky="nsew")

        self.client = None
        self.selected_device = None
        self.device_buttons = {}
        self.characteristic_frames = []

        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.run_async_loop, daemon=True)
        self.thread.start()

        self.after(100, self.discover_adapters)

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

    def device_selected(self, device, button):
        self.selected_device = device
        for btn in self.device_buttons.values():
            btn.configure(fg_color=customtkinter.ThemeManager.theme["CTkButton"]["fg_color"])
        button.configure(fg_color="green")

        self.connect_to_selected_device()

    def scan_for_devices(self):
        self.scan_button.configure(state="disabled", text="Scanning...")
        asyncio.run_coroutine_threadsafe(self.discover_devices(), self.loop)

    def clear_frame(self, frame):
        for widget in frame.winfo_children():
            widget.destroy()

    async def discover_devices(self):
        self.after(0, lambda: self.clear_frame(self.devices_frame))
        self.device_buttons = {}

        adapter = self.adapter_combobox.get()
        if adapter == "Default":
            adapter = None
        scanner_kwargs = {"adapter": adapter} if adapter else {}

        try:
            discovered_devices = await bleak.BleakScanner.discover(timeout=5.0, **scanner_kwargs)
        except bleak.exc.BleakError as e:
            self.after(0, lambda err=e: self.log_message(f"Scanning Error: {err}"))
            discovered_devices = []

        for device in discovered_devices:
            def create_command(dev, btn_ref):
                return lambda: self.device_selected(dev, btn_ref)

            button = customtkinter.CTkButton(self.devices_frame, text=f"{device.name} ({device.address})")
            button.configure(command=create_command(device, button))
            button.pack(padx=5, pady=2, fill="x")
            self.device_buttons[device.address] = button

        self.after(0, lambda: self.scan_button.configure(state="normal", text="Scan for devices"))

    def connect_to_selected_device(self):
        if self.selected_device:
            asyncio.run_coroutine_threadsafe(self._manage_connection(), self.loop)

    async def _manage_connection(self):
        self.after(0, lambda: self.attributes_textbox.delete("1.0", "end"))
        self.after(0, lambda: self.log_message(f"Connecting to {self.selected_device.name}..."))

        if self.client and self.client.is_connected:
            await self.client.disconnect()

        adapter = self.adapter_combobox.get()
        if adapter == "Default":
            adapter = None
        client_kwargs = {"adapter": adapter} if adapter else {}
        self.client = bleak.BleakClient(self.selected_device, **client_kwargs)

        await self.discover_attributes()

    def disconnect_from_device(self):
        if self.client:
            asyncio.run_coroutine_threadsafe(self.disconnect(), self.loop)

    async def disconnect(self):
        await self.client.disconnect()
        self.after(0, self.on_disconnect_ui_update)

    def on_disconnect_ui_update(self):
        self.disconnect_button.configure(state="disabled")
        self.read_all_button.configure(state="disabled")
        self.attributes_textbox.delete("1.0", "end")
        self.clear_frame(self.characteristics_frame)
        self.characteristic_frames.clear()
        self.scan_button.configure(state="normal")
        for btn in self.device_buttons.values():
             btn.configure(fg_color=customtkinter.ThemeManager.theme["CTkButton"]["fg_color"])

    async def discover_attributes(self):
        self.after(0, lambda: self.attributes_textbox.delete("1.0", "end"))
        self.after(0, lambda: self.clear_frame(self.characteristics_frame))
        self.characteristic_frames.clear()

        try:
            await self.client.connect()
            self.after(0, lambda: self.disconnect_button.configure(state="normal"))
            self.after(0, lambda: self.read_all_button.configure(state="normal"))
            self.after(0, lambda: self.scan_button.configure(state="disabled"))

            all_characteristics = []
            for service in self.client.services:
                self.after(0, lambda s=service: self.log_message(f"Service: {s.uuid}"))
                all_characteristics.extend(service.characteristics)

            # Sort characteristics by description, handling None
            all_characteristics.sort(key=lambda char: char.description or "")

            self.after(0, self._populate_characteristics_ui, all_characteristics)

        except Exception as e:
            self.after(0, lambda err=e: self.log_message(f"Connection Error: {err}"))
            self.after(0, self.reset_device_buttons)
            self.after(0, lambda: self.scan_button.configure(state="normal"))

    def _populate_characteristics_ui(self, characteristics):
        for characteristic in characteristics:
            char_frame = CharacteristicFrame(self.characteristics_frame, characteristic, characteristic.description, self.read_characteristic, self.write_characteristic)
            char_frame.pack(padx=5, pady=2, fill="x")
            self.characteristic_frames.append(char_frame)

    def reset_device_buttons(self):
        for btn in self.device_buttons.values():
            btn.configure(fg_color=None)

    def log_message(self, message):
        self.attributes_textbox.insert("end", message + "\n")
        self.attributes_textbox.see("end")

    def read_characteristic(self, characteristic, char_frame):
        if self.client:
            asyncio.run_coroutine_threadsafe(self.read_char(characteristic, char_frame), self.loop)

    async def read_char(self, characteristic, char_frame):
        try:
            value = await self.client.read_gatt_char(characteristic.uuid)
            hex_value = value.hex()
            ascii_value = value.decode('ascii', errors='replace')

            self.after(0, lambda: char_frame.read_value_entry.delete(0, "end"))
            self.after(0, lambda: char_frame.read_value_entry.insert(0, hex_value))
            self.after(0, lambda: char_frame.read_ascii_label.configure(text=ascii_value))
            self.after(0, lambda v=hex_value: self.log_message(f"Value read from {characteristic.uuid}: {v}"))
        except Exception as e:
            self.after(0, lambda err=e: self.log_message(f"Read Error on {characteristic.uuid}: {err}"))

    def write_characteristic(self, characteristic, char_frame):
        if self.client:
            value = char_frame.write_entry.get()
            asyncio.run_coroutine_threadsafe(self.write_char(characteristic, value), self.loop)

    def read_all_characteristics(self):
        self.log_message("--- Reading all readable characteristics ---")
        for char_frame in self.characteristic_frames:
            if "read" in char_frame.characteristic.properties:
                self.read_characteristic(char_frame.characteristic, char_frame)

    async def write_char(self, characteristic, value):
        try:
            try:
                write_value = bytes.fromhex(value)
            except ValueError:
                write_value = value.encode("utf-8")

            await self.client.write_gatt_char(characteristic.uuid, write_value)
            self.after(0, lambda wv=write_value: self.log_message(f"Value written to {characteristic.uuid}: {wv.hex()}"))
        except Exception as e:
             self.after(0, lambda err=e: self.log_message(f"Write Error on {characteristic.uuid}: {err}"))

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
        self.log_message(f"Adapter selected: {choice}")
        if platform.system() == "Linux" and choice != "Default":
            try:
                result = subprocess.run(['hciconfig', '-a', choice], capture_output=True, text=True, check=True)
                self.log_message(f"--- Adapter Info for {choice} ---\n{result.stdout.strip()}\n--------------------")
            except (FileNotFoundError, subprocess.CalledProcessError) as e:
                self.log_message(f"Could not get info for adapter {choice}: {e}")

if __name__ == "__main__":
    app = App()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
