from kivymd.uix.boxlayout import MDBoxLayout
from kivy.properties import ObjectProperty, StringProperty, NumericProperty
from kivy.app import App
from kivy.core.clipboard import Clipboard
from kivymd.uix.dialog import MDDialog
from kivy.core.window import Window

class DeviceFrameKivy(MDBoxLayout):
    device = ObjectProperty(None)
    adv_data = ObjectProperty(None)
    device_name = StringProperty("Unknown")
    device_address = StringProperty("")
    device_rssi = StringProperty("")
    scan_count = NumericProperty(0)

    def on_device(self, instance, value):
        """Handles updates to the device object."""
        self.device_name = self.device.name or "Unknown"
        self.device_address = self.device.address

    def on_adv_data(self, instance, value):
        """Handles updates to the advertisement data object."""
        self.device_rssi = str(self.adv_data.rssi)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Trigger the on_... methods to populate the UI initially
        self.on_device(self, self.device)
        self.on_adv_data(self, self.adv_data)

    def copy_to_clipboard(self, text):
        Clipboard.copy(text)
        dialog = MDDialog(title='Copied',
                          text=f'"{text}" copied to clipboard.',
                          size_hint=(None, None), size=(300, 100))
        dialog.open()
