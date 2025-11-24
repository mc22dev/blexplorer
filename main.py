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
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(1, weight=2)
        self.grid_rowconfigure(4, weight=1)

        # Frame for adapter selection
        self.adapter_frame = customtkinter.CTkFrame(self)
        self.adapter_frame.grid(row=0, column=0, padx=10, pady=(10,0), sticky="ew")
        self.adapter_frame.grid_columnconfigure(1, weight=1)

        self.adapter_label = customtkinter.CTkLabel(self.adapter_frame, text="Bluetooth Adapter:")
        self.adapter_label.grid(row=0, column=0, padx=10, pady=10)

        self.adapter_combobox = customtkinter.CTkComboBox(self.adapter_frame, values=["Default"])
        self.adapter_combobox.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        self.adapter_combobox.set("Default")

        self.refresh_adapters_button = customtkinter.CTkButton(self.adapter_frame, text="Refresh", command=self.discover_adapters)
        self.refresh_adapters_button.grid(row=0, column=2, padx=10, pady=10)

        self.scan_button = customtkinter.CTkButton(self, text="Scan for devices", command=self.scan_for_devices)
        self.scan_button.grid(row=1, column=0, padx=10, pady=10)

        self.devices_frame = customtkinter.CTkScrollableFrame(self, label_text="Nearby Devices")
        self.devices_frame.grid(row=2, column=0, rowspan=3, padx=10, pady=10, sticky="nsew")

        self.connection_frame = customtkinter.CTkFrame(self)
        self.connection_frame.grid(row=4, column=0, padx=10, pady=10, sticky="ew")
        self.connection_frame.grid_columnconfigure(0, weight=1)
        self.connection_frame.grid_columnconfigure(1, weight=1)

        self.connect_button = customtkinter.CTkButton(self.connection_frame, text="Connect", command=self.connect_to_device, state="disabled")
        self.connect_button.grid(row=0, column=0, padx=(0,5), pady=0, sticky="ew")

        self.disconnect_button = customtkinter.CTkButton(self.connection_frame, text="Disconnect", command=self.disconnect_from_device, state="disabled")
        self.disconnect_button.grid(row=0, column=1, padx=(5,0), pady=0, sticky="ew")

        self.attributes_textbox = customtkinter.CTkTextbox(self)
        self.attributes_textbox.grid(row=0, column=1, rowspan=2, padx=10, pady=10, sticky="nsew")

        self.characteristics_frame = customtkinter.CTkScrollableFrame(self, label_text="Characteristics")
        self.characteristics_frame.grid(row=2, column=1, rowspan=1, padx=10, pady=10, sticky="nsew")

        self.read_button = customtkinter.CTkButton(self, text="Read", command=self.read_characteristic, state="disabled")
        self.read_button.grid(row=3, column=1, padx=10, pady=10, sticky="sw")

        self.write_frame = customtkinter.CTkFrame(self)
        self.write_frame.grid(row=4, column=1, padx=10, pady=10, sticky="ew")
        self.write_frame.grid_columnconfigure(0, weight=1)

        self.write_entry = customtkinter.CTkEntry(self.write_frame)
        self.write_entry.grid(row=0, column=0, padx=(0,5), pady=0, sticky="ew")

        self.write_button = customtkinter.CTkButton(self.write_frame, text="Write", command=self.write_characteristic, state="disabled")
        self.write_button.grid(row=0, column=1, padx=(5,0), pady=0)

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

        if not self.client or not self.client.is_connected:
            self.connect_button.configure(state="normal")

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
            self.after(0, lambda err=e: self.attributes_textbox.insert("end", f"Scanning Error: {err}\n"))
            discovered_devices = []

        for device in discovered_devices:
            def create_command(dev, btn_ref):
                return lambda: self.device_selected(dev, btn_ref)

            button = customtkinter.CTkButton(self.devices_frame, text=f"{device.name} ({device.address})")
            button.configure(command=create_command(device, button))
            button.pack(padx=5, pady=2, fill="x")
            self.device_buttons[device.address] = button

        self.after(0, lambda: self.scan_button.configure(state="normal", text="Scan for devices"))

    def connect_to_device(self):
        if self.selected_device:
            self.connect_button.configure(state="disabled")
            self.attributes_textbox.delete("1.0", "end")
            self.attributes_textbox.insert("end", f"Connecting to {self.selected_device.name}...")

            adapter = self.adapter_combobox.get()
            if adapter == "Default":
                adapter = None
            client_kwargs = {"adapter": adapter} if adapter else {}

            self.client = bleak.BleakClient(self.selected_device, **client_kwargs)
            asyncio.run_coroutine_threadsafe(self.discover_attributes(), self.loop)

    def disconnect_from_device(self):
        if self.client:
            asyncio.run_coroutine_threadsafe(self.disconnect(), self.loop)

    async def disconnect(self):
        await self.client.disconnect()
        self.after(0, self.on_disconnect_ui_update)

    def on_disconnect_ui_update(self):
        self.disconnect_button.configure(state="disabled")
        if self.selected_device:
            self.connect_button.configure(state="normal")
        else:
            self.connect_button.configure(state="disabled")
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
                self.after(0, lambda s=service: self.attributes_textbox.insert("end", f"Service: {s.uuid}\n"))
                for characteristic in service.characteristics:
                    self.after(0, lambda c=characteristic: self.attributes_textbox.insert("end", f"  Characteristic: {c.uuid} ({', '.join(c.properties)})\n"))
                    char_button = customtkinter.CTkButton(self.characteristics_frame, text=f"{characteristic.uuid}",
                                                         command=lambda char=characteristic: self.characteristic_selected(char))
                    char_button.pack(padx=5, pady=2, fill="x")
        except Exception as e:
            self.after(0, lambda: self.connect_button.configure(state="normal"))
            self.after(0, lambda err=e: self.attributes_textbox.insert("end", f"Connection Error: {err}\n"))

    def read_characteristic(self):
        if self.selected_characteristic and self.client:
            asyncio.run_coroutine_threadsafe(self.read_char(self.selected_characteristic), self.loop)

    async def read_char(self, characteristic):
        try:
            value = await self.client.read_gatt_char(characteristic.uuid)
            self.after(0, lambda v=value: self.attributes_textbox.insert("end", f"\nValue read: {v.hex()}\n"))
        except Exception as e:
            self.after(0, lambda err=e: self.attributes_textbox.insert("end", f"\nRead Error: {err}\n"))

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
            self.after(0, lambda wv=write_value: self.attributes_textbox.insert("end", f"\nValue written: {wv.hex()}\n"))
        except Exception as e:
             self.after(0, lambda err=e: self.attributes_textbox.insert("end", f"\nWrite Error: {err}\n"))

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
