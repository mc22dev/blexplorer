from kivy.uix.boxlayout import BoxLayout
from kivy.properties import StringProperty, ObjectProperty, NumericProperty
from kivy.app import App

class SerialMonitorSettings(BoxLayout):
    font_name = StringProperty('Roboto')
    font_size = NumericProperty(12)
    app = ObjectProperty(None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = App.get_running_app()
        self.load_settings()

    def load_settings(self):
        self.font_name = self.app.config_manager.get_setting('serial_monitor', 'font_name')
        self.font_size = int(self.app.config_manager.get_setting('serial_monitor', 'font_size'))
        self.ids.font_spinner.text = self.font_name
        self.ids.font_size_slider.value = self.font_size

    def save_settings(self):
        self.font_name = self.ids.font_spinner.text
        self.font_size = self.ids.font_size_slider.value
        self.app.config_manager.set_setting('serial_monitor', 'font_name', self.font_name)
        self.app.config_manager.set_setting('serial_monitor', 'font_size', int(self.font_size))
        # Apply the setting to the serial monitor screen
        serial_monitor_screen = self.app.root.ids.screen_manager.get_screen('serial_monitor')
        serial_monitor_screen.font_name = self.font_name
        serial_monitor_screen.font_size = self.font_size
