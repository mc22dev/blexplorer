import customtkinter
from typing import Any, Callable, Union
from bleak.backends.descriptor import BleakGATTDescriptor
from models import CachedDescriptor

class DescriptorFrame(customtkinter.CTkFrame):
    """A custom tkinter frame that displays information about a BLE descriptor."""

    def __init__(self,
                 master: Any,
                 descriptor: Union[BleakGATTDescriptor, CachedDescriptor],
                 read_callback: Callable[[Union[BleakGATTDescriptor, CachedDescriptor], 'DescriptorFrame'], None],
                 write_callback: Callable[[Union[BleakGATTDescriptor, CachedDescriptor], 'DescriptorFrame'], None]) -> None:
        """
        Initializes the DescriptorFrame.

        Args:
            master: The parent widget.
            descriptor: The BleakGATTDescriptor object.
            read_callback: The callback function to execute when the read button is pressed.
            write_callback: The callback function to execute when the write button is pressed.
        """
        super().__init__(master)
        self.descriptor = descriptor
        self.read_callback = read_callback
        self.write_callback = write_callback

        self.grid_columnconfigure(1, weight=1)

        self.uuid_label = customtkinter.CTkLabel(self, text=str(descriptor.uuid), wraplength=200, justify="left")
        self.uuid_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        self.read_button = customtkinter.CTkButton(self, text="Read", command=self.read_pressed, width=50)
        self.read_button.grid(row=0, column=2, padx=5, pady=5, sticky="e")

        self.read_value_entry = customtkinter.CTkEntry(self)
        self.read_value_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        self.write_button = customtkinter.CTkButton(self, text="Write", command=self.write_pressed, width=50)
        self.write_button.grid(row=1, column=2, padx=5, pady=5, sticky="e")

        self.write_entry = customtkinter.CTkEntry(self)
        self.write_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

    def read_pressed(self) -> None:
        """Handles the read button press event."""
        self.read_callback(self.descriptor, self)

    def write_pressed(self) -> None:
        """Handles the write button press event."""
        self.write_callback(self.descriptor, self)

    def update_value(self, raw_bytes: bytes) -> None:
        """
        Updates the displayed value of the descriptor.

        Args:
            raw_bytes: The new raw value of the descriptor.
        """
        self.read_value_entry.delete(0, "end")
        self.read_value_entry.insert(0, raw_bytes.hex())
