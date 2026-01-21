from kivy.uix.boxlayout import BoxLayout
from kivy.properties import ObjectProperty, StringProperty, BooleanProperty
from kivy.core.clipboard import Clipboard
import struct
import json
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.clock import Clock
from kivy.uix.checkbox import CheckBox
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.core.window import Window


from bleak.backends.characteristic import BleakGATTCharacteristic

from blescanner.ble.gatt import GATT_CHARACTERISTICS


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
        content = BoxLayout(orientation='vertical', padding="8dp")

        options = {
            "char_name": "Characteristic Name",
            "char_uuid": "Characteristic UUID",
            "full_char_properties": "Properties",
            "user_description": "User Description",
            "char_value": "Value"
        }

        checkboxes = {}

        scroll_content = BoxLayout(orientation='vertical', size_hint_y=None)
        scroll_content.bind(minimum_height=scroll_content.setter('height'))

        for key, text in options.items():
            value = getattr(self, key)
            if value:
                box = BoxLayout(orientation='horizontal', size_hint_y=None, height='60dp', spacing=5)

                chk = CheckBox(size_hint_x=None, width='48dp', active=key in self._copy_selection_state)
                box.add_widget(chk)

                text_layout = BoxLayout(orientation='vertical')
                text_layout.add_widget(Label(text=text, halign='left', size_hint_y=None, height='20dp', text_size=(Window.width * 0.6, None)))
                text_layout.add_widget(TextInput(text=str(value), readonly=True, size_hint_y=None, height='30dp'))
                box.add_widget(text_layout)

                scroll_content.add_widget(box)
                checkboxes[key] = chk

        select_buttons = BoxLayout(size_hint_y=None, height='30dp', spacing=5)
        select_all_button = Button(text="Select All")
        deselect_all_button = Button(text="Deselect All")
        select_buttons.add_widget(select_all_button)
        select_buttons.add_widget(deselect_all_button)
        content.add_widget(select_buttons)

        def select_all(instance):
            for chk in checkboxes.values():
                chk.active = True

        def deselect_all(instance):
            for chk in checkboxes.values():
                chk.active = False

        select_all_button.bind(on_release=select_all)
        deselect_all_button.bind(on_release=deselect_all)

        scroll_view = ScrollView(size_hint=(1, 1))
        scroll_view.add_widget(scroll_content)
        content.add_widget(scroll_view)

        copy_button = Button(text="Copy", size_hint_y=None, height='44dp')

        def do_copy(instance):
            self._copy_selected_to_clipboard(checkboxes)
            popup.dismiss()

        copy_button.bind(on_release=do_copy)
        content.add_widget(copy_button)

        popup = Popup(title='Copy Characteristic Info',
                      content=content,
                      size_hint=(0.9, 0.9))

        popup.bind(on_dismiss=lambda instance: self._save_copy_selection(checkboxes))
        popup.open()

    def _save_copy_selection(self, checkboxes):
        """Saves the current selection of checkboxes."""
        self._copy_selection_state = {key for key, chk in checkboxes.items() if chk.active}

    def _copy_selected_to_clipboard(self, checkboxes):
        """Copies the selected device information to the clipboard."""
        to_copy = []
        for key, chk in checkboxes.items():
            if chk.active:
                to_copy.append(str(getattr(self, key)))

        text_to_copy = "\n".join(to_copy)
        Clipboard.copy(text_to_copy)

        popup = Popup(title='Copied',
                      content=Label(text=f'Selected info copied to clipboard.'),
                      size_hint=(None, None), size=(400, 100))
        popup.open()


    def toggle_collapse(self):
        self.collapsed = not self.collapsed
