import customtkinter
from typing import Any, Callable
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

class DeviceFrame(customtkinter.CTkFrame):
    """A custom tkinter frame that displays information about a discovered BLE device."""

    def __init__(self, master: Any, device: BLEDevice, adv_data: AdvertisementData, connect_callback: Callable[['DeviceFrame', BLEDevice], None]) -> None:
        """
        Initializes the DeviceFrame.

        Args:
            master: The parent widget.
            device: The BLEDevice object.
            adv_data: The advertisement data for the device.
            connect_callback: The callback function to execute when the connect button is pressed.
        """
        super().__init__(master, corner_radius=5)
        self.device = device
        self.connect_callback = connect_callback
        self.original_fg_color = self.cget("fg_color")

        self.grid_columnconfigure(0, weight=1)

        self.name_label = customtkinter.CTkLabel(self, text=f"{device.name or 'Unknown'}", font=("Arial", 12, "bold"), anchor="w")
        self.name_label.grid(row=0, column=0, padx=10, pady=(2, 0), sticky="ew")

        self.info_label = customtkinter.CTkLabel(self, text=f"{device.address}  |  RSSI: {adv_data.rssi} dBm", font=("Arial", 10), anchor="w")
        self.info_label.grid(row=1, column=0, padx=10, pady=(0, 2), sticky="ew")

        row = 2
        if adv_data.manufacturer_data:
            for company_id, data in adv_data.manufacturer_data.items():
                self.manufacturer_data_label = customtkinter.CTkLabel(self, text=f"Manufacturer: {company_id}: {data.hex()}", font=("Arial", 9), anchor="w")
                self.manufacturer_data_label.grid(row=row, column=0, padx=10, pady=0, sticky="ew")
                row += 1

        if adv_data.service_uuids:
            self.service_uuids_label = customtkinter.CTkLabel(self, text=f"Services: {', '.join(adv_data.service_uuids)}", font=("Arial", 9), wraplength=200, justify="left", anchor="w")
            self.service_uuids_label.grid(row=row, column=0, padx=10, pady=0, sticky="ew")
            row += 1

        if adv_data.tx_power:
            self.tx_power_label = customtkinter.CTkLabel(self, text=f"TX Power: {adv_data.tx_power} dBm", font=("Arial", 9), anchor="w")
            self.tx_power_label.grid(row=row, column=0, padx=10, pady=(0,2), sticky="ew")
            row += 1

        # Bindings
        self.bind("<Button-1>", self.connect_pressed)
        for widget in self.winfo_children():
            widget.bind("<Button-1>", self.connect_pressed)

        self.info_label.bind("<Enter>", self.on_info_enter)
        self.info_label.bind("<Leave>", self.on_info_leave)
        self.info_label.bind("<Button-1>", self.copy_address)

    def on_info_enter(self, event: Any) -> None:
        """Changes cursor to a hand when hovering over the info label."""
        self.info_label.configure(cursor="hand2", font=("Arial", 10, "underline"))

    def on_info_leave(self, event: Any) -> None:
        """Changes cursor back to default when not hovering over the info label."""
        self.info_label.configure(cursor="", font=("Arial", 10))

    def connect_pressed(self, event: Any) -> None:
        """Handles the connect button press event."""
        self.connect_callback(self, self.device)

    def copy_address(self, event: Any) -> None:
        """Copies the device address to the clipboard."""
        root_window = self.winfo_toplevel()
        root_window.clipboard_clear()
        root_window.clipboard_append(self.device.address)
        # Prevent the connect event from firing
        return "break"
