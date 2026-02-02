from kivymd.uix.boxlayout import MDBoxLayout
from kivy.properties import ObjectProperty, StringProperty
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

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.device_name = self.device.name or "Unknown"
        self.device_address = self.device.address
        self.device_rssi = str(self.adv_data.rssi)

    def copy_to_clipboard(self, text):
        Clipboard.copy(text)
        dialog = MDDialog(title='Copied',
                          text=f'"{text}" copied to clipboard.',
                          size_hint=(None, None), size=(300, 100))
        dialog.open()
