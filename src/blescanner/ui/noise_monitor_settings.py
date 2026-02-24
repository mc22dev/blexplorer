from kivy.uix.boxlayout import BoxLayout
from kivy.properties import StringProperty, ObjectProperty, ListProperty
from kivy.app import App
import os

class NoiseMonitorSettings(BoxLayout):
    alarm_sound = StringProperty('alert.wav')
    available_sounds = ListProperty([])
    app = ObjectProperty(None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = App.get_running_app()
        self.load_available_sounds()
        self.load_settings()

    def load_available_sounds(self):
        # We need to find the assets/sounds directory
        import sys
        if hasattr(sys, '_MEIPASS'):
            base_path = os.path.join(sys._MEIPASS, 'blescanner')
        else:
            # src/blescanner/ui -> src/blescanner/
            base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

        sounds_dir = os.path.join(base_path, "assets", "sounds")
        if os.path.exists(sounds_dir):
            self.available_sounds = [f for f in os.listdir(sounds_dir) if f.endswith('.wav')]
        else:
            self.available_sounds = ['alert.wav', 'alarm.wav']

    def load_settings(self):
        self.alarm_sound = self.app.config_manager.get_setting('noise_monitor', 'alarm_sound')
        self.ids.sound_spinner.text = self.alarm_sound

    def save_settings(self):
        self.alarm_sound = self.ids.sound_spinner.text
        self.app.config_manager.set_setting('noise_monitor', 'alarm_sound', self.alarm_sound)
        # Apply the setting to the noise monitor screen
        noise_monitor_screen = self.app.root.ids.screen_manager.get_screen('noise_monitor')
        noise_monitor_screen.load_alarm_sound()
