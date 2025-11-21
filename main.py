import customtkinter
import bleak
import asyncio
import threading

class App(customtkinter.CTk):
    def __init__(self):
        super().__init__()

        self.title("BLE Scanner")
        self.geometry("800x600")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.scan_button = customtkinter.CTkButton(self, text="Scan for devices", command=self.scan_for_devices)
        self.scan_button.grid(row=0, column=0, padx=10, pady=10)

        self.devices_listbox = customtkinter.CTkListbox(self, command=self.device_selected)
        self.devices_listbox.grid(row=1, column=0, rowspan=3, padx=10, pady=10, sticky="nsew")

        # Frame for connect/disconnect buttons
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

        self.characteristics_listbox = customtkinter.CTkListbox(self, command=self.characteristic_selected)
        self.characteristics_listbox.grid(row=2, column=1, rowspan=1, padx=10, pady=10, sticky="nsew")

        self.read_button = customtkinter.CTkButton(self, text="Read", command=self.read_characteristic, state="disabled")
        self.read_button.grid(row=3, column=1, padx=10, pady=10, sticky="sw")

        # Frame for write entry and button
        self.write_frame = customtkinter.CTkFrame(self)
        self.write_frame.grid(row=4, column=1, padx=10, pady=10, sticky="ew")
        self.write_frame.grid_columnconfigure(0, weight=1)

        self.write_entry = customtkinter.CTkEntry(self.write_frame)
        self.write_entry.grid(row=0, column=0, padx=(0,5), pady=0, sticky="ew")

        self.write_button = customtkinter.CTkButton(self.write_frame, text="Write", command=self.write_characteristic, state="disabled")
        self.write_button.grid(row=0, column=1, padx=(5,0), pady=0)

        self.devices = []
        self.client = None
        self.characteristics = []

        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.run_async_loop, daemon=True)
        self.thread.start()

    def on_closing(self):
        if self.client and self.client.is_connected:
            future = asyncio.run_coroutine_threadsafe(self.client.disconnect(), self.loop)
            future.result() # Wait for disconnect to complete
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.thread.join()
        self.destroy()

    def run_async_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def device_selected(self, selection):
        if not self.client or not self.client.is_connected:
            self.connect_button.configure(state="normal")

    def characteristic_selected(self, selection):
        self.read_button.configure(state="normal")
        self.write_button.configure(state="normal")

    def scan_for_devices(self):
        self.scan_button.configure(state="disabled", text="Scanning...")
        asyncio.run_coroutine_threadsafe(self.discover_devices(), self.loop)

    async def discover_devices(self):
        self.after(0, lambda: self.devices_listbox.delete(0, "end"))
        self.devices = []

        discovered_devices = await bleak.BleakScanner.discover()
        for device in discovered_devices:
            self.devices.append(device)
            self.after(0, lambda d=device: self.devices_listbox.insert("end", f"{d.name} ({d.address})"))

        self.after(0, lambda: self.scan_button.configure(state="normal", text="Scan for devices"))

    def connect_to_device(self):
        selected_indices = self.devices_listbox.curselection()
        if selected_indices:
            self.connect_button.configure(state="disabled")
            self.attributes_textbox.delete("1.0", "end")
            self.attributes_textbox.insert("end", "Connecting...")

            device = self.devices[selected_indices[0]]
            self.client = bleak.BleakClient(device)
            asyncio.run_coroutine_threadsafe(self.discover_attributes(), self.loop)

    def disconnect_from_device(self):
        if self.client:
            asyncio.run_coroutine_threadsafe(self.disconnect(), self.loop)

    async def disconnect(self):
        await self.client.disconnect()
        self.after(0, lambda: self.disconnect_button.configure(state="disabled"))
        self.after(0, lambda: self.connect_button.configure(state="disabled"))
        self.after(0, lambda: self.attributes_textbox.delete("1.0", "end"))
        self.after(0, lambda: self.characteristics_listbox.delete(0, "end"))
        self.after(0, lambda: self.devices_listbox.configure(state="normal"))
        self.after(0, lambda: self.scan_button.configure(state="normal"))

    async def discover_attributes(self):
        self.after(0, lambda: self.attributes_textbox.delete("1.0", "end"))
        self.after(0, lambda: self.characteristics_listbox.delete(0, "end"))
        self.characteristics = []

        try:
            await self.client.connect()
            self.after(0, lambda: self.disconnect_button.configure(state="normal"))
            self.after(0, lambda: self.devices_listbox.configure(state="disabled"))
            self.after(0, lambda: self.scan_button.configure(state="disabled"))

            for service in self.client.services:
                self.after(0, lambda s=service: self.attributes_textbox.insert("end", f"Service: {s.uuid}\n"))
                for characteristic in service.characteristics:
                    self.characteristics.append(characteristic)
                    self.after(0, lambda c=characteristic: self.attributes_textbox.insert("end", f"  Characteristic: {c.uuid} ({', '.join(c.properties)})\n"))
                    self.after(0, lambda c=characteristic: self.characteristics_listbox.insert("end", f"{c.uuid}"))
        except Exception as e:
            self.after(0, lambda: self.connect_button.configure(state="normal"))
            self.after(0, lambda err=e: self.attributes_textbox.insert("end", f"Connection Error: {err}\n"))

    def read_characteristic(self):
        selected_indices = self.characteristics_listbox.curselection()
        if selected_indices and self.client:
            characteristic = self.characteristics[selected_indices[0]]
            asyncio.run_coroutine_threadsafe(self.read_char(characteristic), self.loop)

    async def read_char(self, characteristic):
        try:
            value = await self.client.read_gatt_char(characteristic.uuid)
            self.after(0, lambda v=value: self.attributes_textbox.insert("end", f"Value read: {v.hex()}\n"))
        except Exception as e:
            self.after(0, lambda err=e: self.attributes_textbox.insert("end", f"Read Error: {err}\n"))

    def write_characteristic(self):
        selected_indices = self.characteristics_listbox.curselection()
        if selected_indices and self.client:
            characteristic = self.characteristics[selected_indices[0]]
            value = self.write_entry.get()
            asyncio.run_coroutine_threadsafe(self.write_char(characteristic, value), self.loop)

    async def write_char(self, characteristic, value):
        try:
            # Try to convert from hex to bytes, otherwise encode as utf-8
            try:
                write_value = bytes.fromhex(value)
            except ValueError:
                write_value = value.encode("utf-8")

            await self.client.write_gatt_char(characteristic.uuid, write_value)
            self.after(0, lambda wv=write_value: self.attributes_textbox.insert("end", f"Value written: {wv.hex()}\n"))
        except Exception as e:
             self.after(0, lambda err=e: self.attributes_textbox.insert("end", f"Write Error: {err}\n"))

if __name__ == "__main__":
    app = App()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
