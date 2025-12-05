import customtkinter
import struct
from typing import Any, Callable, Optional
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.descriptor import BleakGATTDescriptor
import tkinter

from descriptor_frame import DescriptorFrame
from collapsible_frame import CollapsibleFrame


class CharacteristicFrame(customtkinter.CTkFrame):
    """A custom tkinter frame that displays information about a BLE characteristic."""

    def __init__(self,
                 master: Any,
                 characteristic: BleakGATTCharacteristic,
                 description: str,
                 read_callback: Callable[[BleakGATTCharacteristic, 'CharacteristicFrame'], None],
                 write_callback: Callable[[BleakGATTCharacteristic, 'CharacteristicFrame'], None],
                 subscribe_callback: Callable[[BleakGATTCharacteristic, 'CharacteristicFrame'], None],
                 unsubscribe_callback: Callable[[BleakGATTCharacteristic, 'CharacteristicFrame'], None],
                 read_desc_callback: Callable[[BleakGATTDescriptor, Any], None],
                 write_desc_callback: Callable[[BleakGATTDescriptor, Any], None]) -> None:
        """
        Initializes the CharacteristicFrame.

        Args:
            master: The parent widget.
            characteristic: The BleakGATTCharacteristic object.
            description: A description of the characteristic.
            read_callback: Callback for read button press.
            write_callback: Callback for write button press.
            subscribe_callback: Callback for subscribe button press.
            unsubscribe_callback: Callback for unsubscribe button press.
            read_desc_callback: Callback for reading a descriptor.
            write_desc_callback: Callback for writing a descriptor.
        """
        super().__init__(master)
        self.characteristic = characteristic
        self.read_callback = read_callback
        self.write_callback = write_callback
        self.subscribe_callback = subscribe_callback
        self.unsubscribe_callback = unsubscribe_callback
        self.read_desc_callback = read_desc_callback
        self.write_desc_callback = write_desc_callback
        self.raw_value: Optional[bytes] = None
        self.write_display_mode = "ascii"  # "hex" or "ascii"

        self.grid_columnconfigure(1, weight=1)

        self.uuid_label = customtkinter.CTkLabel(self, text=str(characteristic.uuid), wraplength=200, justify="left")
        self.uuid_label.grid(row=0, column=0, rowspan=2, padx=5, pady=5, sticky="w")

        self.copy_uuid_button = customtkinter.CTkButton(self, text="Copy", command=self.copy_uuid, width=40, height=20)
        self.copy_uuid_button.grid(row=0, column=1, padx=0, pady=0, sticky="w")

        self.description_label = customtkinter.CTkLabel(self, text=description, wraplength=200, justify="left", font=("Arial", 10))
        self.description_label.grid(row=2, column=0, columnspan=5, padx=5, pady=(0,5), sticky="w")

        self.user_description_label = customtkinter.CTkLabel(self, text="", wraplength=200, justify="left", font=("Arial", 10, "italic"))
        self.user_description_label.grid(row=3, column=0, columnspan=5, padx=5, pady=(0,5), sticky="w")

        # Read widgets
        self.read_frame = customtkinter.CTkFrame(self, fg_color="transparent")
        self.read_frame.grid(row=0, column=1, padx=0, pady=0, sticky="ew")
        self.read_frame.grid_columnconfigure(1, weight=1)

        self.read_button = customtkinter.CTkButton(self.read_frame, text="Read", command=self.read_pressed, width=50)
        self.read_button.grid(row=0, column=0, padx=5, pady=5, sticky="e")

        self.read_value_entry = customtkinter.CTkEntry(self.read_frame)
        self.read_value_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        self.copy_read_button = customtkinter.CTkButton(self.read_frame, text="Copy", command=self.copy_read_value, width=40, height=20)
        self.copy_read_button.grid(row=0, column=5, padx=5, pady=5)

        self.interpreter_combobox = customtkinter.CTkComboBox(self.read_frame, values=["Hex", "ASCII", "Int8", "UInt8", "Int16", "UInt16", "Int32", "UInt32", "Float32", "Float64"], command=self.interpret_data)
        self.interpreter_combobox.grid(row=0, column=6, padx=5, pady=5)
        self.interpreter_combobox.set("Hex")

        self.subscribe_button = customtkinter.CTkButton(self.read_frame, text="Subscribe", command=self.subscribe_pressed, width=80)
        self.subscribe_button.grid(row=0, column=3, padx=5, pady=5)
        self.unsubscribe_button = customtkinter.CTkButton(self.read_frame, text="Unsubscribe", command=self.unsubscribe_pressed, width=90, state="disabled")
        self.unsubscribe_button.grid(row=0, column=4, padx=5, pady=5)

        if "read" not in self.characteristic.properties:
            self.read_button.configure(state="disabled")
            self.read_value_entry.configure(state="disabled")
            self.interpreter_combobox.configure(state="disabled")
            self.copy_read_button.configure(state="disabled")

        if "notify" not in self.characteristic.properties and "indicate" not in self.characteristic.properties:
            self.subscribe_button.configure(state="disabled")

        # Write widgets
        self.write_frame = customtkinter.CTkFrame(self, fg_color="transparent")
        self.write_frame.grid(row=1, column=1, padx=0, pady=0, sticky="ew")
        self.write_frame.grid_columnconfigure(1, weight=1)

        self.write_button = customtkinter.CTkButton(self.write_frame, text="Write", command=self.write_pressed, width=50)
        self.write_button.grid(row=0, column=0, padx=5, pady=5, sticky="e")

        self.write_entry = customtkinter.CTkEntry(self.write_frame)
        self.write_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.write_entry.bind("<Key>", self._reset_write_status_color)

        self.write_format_toggle_button = customtkinter.CTkButton(self.write_frame, text="ASCII", width=40, command=self.toggle_write_display_mode)
        self.write_format_toggle_button.grid(row=0, column=2, padx=5, pady=5)

        if "write" not in self.characteristic.properties and "write-without-response" not in self.characteristic.properties:
            self.write_button.configure(state="disabled")
            self.write_entry.configure(state="disabled")
            self.write_format_toggle_button.configure(state="disabled")

        self.properties_label = customtkinter.CTkLabel(self.write_frame, text=f"({', '.join(self.characteristic.properties)})", font=("Arial", 10))
        self.properties_label.grid(row=1, column=1, padx=5, pady=(0,5), sticky="w")

        if self.characteristic.descriptors:
            self.descriptor_frame = CollapsibleFrame(self, text="Descriptors")
            self.descriptor_frame.grid(row=4, column=0, columnspan=2, padx=5, pady=5, sticky="ew")
            for descriptor in self.characteristic.descriptors:
                desc_frame = DescriptorFrame(self.descriptor_frame.content_frame, descriptor, self.read_desc_callback, self.write_desc_callback)
                desc_frame.pack(padx=5, pady=2, fill="x")

    def read_pressed(self) -> None:
        """Handles the read button press event."""
        self.read_callback(self.characteristic, self)

    def write_pressed(self) -> None:
        """Handles the write button press event."""
        self.write_callback(self.characteristic, self)

    def subscribe_pressed(self) -> None:
        """Handles the subscribe button press event."""
        self.subscribe_callback(self.characteristic, self)
        self.subscribe_button.configure(state="disabled")
        self.unsubscribe_button.configure(state="normal")

    def unsubscribe_pressed(self) -> None:
        """Handles the unsubscribe button press event."""
        self.unsubscribe_callback(self.characteristic, self)
        self.subscribe_button.configure(state="normal")
        self.unsubscribe_button.configure(state="disabled")

    def copy_uuid(self) -> None:
        """Copies the characteristic UUID to the clipboard."""
        root_window = self.winfo_toplevel()
        root_window.clipboard_clear()
        root_window.clipboard_append(str(self.characteristic.uuid))

    def copy_read_value(self) -> None:
        """Copies the read value to the clipboard."""
        root_window = self.winfo_toplevel()
        root_window.clipboard_clear()
        root_window.clipboard_append(self.read_value_entry.get())

    def _reset_write_status_color(self, event: Optional[tkinter.Event] = None) -> None:
        """Resets the background color of the write entry field."""
        default_color = customtkinter.ThemeManager.theme["CTkEntry"]["fg_color"]
        self.write_entry.configure(fg_color=default_color)

    def set_write_status_color(self, color: str) -> None:
        """Sets the background color of the write entry field."""
        self.write_entry.configure(fg_color=color)

    def interpret_data(self, interpretation: str) -> None:
        """
        Interprets and displays the raw characteristic value based on the selected format.

        Args:
            interpretation: The desired format (e.g., "Hex", "ASCII", "Int32").
        """
        if self.raw_value is None:
            self.read_value_entry.delete(0, "end")
            self.read_value_entry.insert(0, "")
            return

        self.read_value_entry.delete(0, "end")
        value_to_display = "N/A"
        try:
            if interpretation == "Hex":
                value_to_display = self.raw_value.hex()
            elif interpretation == "ASCII":
                value_to_display = self.raw_value.decode('ascii', errors='replace')
            elif interpretation == "Int8":
                if len(self.raw_value) >= 1: value_to_display = str(struct.unpack('<b', self.raw_value[:1])[0])
            elif interpretation == "UInt8":
                if len(self.raw_value) >= 1: value_to_display = str(struct.unpack('<B', self.raw_value[:1])[0])
            elif interpretation == "Int16":
                if len(self.raw_value) >= 2: value_to_display = str(struct.unpack('<h', self.raw_value[:2])[0])
            elif interpretation == "UInt16":
                if len(self.raw_value) >= 2: value_to_display = str(struct.unpack('<H', self.raw_value[:2])[0])
            elif interpretation == "Int32":
                if len(self.raw_value) >= 4: value_to_display = str(struct.unpack('<i', self.raw_value[:4])[0])
            elif interpretation == "UInt32":
                if len(self.raw_value) >= 4: value_to_display = str(struct.unpack('<I', self.raw_value[:4])[0])
            elif interpretation == "Float32":
                if len(self.raw_value) >= 4: value_to_display = str(struct.unpack('<f', self.raw_value[:4])[0])
            elif interpretation == "Float64":
                if len(self.raw_value) >= 8: value_to_display = str(struct.unpack('<d', self.raw_value[:8])[0])
        except (struct.error, UnicodeDecodeError):
            value_to_display = "Interpretation Error"

        self.read_value_entry.insert(0, value_to_display)

    def update_value(self, raw_bytes: bytes) -> None:
        """
        Updates the characteristic's raw value and re-interprets it.

        Args:
            raw_bytes: The new raw value of the characteristic.
        """
        self.raw_value = raw_bytes
        self.interpret_data(self.interpreter_combobox.get())

    def toggle_write_display_mode(self) -> None:
        """Toggles the display mode of the write entry field between ASCII and Hex."""
        current_text = self.write_entry.get()
        if self.write_display_mode == "ascii":
            try:
                hex_value = current_text.encode('ascii').hex()
                self.write_entry.delete(0, "end")
                self.write_entry.insert(0, hex_value)
                self.write_display_mode = "hex"
                self.write_format_toggle_button.configure(text="Hex")
            except UnicodeEncodeError:
                self.write_entry.delete(0, "end")
                self.write_entry.insert(0, "Invalid ASCII")
        else: # hex
            try:
                ascii_value = bytes.fromhex(current_text).decode('ascii')
                self.write_entry.delete(0, "end")
                self.write_entry.insert(0, ascii_value)
                self.write_display_mode = "ascii"
                self.write_format_toggle_button.configure(text="ASCII")
            except (ValueError, UnicodeDecodeError):
                self.write_entry.delete(0, "end")
                self.write_entry.insert(0, "Invalid Hex")
