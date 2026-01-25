import asyncio
import os
from kivy.app import App
from kivy.uix.screenmanager import Screen
from kivy.properties import BooleanProperty, StringProperty, ListProperty, NumericProperty
from kivy.clock import Clock
import serial.tools.list_ports
import serial_asyncio
from blescanner.models import LogLevel


class SerialMonitorScreen(Screen):
    is_connected = BooleanProperty(False)
    serial_ports = ListProperty([])
    output_text = StringProperty("")
    font_name = StringProperty("Roboto")
    font_size = NumericProperty(12)
    char_delay = NumericProperty(0)
    rx_bytes = NumericProperty(0)
    tx_bytes = NumericProperty(0)
    rx_speed_str = StringProperty("0 B/s")
    tx_speed_str = StringProperty("0 B/s")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.serial_port = None
        self.read_task = None
        self.app = App.get_running_app()
        self.speed_update_task = None
        self._last_rx_bytes = 0
        self._last_tx_bytes = 0
        Clock.schedule_once(self.refresh_serial_ports)

    def on_enter(self, *args):
        """Called when the screen is entered."""
        self.refresh_serial_ports()
        Clock.schedule_once(lambda dt: self.load_settings())

    def on_leave(self, *args):
        """Called when the screen is left."""
        self.save_settings()

    def load_settings(self):
        """Loads settings from the config manager and applies them."""
        self.font_name = self.app.config_manager.get_setting('serial_monitor', 'font_name')
        self.font_size = int(self.app.config_manager.get_setting('serial_monitor', 'font_size'))
        self.ids.eol_spinner.text = self.app.config_manager.get_setting('serial_monitor', 'eol')
        delay = self.app.config_manager.get_setting('serial_monitor', 'char_delay')
        self.char_delay = int(delay)
        self.ids.delay_input.text = str(delay)

        last_port = self.app.config_manager.get_setting('serial_monitor', 'last_used_port')
        if last_port and last_port in self.serial_ports:
            self.ids.port_spinner.text = last_port
            port_section = f'serial_monitor_ports_{last_port}'
            if self.app.config_manager.config.has_section(port_section):
                self.ids.bitrate_spinner.text = self.app.config_manager.get_setting(port_section, 'baudrate', default='115200')
                self.ids.databits_spinner.text = self.app.config_manager.get_setting(port_section, 'databits', default='8')
                self.ids.parity_spinner.text = self.app.config_manager.get_setting(port_section, 'parity', default='N')
                self.ids.stopbits_spinner.text = self.app.config_manager.get_setting(port_section, 'stopbits', default='1')

    def save_settings(self):
        """Saves current settings."""
        self.app.config_manager.set_setting('serial_monitor', 'font_name', self.font_name)
        self.app.config_manager.set_setting('serial_monitor', 'font_size', int(self.font_size))
        self.app.config_manager.set_setting('serial_monitor', 'eol', self.ids.eol_spinner.text)
        self.app.config_manager.set_setting('serial_monitor', 'char_delay', self.ids.delay_input.text)
        port = self.ids.port_spinner.text
        if port != 'Select Port':
            self.app.config_manager.set_setting('serial_monitor', 'last_used_port', port)
            port_section = f'serial_monitor_ports_{port}'
            self.app.config_manager.set_setting(port_section, 'baudrate', self.ids.bitrate_spinner.text)
            self.app.config_manager.set_setting(port_section, 'databits', self.ids.databits_spinner.text)
            self.app.config_manager.set_setting(port_section, 'parity', self.ids.parity_spinner.text)
            self.app.config_manager.set_setting(port_section, 'stopbits', self.ids.stopbits_spinner.text)

    def refresh_serial_ports(self, *args):
        ports = serial.tools.list_ports.comports()

        def sort_key(port):
            """Prioritize ttyUSB and ttyACM ports."""
            if port.device.startswith('/dev/ttyUSB') or port.device.startswith('/dev/ttyACM'):
                return (0, port.device)
            return (1, port.device)

        sorted_ports = sorted(ports, key=sort_key)
        self.serial_ports = [port.device for port in sorted_ports]

        if self.serial_ports:
            port_spinner = self.ids.get('port_spinner')
            if port_spinner:
                port_spinner.values = self.serial_ports
                last_port = self.app.config_manager.get_setting('serial_monitor', 'last_used_port')
                if last_port in self.serial_ports:
                    port_spinner.text = last_port
                elif port_spinner.text not in self.serial_ports:
                    port_spinner.text = self.serial_ports[0]
        else:
            self.ids.port_spinner.text = 'Select Port'
            self.ids.port_spinner.values = []


    async def connect(self):
        port = self.ids.port_spinner.text
        if port == 'Select Port' or not self.serial_ports:
            self.output_text += "[ERROR] Please select a serial port.\n"
            return

        baudrate_str = self.ids.bitrate_spinner.text
        databits_str = self.ids.databits_spinner.text
        parity = self.ids.parity_spinner.text
        stopbits_str = self.ids.stopbits_spinner.text

        # Save settings for this port
        self.save_settings()

        coro = serial_asyncio.create_serial_connection(
            asyncio.get_event_loop(),
            lambda: SerialProtocol(self),
            port,
            baudrate=int(baudrate_str),
            bytesize=int(databits_str),
            parity=parity,
            stopbits=float(stopbits_str)
        )
        try:
            self.transport, self.protocol = await coro
            self.is_connected = True
            self.output_text += f"[INFO] Connected to {port}\n"
            self.rx_bytes = 0
            self.tx_bytes = 0
            self._last_rx_bytes = 0
            self._last_tx_bytes = 0
            self.speed_update_task = Clock.schedule_interval(self._update_speeds, 1)

        except serial.SerialException as e:
            self.output_text += f"[ERROR] Could not connect to {port}: {e}\n"
            self.is_connected = False
        except Exception as e:
            self.output_text += f"[ERROR] An unexpected error occurred: {e}\n"
            self.is_connected = False

    def disconnect(self):
        if self.is_connected and self.transport:
            if self.speed_update_task:
                self.speed_update_task.cancel()
                self.speed_update_task = None
            self.transport.close()
            # The connection_lost callback will handle the state change
        else:
            self.is_connected = False
            self.output_text += "[INFO] Already disconnected\n"


    def toggle_connection(self):
        if self.is_connected:
            self.disconnect()
        else:
            asyncio.create_task(self.connect())

    def send_data(self):
        if not self.is_connected or not self.transport:
            return
        asyncio.create_task(self.do_send_data())


    async def do_send_data(self):
        data_to_send = self.ids.input_text.text
        eol = self.ids.eol_spinner.text
        delay_ms_str = self.ids.delay_input.text

        try:
            delay_ms = int(delay_ms_str)
            if not 0 <= delay_ms <= 1000:
                self.output_text += "[ERROR] Delay must be between 0 and 1000 ms.\n"
                return
            self.char_delay = delay_ms
            self.save_settings()
        except ValueError:
            self.output_text += "[ERROR] Invalid delay value.\n"
            return

        if eol == 'Hex':
            try:
                # Remove spaces and convert hex string to bytes
                data_bytes = bytes.fromhex(data_to_send.replace(" ", ""))
            except ValueError:
                self.output_text += "[ERROR] Invalid hexadecimal data.\n"
                return
        else:
            if eol == 'LF':
                data_to_send += '\n'
            elif eol == 'CR':
                data_to_send += '\r'
            elif eol == 'LF/CR':
                data_to_send += '\n\r'
            data_bytes = data_to_send.encode('utf-8')

        num_bytes = len(data_bytes)
        if self.char_delay > 0:
            delay_s = self.char_delay / 1000.0
            for byte in data_bytes:
                self.transport.write(bytes([byte]))
                await asyncio.sleep(delay_s)
        else:
            self.transport.write(data_bytes)

        self.tx_bytes += num_bytes
        self.ids.input_text.text = ""

        def refocus(dt):
            self.ids.input_text.focus = True
        Clock.schedule_once(refocus)


    def clear_log(self):
        self.output_text = ""
        self.rx_bytes = 0
        self.tx_bytes = 0
        self._last_rx_bytes = 0
        self._last_tx_bytes = 0

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

    def _update_speeds(self, dt):
        """Calculates and updates the RX/TX speed labels."""
        rx_speed = self.rx_bytes - self._last_rx_bytes
        tx_speed = self.tx_bytes - self._last_tx_bytes
        self._last_rx_bytes = self.rx_bytes
        self._last_tx_bytes = self.tx_bytes

        self.rx_speed_str = f"{self._format_speed(rx_speed)}/s"
        self.tx_speed_str = f"{self._format_speed(tx_speed)}/s"

    @staticmethod
    def _format_speed(num_bytes):
        """Formats a number of bytes into a human-readable string."""
        if num_bytes < 1024:
            return f"{num_bytes} B"
        elif num_bytes < 1024 * 1024:
            return f"{num_bytes / 1024:.2f} KB"
        else:
            return f"{num_bytes / (1024 * 1024):.2f} MB"


class SerialProtocol(asyncio.Protocol):
    def __init__(self, screen):
        super().__init__()
        self.screen = screen
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport

    def data_received(self, data):
        # Schedule the UI update on the main Kivy thread
        self.screen.rx_bytes += len(data)
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
            if self.screen.speed_update_task:
                self.screen.speed_update_task.cancel()
                self.screen.speed_update_task = None
            self.screen.is_connected = False
            self.screen.transport = None
            self.screen.protocol = None
            self.screen.output_text += "[INFO] Disconnected\n"
            if exc:
                self.screen.output_text += f"[ERROR] Connection lost: {exc}\n"
