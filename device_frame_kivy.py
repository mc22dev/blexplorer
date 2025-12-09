from kivy.uix.boxlayout import BoxLayout
from kivy.properties import ObjectProperty, StringProperty
from kivy.app import App
from kivy.core.clipboard import Clipboard


class DeviceFrameKivy(BoxLayout):
    device = ObjectProperty(None)
    device_name = StringProperty('')
    device_address = StringProperty('')
    device_rssi = StringProperty('')

    def __init__(self, device, adv_data, **kwargs):
        super().__init__(**kwargs)
        self.device = device
        self.device_name = device.name or 'Unknown'
        self.device_address = device.address
        self.device_rssi = f"RSSI: {adv_data.rssi}"

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            App.get_running_app().connect_to_device(self.device)
            return True
        return super().on_touch_down(touch)

    def copy_to_clipboard(self, text):
        Clipboard.copy(text)
