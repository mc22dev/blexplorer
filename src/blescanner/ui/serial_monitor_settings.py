from kivy.uix.boxlayout import BoxLayout
from kivy.properties import StringProperty, ObjectProperty
from kivy.app import App

class SerialMonitorSettings(BoxLayout):
    font_name = StringProperty('Roboto')
    app = ObjectProperty(None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = App.get_running_app()
        self.load_settings()

    def load_settings(self):
        self.font_name = self.app.config_manager.get_setting('serial_monitor', 'font_name')
        self.ids.font_spinner.text = self.font_name

    def save_settings(self):
        self.font_name = self.ids.font_spinner.text
        self.app.config_manager.set_setting('serial_monitor', 'font_name', self.font_name)
        # Apply the setting to the serial monitor screen
        serial_monitor_screen = self.app.root.ids.screen_manager.get_screen('serial_monitor')
        serial_monitor_screen.font_name = self.font_name
