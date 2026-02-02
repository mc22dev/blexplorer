
import asyncio

from kivy.uix.label import Label
from kivy.uix.popup import Popup

from file_chooser_dialog import FileChooserDialog
from models import LogLevel


class UIManager:
    """
    Manages UI updates and interactions for the BLEScannerApp.
    """

    def __init__(self, log_callback, discover_attributes_callback, read_characteristic_callback, reset_char_color_callback):
        self.log_callback = log_callback
        self.discover_attributes_callback = discover_attributes_callback
        self.read_characteristic_callback = read_characteristic_callback
        self.reset_char_color_callback = reset_char_color_callback
        self.root = None
        self.dialog = None
        self.app_state = None

    def set_app_state(self, app_state):
        self.app_state = app_state

    def update_connection_ui(self, is_connected: bool):
        """Updates the UI based on the connection status."""
        self.app_state.is_connected = is_connected
        self.app_state.is_connecting = False
        if is_connected:
            self.log_callback("Device connected.", LogLevel.SUCCESS)
            self.discover_attributes_callback()
            self.switch_to_device_tab()
        else:
            if self.app_state.selected_device_frame:
                self.app_state.selected_device_frame.is_selected = False
                self.app_state.selected_device_frame = None
            self.clear_characteristic_list()
            self.app_state.characteristic_frames = {}

    def switch_to_device_tab(self):
        """Switches the main view to the device screen tab."""
        self.root.ids.bottom_nav.switch_to(self.root.ids.device_screen_tab)

    def clear_characteristic_list(self):
        """Clears the characteristic list in the device screen."""
        self.root.ids.device_screen.ids.characteristic_list.clear_widgets()

    def on_characteristic_read(self, char_frame, value):
        """Handles the UI update after a characteristic read."""
        if value is not None:
            char_frame.raw_value = value
            display_format = char_frame.ids.format_spinner.text
            self.log_callback(f"Value read from {char_frame.char_uuid} ({display_format}): {char_frame.char_value}", LogLevel.SUCCESS)
            char_frame.ids.value_input.background_color = (0, 1, 0, 1)  # Green for success
            self.reset_char_color_callback(char_frame)
        else:
            self.log_callback(f"Failed to read from {char_frame.char_uuid}", LogLevel.ERROR)

    def on_characteristic_write(self, char_frame, success, characteristic, value_written, write_mode):
        """Handles the UI update after a characteristic write."""
        if success:
            self.log_callback(f"Value written to {char_frame.char_uuid} ({write_mode}): {value_written}", LogLevel.SUCCESS)
            if "read" in characteristic.properties:
                asyncio.create_task(self.read_characteristic_callback(characteristic, char_frame))
        else:
            self.log_callback(f"Write Error on {char_frame.char_uuid}", LogLevel.ERROR)
            char_frame.ids.value_input.background_color = (1, 0.6, 0.6, 1)

    def on_descriptor_read(self, descriptor, frame, value):
        """Handles the UI update after a descriptor read."""
        if value is not None:
            # Handle both CharacteristicFrameKivy and DescriptorFrameKivy
            if 'user_description_label' in frame.ids:
                frame.ids.user_description_label.text = f"{value.decode('utf-8')}"
            elif hasattr(frame, 'desc_value'):
                frame.desc_value = value.hex()
            self.log_callback(f"Value read from {descriptor.uuid}: {value.hex()}", LogLevel.SUCCESS)
        else:
            self.log_callback(f"Failed to read from {descriptor.uuid}", LogLevel.ERROR)

    def on_descriptor_write(self, desc_frame, success):
        """Handles the UI update after a descriptor write."""
        if success:
            self.log_callback(f"Value written to {desc_frame.desc_uuid}", LogLevel.SUCCESS)
        else:
            self.log_callback(f"Write Error on {desc_frame.desc_uuid}", LogLevel.ERROR)

    def show_save_dialog(self, title, callback):
        """Shows a save file dialog."""
        self.log_callback(f"Showing {title} dialog...", LogLevel.INFO)
        content = FileChooserDialog(title=title, callback=callback, dismiss_callback=self.dismiss_popup, mode='save')
        self._open_dialog(title, content)

    def _open_dialog(self, title, content):
        """Helper to create and open a dialog popup."""
        self.dialog = Popup(title=title, content=content, size_hint=(0.9, 0.9))
        self.dialog.open()

    def dismiss_popup(self):
        """Dismisses the currently open dialog."""
        if hasattr(self, 'dialog') and self.dialog:
            self.dialog.dismiss()
