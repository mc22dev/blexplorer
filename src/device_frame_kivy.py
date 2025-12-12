from kivy.uix.boxlayout import BoxLayout
from kivy.properties import ObjectProperty, StringProperty, BooleanProperty
from kivy.app import App
from kivy.core.clipboard import Clipboard
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.core.window import Window

class DeviceFrameKivy(BoxLayout):
    device = ObjectProperty(None)
    adv_data = ObjectProperty(None)
    device_name = StringProperty("Unknown")
    device_address = StringProperty("")
    device_rssi = StringProperty("")
    hovered = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.device_name = self.device.name or "Unknown"
        self.device_address = self.device.address
        self.device_rssi = str(self.adv_data.rssi)
        Window.bind(mouse_pos=self.on_mouse_pos)

    def on_mouse_pos(self, *args):
        pos = args[1]
        if not self.get_root_window():
            return
        local_pos = self.to_widget(*pos)
        self.hovered = self.collide_point(*local_pos)

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            for child in self.walk(restrict=True):
                if isinstance(child, Button) and child.collide_point(*touch.pos):
                    return super().on_touch_down(touch)
            App.get_running_app().connect_to_device(self.device)
            return True
        return super().on_touch_down(touch)

    def copy_to_clipboard(self, text):
        Clipboard.copy(text)
        popup = Popup(title='Copied',
                      content=Label(text=f'"{text}" copied to clipboard.'),
                      size_hint=(None, None), size=(300, 100))
        popup.open()
