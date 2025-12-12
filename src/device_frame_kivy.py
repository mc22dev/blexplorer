from kivymd.uix.boxlayout import MDBoxLayout
from kivy.properties import ObjectProperty, StringProperty, BooleanProperty
from kivy.app import App
from kivy.core.clipboard import Clipboard
from kivymd.uix.dialog import MDDialog
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDRaisedButton
from kivy.core.window import Window

class DeviceFrameKivy(MDBoxLayout):
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
                if isinstance(child, MDRaisedButton) and child.collide_point(*touch.pos):
                    return super().on_touch_down(touch)
            App.get_running_app().connect_to_device(self.device)
            return True
        return super().on_touch_down(touch)

    def copy_to_clipboard(self, text):
        Clipboard.copy(text)
        dialog = MDDialog(title='Copied',
                          text=f'"{text}" copied to clipboard.',
                          size_hint=(None, None), size=(300, 100))
        dialog.open()
