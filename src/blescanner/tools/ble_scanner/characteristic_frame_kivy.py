from kivy.uix.boxlayout import BoxLayout
from kivy.properties import ObjectProperty, StringProperty, BooleanProperty
import struct
import json

from bleak.backends.characteristic import BleakGATTCharacteristic
from .gatt import GATT_CHARACTERISTICS
from blescanner.ui.copy_popup import CopyPopup


class CharacteristicFrameKivy(BoxLayout):
    characteristic = ObjectProperty(None)
    char_uuid = StringProperty('')
    char_name = StringProperty('')
    full_char_properties = StringProperty('')
    char_value = StringProperty('')
    user_description = StringProperty('')
    raw_value = ObjectProperty(b'')
    collapsed = BooleanProperty(False)

    def __init__(self, characteristic: BleakGATTCharacteristic, **kwargs):
        super().__init__(**kwargs)
        self.characteristic = characteristic
        self.char_uuid = characteristic.uuid
        self.char_name = self.characteristic.description or "Unknown Characteristic"
        self._copy_selection_state = set()

        # Create the full properties string for the tooltip
        self.full_char_properties = ", ".join(sorted(characteristic.properties))

        if "write" not in self.characteristic.properties and "write-without-response" not in self.characteristic.properties:
            self.ids.write_button.disabled = True
            self.ids.value_input.disabled = True

        if "read" not in self.characteristic.properties:
            self.ids.read_button.disabled = True

        if "notify" not in self.characteristic.properties and "indicate" not in self.characteristic.properties:
            self.ids.subscribe_button.disabled = True

        # Set user description if available
        short_uuid = self.char_uuid.split('-')[0].lstrip('0')
        if len(short_uuid) == 3:
            short_uuid = "0" + short_uuid
        user_description = GATT_CHARACTERISTICS.get(short_uuid.lower())
        if user_description:
            self.user_description = user_description

    def _is_printable_ascii(self, data: bytes) -> bool:
        """Checks if byte data is empty or contains only printable ASCII characters."""
        if not data:
            return True
        try:
            decoded = data.decode('ascii')
            # Check for non-printable characters, allowing common whitespace.
            return all(32 <= ord(char) < 127 or char in '\n\r\t' for char in decoded)
        except UnicodeDecodeError:
            return False

    def on_raw_value(self, instance, value):
        """
        When the raw_value is updated, re-format it based on the current
        selection in the format spinner. Automatically select ASCII if the
        value is printable.
        """
        current_format = self.ids.format_spinner.text
        new_format = current_format

        if self._is_printable_ascii(value):
            new_format = 'ASCII'
        elif current_format == 'ASCII':
            new_format = 'Hex'

        if new_format != current_format:
            self.ids.format_spinner.text = new_format
        else:
            self.on_format_change(new_format)

    def on_format_change(self, format_text: str):
        """
        Handles the conversion of the raw byte data into different formats.
        """
        if not self.raw_value:
            self.char_value = ""
            return

        try:
            if format_text == 'Hex':
                self.char_value = self.raw_value.hex()
            elif format_text == 'ASCII':
                self.char_value = self.raw_value.decode('ascii')
            elif format_text == 'JSON':
                try:
                    self.char_value = json.dumps(json.loads(self.raw_value.decode('utf-8')), indent=2)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    self.char_value = "Invalid JSON"
            elif format_text == 'Int8':
                self.char_value = str(struct.unpack('<b', self.raw_value)[0])
            elif format_text == 'UInt8':
                self.char_value = str(struct.unpack('<B', self.raw_value)[0])
            elif format_text == 'Int16':
                self.char_value = str(struct.unpack('<h', self.raw_value)[0])
            elif format_text == 'UInt16':
                self.char_value = str(struct.unpack('<H', self.raw_value)[0])
            elif format_text == 'Int32':
                self.char_value = str(struct.unpack('<i', self.raw_value)[0])
            elif format_text == 'UInt32':
                self.char_value = str(struct.unpack('<I', self.raw_value)[0])
            elif format_text == 'Float32':
                self.char_value = str(struct.unpack('<f', self.raw_value)[0])
            elif format_text == 'Float64':
                self.char_value = str(struct.unpack('<d', self.raw_value)[0])
            else:
                self.char_value = self.raw_value.hex()
        except (struct.error, UnicodeDecodeError):
            self.char_value = "Invalid Format"

    def show_copy_popup(self):
        """Displays a popup to select what to copy."""
        data_to_copy = {
            "char_name": {"name": "Characteristic Name", "value": self.char_name},
            "char_uuid": {"name": "Characteristic UUID", "value": self.char_uuid},
            "full_char_properties": {"name": "Properties", "value": self.full_char_properties},
            "user_description": {"name": "User Description", "value": self.user_description},
            "char_value": {"name": "Value", "value": self.char_value},
        }

        popup = CopyPopup(
            title='Copy Characteristic Info',
            data_dict=data_to_copy,
            selection_state=self._copy_selection_state,
            save_callback=self._save_copy_selection
        )
        popup.open()

    def _save_copy_selection(self, selection):
        """Saves the current selection of checkboxes."""
        self._copy_selection_state = selection


    def toggle_collapse(self):
        self.collapsed = not self.collapsed
