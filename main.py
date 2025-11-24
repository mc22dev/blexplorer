import customtkinter
import bleak
import asyncio
import threading
import platform
import subprocess
import re

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

        self.adapter_combobox = customtkinter.CTkComboBox(self.adapter_frame, values=["Default"])
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

        # Right column for characteristics and controls
        self.right_frame = customtkinter.CTkFrame(self)
        self.right_frame.grid(row=1, column=1, padx=10, pady=(0,10), sticky="nsew")
        self.right_frame.grid_columnconfigure(0, weight=1)
        self.right_frame.grid_rowconfigure(0, weight=1)

        self.characteristics_frame = customtkinter.CTkScrollableFrame(self.right_frame, label_text="Characteristics")
        self.characteristics_frame.grid(row=0, column=0, columnspan=2, padx=10, pady=(10,0), sticky="nsew")

        self.read_button = customtkinter.CTkButton(self.right_frame, text="Read", command=self.read_characteristic, state="disabled")
        self.read_button.grid(row=1, column=0, padx=10, pady=10, sticky="sw")

        self.write_frame = customtkinter.CTkFrame(self.right_frame)
        self.write_frame.grid(row=2, column=0, columnspan=2, padx=10, pady=10, sticky="ew")
        self.write_frame.grid_columnconfigure(0, weight=1)

        self.write_entry = customtkinter.CTkEntry(self.write_frame)
        self.write_entry.grid(row=0, column=0, padx=(0,5), pady=0, sticky="ew")

        self.write_button = customtkinter.CTkButton(self.write_frame, text="Write", command=self.write_characteristic, state="disabled")
        self.write_button.grid(row=0, column=1, padx=(5,0), pady=0)

        # Bottom debug window
        self.attributes_textbox = customtkinter.CTkTextbox(self)
        self.attributes_textbox.grid(row=2, column=0, columnspan=2, padx=10, pady=(0,10), sticky="nsew")

        self.client = None
        self.selected_device = None
        self.selected_characteristic = None
        self.device_buttons = {}

        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.run_async_loop, daemon=True)
        self.thread.start()

        self.after(100, self.discover_adapters) # Discover adapters on startup

    def on_closing(self):
        if self.client and self.client.is_connected:
            future = asyncio.run_coroutine_threadsafe(self.client.disconnect(), self.loop)
            future.result()
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

    def characteristic_selected(self, characteristic):
        self.selected_characteristic = characteristic
        self.read_button.configure(state="normal")
        self.write_button.configure(state="normal")

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
            discovered_devices = await bleak.BleakScanner.discover(**scanner_kwargs)
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

        # Disconnect from any existing client
        if self.client and self.client.is_connected:
            await self.client.disconnect()

        # Create and connect the new client
        adapter = self.adapter_combobox.get()
        if adapter == "Default":
            adapter = None
        client_kwargs = {"adapter": adapter} if adapter else {}
        self.client = bleak.BleakClient(self.selected_device, **client_kwargs)

        # Discover attributes, which includes the connect call
        await self.discover_attributes()

    def disconnect_from_device(self):
        if self.client:
            asyncio.run_coroutine_threadsafe(self.disconnect(), self.loop)

    async def disconnect(self):
        await self.client.disconnect()
        self.after(0, self.on_disconnect_ui_update)

    def on_disconnect_ui_update(self):
        self.disconnect_button.configure(state="disabled")
        self.attributes_textbox.delete("1.0", "end")
        self.clear_frame(self.characteristics_frame)
        self.scan_button.configure(state="normal")
        # Reset device button colors, but don't clear the selected device
        for btn in self.device_buttons.values():
             btn.configure(fg_color=customtkinter.ThemeManager.theme["CTkButton"]["fg_color"])

    async def discover_attributes(self):
        self.after(0, lambda: self.attributes_textbox.delete("1.0", "end"))
        self.after(0, lambda: self.clear_frame(self.characteristics_frame))

        try:
            await self.client.connect()
            self.after(0, lambda: self.disconnect_button.configure(state="normal"))
            self.after(0, lambda: self.scan_button.configure(state="disabled"))

            for service in self.client.services:
                self.after(0, lambda s=service: self.log_message(f"Service: {s.uuid}"))
                for characteristic in service.characteristics:
                    self.after(0, lambda c=characteristic: self.log_message(f"  Characteristic: {c.uuid} ({', '.join(c.properties)})"))
                    char_button = customtkinter.CTkButton(self.characteristics_frame, text=f"{characteristic.uuid}",
                                                         command=lambda char=characteristic: self.characteristic_selected(char))
                    char_button.pack(padx=5, pady=2, fill="x")
        except Exception as e:
            self.after(0, lambda err=e: self.log_message(f"Connection Error: {err}"))
            self.after(0, self.reset_device_buttons)
            self.after(0, lambda: self.scan_button.configure(state="normal"))

    def reset_device_buttons(self):
        for btn in self.device_buttons.values():
            btn.configure(fg_color=None)

    def log_message(self, message):
        self.attributes_textbox.insert("end", message + "\n")
        self.attributes_textbox.see("end")

    def read_characteristic(self):
        if self.selected_characteristic and self.client:
            asyncio.run_coroutine_threadsafe(self.read_char(self.selected_characteristic), self.loop)

    async def read_char(self, characteristic):
        try:
            value = await self.client.read_gatt_char(characteristic.uuid)
            self.after(0, lambda v=value: self.log_message(f"\nValue read: {v.hex()}"))
        except Exception as e:
            self.after(0, lambda err=e: self.log_message(f"\nRead Error: {err}"))

    def write_characteristic(self):
        if self.selected_characteristic and self.client:
            value = self.write_entry.get()
            asyncio.run_coroutine_threadsafe(self.write_char(self.selected_characteristic, value), self.loop)

    async def write_char(self, characteristic, value):
        try:
            try:
                write_value = bytes.fromhex(value)
            except ValueError:
                write_value = value.encode("utf-8")

            await self.client.write_gatt_char(characteristic.uuid, write_value)
            self.after(0, lambda wv=write_value: self.log_message(f"\nValue written: {wv.hex()}"))
        except Exception as e:
             self.after(0, lambda err=e: self.log_message(f"\nWrite Error: {err}"))

    def discover_adapters(self):
        adapters = ["Default"]
        if platform.system() == "Linux":
            try:
                result = subprocess.run(['hciconfig'], capture_output=True, text=True, check=True)
                adapters.extend(re.findall(r'^(hci\d+)', result.stdout, re.MULTILINE))
            except (FileNotFoundError, subprocess.CalledProcessError):
                # hciconfig not found or failed
                pass
        self.adapter_combobox.configure(values=adapters)
        self.adapter_combobox.set("Default")

if __name__ == "__main__":
    app = App()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
