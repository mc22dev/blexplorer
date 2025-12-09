from kivy.uix.boxlayout import BoxLayout
from kivy.properties import ObjectProperty, StringProperty, BoundedNumericProperty
from kivy.core.clipboard import Clipboard
import struct
import json
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.clock import Clock

from bleak.backends.characteristic import BleakGATTCharacteristic


class Toast(Popup):
    def __init__(self, text, **kwargs):
        super().__init__(**kwargs)
        self.content = Label(text=text)
        self.size_hint = (None, None)
        self.size = (150, 50)
        self.title = ""
        self.separator_height = 0

    def show(self, duration=1):
        self.open()
        Clock.schedule_once(self.dismiss, duration)


class InfoPopup(Popup):
    def __init__(self, title, text, copy_callback, **kwargs):
        super().__init__(**kwargs)
        self.title = title
        self.size_hint = (0.9, 0.4)

        content = BoxLayout(orientation='vertical', padding='10dp', spacing='10dp')

        info_label = Label(text=text, size_hint_y=None)
        info_label.bind(texture_size=info_label.setter('size'))

        buttons = BoxLayout(size_hint_y=None, height='44dp', spacing='10dp')
        copy_button = Button(text='Copy')
        copy_button.bind(on_release=lambda x: copy_callback(text))
        close_button = Button(text='Close')
        close_button.bind(on_release=self.dismiss)

        buttons.add_widget(copy_button)
        buttons.add_widget(close_button)

        content.add_widget(info_label)
        content.add_widget(buttons)

        self.content = content


class CharacteristicFrameKivy(BoxLayout):
    characteristic = ObjectProperty(None)
    char_uuid = StringProperty('')
    short_uuid = StringProperty('')
    char_properties = StringProperty('')
    full_char_properties = StringProperty('')
    char_value = StringProperty('')
    raw_value = ObjectProperty(b'')

    def __init__(self, characteristic: BleakGATTCharacteristic, **kwargs):
        super().__init__(**kwargs)
        self.characteristic = characteristic
        self.char_uuid = characteristic.uuid
        if self.char_uuid.startswith("0000") and self.char_uuid.endswith("-0000-1000-8000-00805f9b34fb"):
            self.short_uuid = f"0x{self.char_uuid[4:8]}"
        else:
            self.short_uuid = f"{self.char_uuid.split('-')[0]}..."

        prop_map = {
            "read": "R",
            "write": "W",
            "write-without-response": "W",
            "notify": "N",
            "indicate": "I",
        }

        # Create the abbreviated properties string
        abbreviated_props = sorted(list(set([prop_map[p] for p in characteristic.properties if p in prop_map])))
        self.char_properties = "/".join(abbreviated_props)

        # Create the full properties string for the tooltip
        self.full_char_properties = "\n".join(sorted(characteristic.properties))

        if "write" not in self.characteristic.properties and "write-without-response" not in self.characteristic.properties:
            self.ids.write_button.disabled = True
            self.ids.value_input.disabled = True

        if "read" not in self.characteristic.properties:
            self.ids.read_button.disabled = True

        if "notify" not in self.characteristic.properties and "indicate" not in self.characteristic.properties:
            self.ids.subscribe_button.disabled = True

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

    def copy_to_clipboard(self, text):
        Clipboard.copy(text)
        Toast(text='Copied!').show()

    def show_info_popup(self):
        popup = InfoPopup(title="Full UUID", text=self.char_uuid, copy_callback=self.copy_to_clipboard)
        popup.open()

    def show_properties_popup(self):
        popup = InfoPopup(title="Properties", text=self.full_char_properties, copy_callback=self.copy_to_clipboard)
        popup.open()
