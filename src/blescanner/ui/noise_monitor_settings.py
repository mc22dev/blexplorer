from kivy.uix.boxlayout import BoxLayout
from kivy.properties import StringProperty, ObjectProperty, ListProperty, NumericProperty
from kivy.app import App
import os

class NoiseMonitorSettings(BoxLayout):
    alarm_sound = StringProperty('alert.wav')
    sensitivity = NumericProperty(1.0)
    num_bars = NumericProperty(9)
    average_time = NumericProperty(500)
    alarm_cooldown = NumericProperty(2)
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
        self.sensitivity = float(self.app.config_manager.get_setting('noise_monitor', 'sensitivity'))
        self.num_bars = int(self.app.config_manager.get_setting('noise_monitor', 'num_bars', default='9'))
        self.average_time = int(self.app.config_manager.get_setting('noise_monitor', 'average_time', default='500'))
        self.alarm_cooldown = int(self.app.config_manager.get_setting('noise_monitor', 'alarm_cooldown', default='2'))
        self.ids.sound_spinner.text = self.alarm_sound
        self.ids.sensitivity_slider.value = self.sensitivity
        self.ids.num_bars_slider.value = self.num_bars
        self.ids.average_time_slider.value = self.average_time
        self.ids.alarm_cooldown_slider.value = self.alarm_cooldown

    def save_settings(self):
        self.alarm_sound = self.ids.sound_spinner.text
        self.sensitivity = self.ids.sensitivity_slider.value
        self.num_bars = int(self.ids.num_bars_slider.value)
        self.average_time = int(self.ids.average_time_slider.value)
        self.alarm_cooldown = int(self.ids.alarm_cooldown_slider.value)
        self.app.config_manager.set_setting('noise_monitor', 'alarm_sound', self.alarm_sound)
        self.app.config_manager.set_setting('noise_monitor', 'sensitivity', str(self.sensitivity))
        self.app.config_manager.set_setting('noise_monitor', 'num_bars', str(self.num_bars))
        self.app.config_manager.set_setting('noise_monitor', 'average_time', str(self.average_time))
        self.app.config_manager.set_setting('noise_monitor', 'alarm_cooldown', str(self.alarm_cooldown))
        # Apply the setting to the noise monitor screen
        noise_monitor_screen = self.app.root.ids.screen_manager.get_screen('noise_monitor')
        noise_monitor_screen.load_alarm_sound()
        noise_monitor_screen.sensitivity = self.sensitivity
        noise_monitor_screen.num_bars = self.num_bars
        noise_monitor_screen.average_time = self.average_time
        noise_monitor_screen.alarm_cooldown = self.alarm_cooldown
