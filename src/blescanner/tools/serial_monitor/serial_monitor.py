import asyncio
import os
from kivy.app import App
from kivy.uix.screenmanager import Screen
from kivy.properties import BooleanProperty, StringProperty, ListProperty
from kivy.clock import Clock
import serial.tools.list_ports
import serial_asyncio
from blescanner.models import LogLevel


class SerialMonitorScreen(Screen):
    is_connected = BooleanProperty(False)
    serial_ports = ListProperty([])
    output_text = StringProperty("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.serial_port = None
        self.read_task = None
        Clock.schedule_once(self.refresh_serial_ports)

    def on_enter(self, *args):
        """Called when the screen is entered."""
        self.refresh_serial_ports()

    def refresh_serial_ports(self, *args):
        self.serial_ports = [port.device for port in serial.tools.list_ports.comports()]
        port_spinner = self.ids.get('port_spinner')
        if port_spinner:
            port_spinner.values = self.serial_ports
            # If the current selection is no longer valid, reset it
            if port_spinner.text not in self.serial_ports:
                port_spinner.text = 'Select Port'

    async def connect(self):
        port = self.ids.port_spinner.text
        if port == 'Select Port':
            self.output_text += "[ERROR] Please select a serial port.\\n"
            return

        baudrate = int(self.ids.bitrate_spinner.text)
        databits = int(self.ids.databits_spinner.text)
        parity = self.ids.parity_spinner.text
        stopbits = float(self.ids.stopbits_spinner.text)

        coro = serial_asyncio.create_serial_connection(
            asyncio.get_event_loop(),
            lambda: SerialProtocol(self),
            port,
            baudrate=baudrate,
            bytesize=databits,
            parity=parity,
            stopbits=stopbits
        )
        try:
            self.transport, self.protocol = await coro
            self.is_connected = True
            self.output_text += f"[INFO] Connected to {port}\\n"
        except serial.SerialException as e:
            self.output_text += f"[ERROR] Could not connect to {port}: {e}\\n"
            self.is_connected = False
        except Exception as e:
            self.output_text += f"[ERROR] An unexpected error occurred: {e}\\n"
            self.is_connected = False

    def disconnect(self):
        if self.is_connected and self.transport:
            self.transport.close()
            # The connection_lost callback will handle the state change
        else:
            self.is_connected = False
            self.output_text += "[INFO] Already disconnected\\n"


    def toggle_connection(self):
        if self.is_connected:
            self.disconnect()
        else:
            asyncio.create_task(self.connect())

    def send_data(self):
        if self.is_connected and self.transport:
            data = self.ids.input_text.text
            self.transport.write(data.encode('utf-8'))
            self.ids.input_text.text = ""

    def clear_log(self):
        self.output_text = ""

    def save_log(self):
        app = App.get_running_app()
        if app:
            app.ui_manager.show_save_dialog("Save Serial Log", self._do_save_log)

    def _do_save_log(self, path, selection):
        app = App.get_running_app()
        if not selection:
            if app:
                app.ui_manager.dismiss_popup()
            return
        filepath = os.path.join(path, selection[0])
        if not filepath.lower().endswith('.txt'):
            filepath += '.txt'
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(self.ids.output_text.text)
            if app:
                app.log_with_timestamp(f"Serial log saved to {filepath}", LogLevel.SUCCESS)
        except IOError as e:
            if app:
                app.log_with_timestamp(f"Error saving serial log: {e}", LogLevel.ERROR)
        finally:
            if app:
                app.ui_manager.dismiss_popup()

class SerialProtocol(asyncio.Protocol):
    def __init__(self, screen):
        super().__init__()
        self.screen = screen
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport

    def data_received(self, data):
        # Schedule the UI update on the main Kivy thread
        Clock.schedule_once(lambda dt: self._update_output(data))

    def _update_output(self, data):
        try:
            text = data.decode('utf-8', errors='replace')
            self.screen.output_text += text
            # Auto-scroll
            scroll_view = self.screen.ids.get('scroll_view')
            if scroll_view:
                scroll_view.scroll_y = 0
        except Exception as e:
            app = App.get_running_app()
            if app:
                app.log_with_timestamp(f"Error decoding serial data: {e}", LogLevel.ERROR)

    def connection_lost(self, exc):
        # Schedule the UI update on the main Kivy thread
        Clock.schedule_once(lambda dt: self._handle_disconnection(exc))

    def _handle_disconnection(self, exc):
        if self.screen.is_connected:
            self.screen.is_connected = False
            self.screen.transport = None
            self.screen.protocol = None
            self.screen.output_text += "[INFO] Disconnected\\n"
            if exc:
                self.screen.output_text += f"[ERROR] Connection lost: {exc}\\n"
