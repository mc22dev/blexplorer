from kivy.uix.boxlayout import BoxLayout
from kivy.properties import StringProperty, ObjectProperty, NumericProperty, BooleanProperty
from kivy.app import App
from kivy.utils import platform
import os

class FTPServerSettings(BoxLayout):
    port = StringProperty('2121')
    user = StringProperty('user')
    password = StringProperty('password')
    directory = StringProperty('.')
    read_only = BooleanProperty(False)
    app = ObjectProperty(None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = App.get_running_app()
        self.load_settings()

    def load_settings(self):
        self.port = self.app.config_manager.get_setting('ftp_server', 'port')
        self.user = self.app.config_manager.get_setting('ftp_server', 'user')
        self.password = self.app.config_manager.get_setting('ftp_server', 'password')
        self.directory = self.app.config_manager.get_setting('ftp_server', 'directory')
        self.read_only = self.app.config_manager.get_setting('ftp_server', 'read_only') == 'True'

        self.ids.port_input.text = self.port
        self.ids.user_input.text = self.user
        self.ids.password_input.text = self.password
        self.ids.directory_input.text = self.directory
        self.ids.read_only_checkbox.active = self.read_only

    def set_external_storage(self):
        path = self.app.platform_utils.get_external_storage_path()
        self.ids.directory_input.text = path

    def save_settings(self):
        self.port = self.ids.port_input.text
        self.user = self.ids.user_input.text
        self.password = self.ids.password_input.text
        self.directory = self.ids.directory_input.text
        self.read_only = self.ids.read_only_checkbox.active

        self.app.config_manager.set_setting('ftp_server', 'port', self.port)
        self.app.config_manager.set_setting('ftp_server', 'user', self.user)
        self.app.config_manager.set_setting('ftp_server', 'password', self.password)
        self.app.config_manager.set_setting('ftp_server', 'directory', self.directory)
        self.app.config_manager.set_setting('ftp_server', 'read_only', str(self.read_only))

        # Notify the screen
        ftp_screen = self.app.root.ids.screen_manager.get_screen('ftp_server')
        ftp_screen.update_server_info()
