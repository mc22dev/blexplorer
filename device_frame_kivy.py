from kivy.uix.boxlayout import BoxLayout
from kivy.properties import ObjectProperty, StringProperty
from kivy.app import App
from kivy.core.clipboard import Clipboard
from characteristic_frame_kivy import InfoPopup, Toast


class DeviceFrameKivy(BoxLayout):
    device = ObjectProperty(None)
    device_name = StringProperty('')
    device_address = StringProperty('')
    device_rssi = StringProperty('')
    rssi_bars = StringProperty('')

    def __init__(self, device, adv_data, **kwargs):
        super().__init__(**kwargs)
        self.device = device
        self.device_name = device.name or 'Unknown'
        self.device_address = device.address
        self.device_rssi = f"{adv_data.rssi} dBm"
        self.rssi_bars = self._get_rssi_bars(adv_data.rssi)

    def _get_rssi_bars(self, rssi: int) -> str:
        """Converts RSSI value to a 4-bar graphical representation."""
        if rssi >= -67:
            return '████'
        elif rssi >= -75:
            return '███ '
        elif rssi >= -85:
            return '██  '
        elif rssi >= -95:
            return '█   '
        else:
            return '    '

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            # If the touch is on a child button, let the button handle it.
            for child in self.walk():
                if isinstance(child, Button) and child.collide_point(*touch.pos):
                    return super().on_touch_down(touch)
            App.get_running_app().connect_to_device(self.device)
            return True
        return super().on_touch_down(touch)

    def copy_to_clipboard(self, text):
        Clipboard.copy(text)
        Toast(text='Copied!').show()

    def show_rssi_popup(self):
        popup = InfoPopup(title="RSSI", text=self.device_rssi, copy_callback=self.copy_to_clipboard)
        popup.open()
