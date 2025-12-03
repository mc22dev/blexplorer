import customtkinter

class DeviceFrame(customtkinter.CTkFrame):
    def __init__(self, master, device, adv_data, connect_callback):
        super().__init__(master)
        self.device = device
        self.connect_callback = connect_callback

        self.grid_columnconfigure(0, weight=1)

        self.name_label = customtkinter.CTkLabel(self, text=f"{device.name or 'Unknown'}", font=("Arial", 12, "bold"))
        self.name_label.grid(row=0, column=0, padx=10, pady=(5,0), sticky="w")

        self.address_label = customtkinter.CTkLabel(self, text=f"{device.address}", font=("Arial", 10))
        self.address_label.grid(row=1, column=0, padx=10, pady=0, sticky="w")

        self.copy_address_button = customtkinter.CTkButton(self, text="Copy", command=self.copy_address, width=40, height=20)
        self.copy_address_button.grid(row=1, column=1, padx=0, pady=0, sticky="w")

        self.rssi_label = customtkinter.CTkLabel(self, text=f"RSSI: {adv_data.rssi} dBm", font=("Arial", 10))
        self.rssi_label.grid(row=2, column=0, padx=10, pady=(0,5), sticky="w")

        row = 3
        if adv_data.manufacturer_data:
            for company_id, data in adv_data.manufacturer_data.items():
                self.manufacturer_data_label = customtkinter.CTkLabel(self, text=f"Manufacturer: {company_id}: {data.hex()}", font=("Arial", 10))
                self.manufacturer_data_label.grid(row=row, column=0, padx=10, pady=0, sticky="w")
                row += 1

        if adv_data.service_uuids:
            self.service_uuids_label = customtkinter.CTkLabel(self, text=f"Services: {', '.join(adv_data.service_uuids)}", font=("Arial", 10), wraplength=200, justify="left")
            self.service_uuids_label.grid(row=row, column=0, padx=10, pady=0, sticky="w")
            row += 1

        if adv_data.tx_power:
            self.tx_power_label = customtkinter.CTkLabel(self, text=f"TX Power: {adv_data.tx_power} dBm", font=("Arial", 10))
            self.tx_power_label.grid(row=row, column=0, padx=10, pady=(0,5), sticky="w")
            row += 1

        self.connect_button = customtkinter.CTkButton(self, text="Connect", command=self.connect_pressed)
        self.connect_button.grid(row=0, column=1, rowspan=row, padx=10, pady=5, sticky="e")

    def connect_pressed(self):
        self.connect_callback(self.device, self)

    def copy_address(self):
        root_window = self.winfo_toplevel()
        root_window.clipboard_clear()
        root_window.clipboard_append(self.device.address)
