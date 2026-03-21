import os
import threading
import logging
import asyncio

from kivy.uix.screenmanager import Screen
from kivy.properties import StringProperty, BooleanProperty, ListProperty
from kivy.clock import Clock
from kivy.app import App
from kivy.logger import Logger

try:
    from pyftpdlib.authorizers import DummyAuthorizer
    from pyftpdlib.handlers import FTPHandler
    from pyftpdlib.servers import FTPServer
    HAS_PYFTPDLIB = True
except ImportError:
    HAS_PYFTPDLIB = False

from blescanner.platform import platform_utils

class FTPServerScreen(Screen):
    server_status = StringProperty("Stopped")
    is_running = BooleanProperty(False)
    log_text = StringProperty("")
    server_address = StringProperty("Unknown")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = App.get_running_app()
        self.server = None
        self.server_thread = None

    def on_enter(self, *args):
        self.update_server_info()

    def update_server_info(self):
        ip, _ = platform_utils.get_local_ip_and_mask()
        port = self.app.config_manager.get_setting('ftp_server', 'port')
        if ip:
            self.server_address = f"ftp://{ip}:{port}"
        else:
            self.server_address = f"Unknown (Listen on port {port})"

    def toggle_server(self):
        if self.is_running:
            self.stop_server()
        else:
            self.start_server()

    def start_server(self):
        if not HAS_PYFTPDLIB:
            self.log_message("Error: pyftpdlib not installed")
            return

        if self.is_running:
            return

        try:
            port = int(self.app.config_manager.get_setting('ftp_server', 'port'))
            user = self.app.config_manager.get_setting('ftp_server', 'user')
            password = self.app.config_manager.get_setting('ftp_server', 'password')
            directory = self.app.config_manager.get_setting('ftp_server', 'directory')
            read_only = self.app.config_manager.get_setting('ftp_server', 'read_only') == 'True'

            if directory == '.':
                directory = os.getcwd()

            if not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)

            authorizer = DummyAuthorizer()
            perm = "elradfmwMT" if not read_only else "elr"
            authorizer.add_user(user, password, directory, perm=perm)

            handler = FTPHandler
            handler.authorizer = authorizer
            handler.banner = "BLEScanner FTP Server ready."

            # Redirect pyftpdlib logging to our log_message
            class KivyLoggerHandler(logging.Handler):
                def __init__(self, screen):
                    super().__init__()
                    self.screen = screen
                def emit(self, record):
                    msg = self.format(record)
                    Clock.schedule_once(lambda dt: self.screen.log_message(msg))

            ftp_logger = logging.getLogger('pyftpdlib')
            ftp_logger.setLevel(logging.INFO)
            # Remove old handlers
            for h in ftp_logger.handlers[:]:
                ftp_logger.removeHandler(h)
            ftp_logger.addHandler(KivyLoggerHandler(self))

            self.server = FTPServer(('', port), handler)

            self.server_thread = threading.Thread(target=self._run_server, daemon=True)
            self.server_thread.start()

            self.is_running = True
            self.server_status = "Running"
            self.update_server_info()
            self.log_message(f"Server started on port {port}, root: {directory}")
            if read_only:
                self.log_message("Mode: Read-Only")
            else:
                self.log_message("Mode: Read-Write")

        except Exception as e:
            self.log_message(f"Failed to start server: {e}")
            self.is_running = False
            self.server_status = "Stopped"

    def _run_server(self):
        try:
            self.server.serve_forever()
        except Exception as e:
            Clock.schedule_once(lambda dt: self.log_message(f"Server thread error: {e}"))
        finally:
            Clock.schedule_once(lambda dt: self._on_server_stopped())

    def _on_server_stopped(self):
        self.is_running = False
        self.server_status = "Stopped"
        self.log_message("Server stopped.")

    def stop_server(self):
        if self.server:
            self.server.close_all()
            self.server = None
        self.is_running = False
        self.server_status = "Stopped"

    def log_message(self, message):
        timestamp = Clock.get_time() # or use datetime
        import datetime
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        self.log_text += f"[{ts}] {message}\n"

    def clear_log(self):
        self.log_text = ""
