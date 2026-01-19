
import asyncio

from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.popup import Popup

from file_chooser_dialog import FileChooserDialog
from models import LogLevel


class UIManager:
    """
    Manages UI updates and interactions for the BLEScannerApp.
    """

    def __init__(self, app):
        self.app = app

    def log_with_timestamp(self, message: str, level: LogLevel = LogLevel.INFO):
        """Logs a message with a timestamp and level."""
        self.app.log_with_timestamp(message, level)

    def update_connection_ui(self, is_connected: bool):
        """Updates the UI based on the connection status."""
        self.app.is_connected = is_connected
        self.app.is_connecting = False
        if is_connected:
            self.log_with_timestamp("Device connected.", LogLevel.SUCCESS)
            self.app.discover_attributes()
            self.app.root.ids.bottom_nav.switch_to(self.app.root.ids.device_screen_tab)
        else:
            if self.app.selected_device_frame:
                self.app.selected_device_frame.is_selected = False
                self.app.selected_device_frame = None
            self.app.root.ids.device_screen.ids.characteristic_list.clear_widgets()
            self.app.characteristic_frames = {}

    def on_characteristic_read(self, char_frame, value):
        """Handles the UI update after a characteristic read."""
        if value is not None:
            char_frame.raw_value = value
            display_format = char_frame.ids.format_spinner.text
            self.log_with_timestamp(f"Value read from {char_frame.char_uuid} ({display_format}): {char_frame.char_value}", LogLevel.SUCCESS)
            char_frame.ids.value_input.background_color = (0, 1, 0, 1)  # Green for success
            self.app.reset_char_color(char_frame)
        else:
            self.log_with_timestamp(f"Failed to read from {char_frame.char_uuid}", LogLevel.ERROR)

    def on_characteristic_write(self, char_frame, success, characteristic, value_written, write_mode):
        """Handles the UI update after a characteristic write."""
        if success:
            self.log_with_timestamp(f"Value written to {char_frame.char_uuid} ({write_mode}): {value_written}", LogLevel.SUCCESS)
            if "read" in characteristic.properties:
                asyncio.create_task(self.app.read_characteristic(characteristic, char_frame))
        else:
            self.log_with_timestamp(f"Write Error on {char_frame.char_uuid}", LogLevel.ERROR)
            char_frame.ids.value_input.background_color = (1, 0.6, 0.6, 1)

    def on_descriptor_read(self, descriptor, desc_frame, value):
        """Handles the UI update after a descriptor read."""
        if value is not None:
            if isinstance(desc_frame, Label):
                desc_frame.text = f"{value.decode('utf-8')}"
            else:
                desc_frame.desc_value = value.hex()
            self.log_with_timestamp(f"Value read from {descriptor.uuid}: {value.hex()}", LogLevel.SUCCESS)
        else:
            self.log_with_timestamp(f"Failed to read from {descriptor.uuid}", LogLevel.ERROR)

    def on_descriptor_write(self, desc_frame, success):
        """Handles the UI update after a descriptor write."""
        if success:
            self.log_with_timestamp(f"Value written to {desc_frame.desc_uuid}", LogLevel.SUCCESS)
        else:
            self.log_with_timestamp(f"Write Error on {desc_frame.desc_uuid}", LogLevel.ERROR)

    def show_save_dialog(self, title, callback):
        """Shows a save file dialog."""
        self.log_with_timestamp(f"Showing {title} dialog...", LogLevel.INFO)
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
