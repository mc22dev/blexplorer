import asyncio
import logging
import pyte
from kivy.app import App
from kivy.uix.screenmanager import Screen
from kivy.properties import BooleanProperty, StringProperty, ListProperty, NumericProperty, ObjectProperty
from kivy.clock import Clock
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.core.window import Window
from blescanner.models import LogLevel

# Optional imports for protocols
try:
    import asyncssh
except ImportError:
    asyncssh = None

try:
    import telnetlib3
except ImportError:
    telnetlib3 = None

logger = logging.getLogger(__name__)

# Standard ANSI colors mapped to Kivy-friendly hex (RGB)
COLOR_MAP = {
    'black': '#000000',
    'red': '#cc0000',
    'green': '#4e9a06',
    'yellow': '#c4a000',
    'blue': '#3465a4',
    'magenta': '#75507b',
    'cyan': '#06989a',
    'white': '#d3d7cf',
}

class TerminalInput(TextInput):
    """
    A hidden TextInput to handle complex text input (dead keys, IME).
    """
    def insert_text(self, substring, from_undo=False):
        app = App.get_running_app()
        screen = app.root.ids.screen_manager.get_screen('terminal')
        if screen.is_connected:
            screen._send_to_connection(substring)
        return # Don't actually insert text into the widget

class TerminalRow(RecycleDataViewBehavior, BoxLayout):
    text = StringProperty("")
    index = NumericProperty(0)
    cursor_x = NumericProperty(-1)
    char_width = NumericProperty(10)
    left_padding = NumericProperty(5)

    def refresh_view_attrs(self, rv, index, data):
        self.index = index
        return super().refresh_view_attrs(rv, index, data)

class KivyScreen(pyte.Screen):
    """
    Custom pyte screen that notifies when it changes.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.any_changes = False

    def draw(self, *args, **kwargs):
        super().draw(*args, **kwargs)
        self.any_changes = True

    def cursor_position_update(self, *args, **kwargs):
        super().cursor_position_update(*args, **kwargs)
        self.any_changes = True

    def erase_in_display(self, *args, **kwargs):
        super().erase_in_display(*args, **kwargs)
        self.any_changes = True

    def erase_in_line(self, *args, **kwargs):
        super().erase_in_line(*args, **kwargs)
        self.any_changes = True

class TerminalScreen(Screen):
    is_connected = BooleanProperty(False)
    output_data = ListProperty([])
    serial_ports = ListProperty([])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = App.get_running_app()
        self.columns = 80
        self.rows = 24
        self.pyte_screen = KivyScreen(self.columns, self.rows)
        self.pyte_stream = pyte.Stream(self.pyte_screen)
        self.connection = None
        self.transport = None
        self.protocol = None
        self.writer = None
        self.chan = None
        self._update_event = None

    def on_enter(self, *args):
        self.refresh_serial_ports()
        Window.bind(on_key_down=self._on_key_down)
        if self.is_connected:
            def _focus(dt):
                self.ids.hidden_input.focus = True
            Clock.schedule_once(_focus, 0.1)
        if not self._update_event:
            self._update_event = Clock.schedule_interval(self.update_ui, 1.0 / 30.0)

    def on_leave(self, *args):
        Window.unbind(on_key_down=self._on_key_down)
        self.ids.hidden_input.focus = False
        if self._update_event:
            self._update_event.cancel()
            self._update_event = None

    def on_protocol_change(self, protocol):
        if protocol == 'SSH':
            self.ids.port_input.text = '22'
        elif protocol == 'Telnet':
            self.ids.port_input.text = '23'

    def refresh_serial_ports(self, *args):
        ports = self.app.platform_utils.list_serial_ports()
        self.serial_ports = [port.device for port in ports]
        if self.serial_ports and self.ids.port_spinner.text == 'Select Port':
             self.ids.port_spinner.text = self.serial_ports[0]

    def toggle_connection(self):
        if self.is_connected:
            self.disconnect()
        else:
            asyncio.create_task(self.connect())

    async def connect(self):
        protocol = self.ids.protocol_spinner.text
        host = self.ids.host_input.text
        port_str = self.ids.port_input.text
        user = self.ids.user_input.text
        password = self.ids.password_input.text

        try:
            if protocol == 'SSH':
                if not asyncssh:
                    self.log("asyncssh not installed", LogLevel.ERROR)
                    return
                self.log(f"Connecting to {host}:{port_str} via SSH...")
                self.connection = await asyncssh.connect(host, port=int(port_str), username=user, password=password, known_hosts=None)

                # create_session without a command requests a shell automatically.
                # It returns (channel, session).
                self.chan, self.session = await self.connection.create_session(
                    lambda: SSHClientSession(self),
                    term_type='xterm-color',
                    term_size=(self.columns, self.rows)
                )

                self.is_connected = True
                self.ids.hidden_input.focus = True
                self.log(f"Connected to {host} via SSH")

            elif protocol == 'Telnet':
                if not telnetlib3:
                    self.log("telnetlib3 not installed", LogLevel.ERROR)
                    return
                # telnetlib3.open_connection returns (reader, writer)
                self.reader, self.writer = await telnetlib3.open_connection(host, int(port_str))
                self.is_connected = True
                self.ids.hidden_input.focus = True
                self.log(f"Connected to {host} via Telnet")
                asyncio.create_task(self._telnet_read_loop())

            elif protocol == 'Serial':
                serial_port = self.ids.port_spinner.text
                baudrate = int(self.ids.bitrate_spinner.text)
                self.transport, self.protocol = await self.app.platform_utils.create_serial_connection(
                    asyncio.get_event_loop(),
                    lambda: SerialProtocol(self),
                    serial_port,
                    baudrate=baudrate
                )
                self.is_connected = True
                self.ids.hidden_input.focus = True
                self.log(f"Connected to {serial_port} at {baudrate} bps")

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            self.log(f"Connection failed: {e}", LogLevel.ERROR)
            logger.error(f"Terminal connection error details:\n{error_details}")
            self.disconnect()

    async def _telnet_read_loop(self):
        try:
            while self.is_connected:
                data = await self.reader.read(1024)
                if not data:
                    break
                self.feed_data(data)
        except Exception as e:
            self.log(f"Telnet read error: {e}", LogLevel.ERROR)
        finally:
            self.disconnect()

    def disconnect(self):
        self.is_connected = False
        if self.transport:
            self.transport.close()
            self.transport = None
        if self.connection:
            self.connection.close()
            self.connection = None
        if self.writer:
            self.writer.close()
            self.writer = None
        self.chan = None
        self.log("Disconnected")

    def feed_data(self, data):
        if isinstance(data, str):
            self.pyte_stream.feed(data)
        else:
            try:
                self.pyte_stream.feed(data.decode('utf-8', errors='replace'))
            except Exception as e:
                logger.error(f"Error feeding data: {e}")

    def get_line_markup(self, y):
        line_str = ""
        current_fg = None
        current_bold = False

        row = self.pyte_screen.buffer[y]

        for x in range(self.pyte_screen.columns):
            char = row[x]

            style_changed = (char.fg != current_fg or char.bold != current_bold)

            if style_changed:
                # Close previous tags
                if current_bold: line_str += "[/b]"
                if current_fg and current_fg in COLOR_MAP: line_str += "[/color]"

                # Open new tags
                current_fg = char.fg
                current_bold = char.bold

                if current_fg and current_fg in COLOR_MAP:
                    line_str += f"[color={COLOR_MAP[current_fg]}]"
                if current_bold:
                    line_str += "[b]"

            # Escape markup characters
            c = char.data
            if c == '[': c = '[['
            elif c == ']': c = ']]'
            line_str += c

        # Close tags at end of line
        if current_bold: line_str += "[/b]"
        if current_fg and current_fg in COLOR_MAP: line_str += "[/color]"

        return line_str

    def update_ui(self, dt):
        if not self.pyte_screen.any_changes:
            return

        self.pyte_screen.any_changes = False
        new_data = []
        cursor_x = self.pyte_screen.cursor.x
        cursor_y = self.pyte_screen.cursor.y

        for y in range(self.pyte_screen.lines):
            row_cursor_x = cursor_x if y == cursor_y else -1
            new_data.append({
                'text': self.get_line_markup(y),
                'cursor_x': row_cursor_x
            })

        self.output_data = new_data

    def on_touch_down(self, touch):
        res = super().on_touch_down(touch)

        # Delay focus check to allow focus to settle after touch processing
        def _check_focus(dt):
            # If the user clicked on a settings input, let it keep focus
            if any(ti.focus for ti in [self.ids.host_input, self.ids.port_input, self.ids.user_input, self.ids.password_input]):
                return

            # Otherwise, if connected, ensure the hidden terminal input has focus
            if self.is_connected:
                 self.ids.hidden_input.focus = True

        Clock.schedule_once(_check_focus)
        return res

    def _on_key_down(self, window, key, scancode, codepoint, modifier):
        if not self.manager or self.manager.current != self.name:
            return

        # Don't capture keys if any settings input has focus
        if any(ti.focus for ti in [self.ids.host_input, self.ids.port_input, self.ids.user_input, self.ids.password_input]):
            return False

        if not self.is_connected:
            return

        # Mapping for some keys
        key_map = {
            273: '\x1b[A', # Up
            274: '\x1b[B', # Down
            275: '\x1b[C', # Right
            276: '\x1b[D', # Left
            13: '\r',      # Enter
            8: '\x7f',     # Backspace
            9: '\t',      # Tab
            27: '\x1b',    # Escape
        }

        if 'ctrl' in modifier:
            if codepoint:
                # Basic Ctrl+Key support (A=1, B=2, ...)
                val = ord(codepoint.lower()) - ord('a') + 1
                if 1 <= val <= 26:
                    self._send_to_connection(chr(val))
                    return True

        if key in key_map:
            self._send_to_connection(key_map[key])
            return True

        return False

    def _send_to_connection(self, data):
        if not self.is_connected:
            return

        protocol = self.ids.protocol_spinner.text
        if protocol == 'SSH' and self.chan:
            self.chan.write(data)
        elif protocol == 'Telnet' and self.writer:
            self.writer.write(data)
        elif protocol == 'Serial' and self.transport:
            self.transport.write(data.encode('utf-8'))

    def clear_terminal(self):
        self.pyte_screen.reset()
        self.pyte_screen.any_changes = True

    def save_session(self):
        """
        Opens a save dialog to save the current terminal screen content to a file.
        """
        self.app.ui_manager.show_save_dialog(
            title="Save Terminal Session",
            callback=self._on_save_session
        )

    def _on_save_session(self, filepath):
        """
        Callback from the save dialog to write the terminal content to the chosen file.
        """
        if not filepath:
            return
        try:
            # Get the current display content from pyte screen
            # Strip trailing spaces from each line for a cleaner file
            content = "\n".join(line.rstrip() for line in self.pyte_screen.display)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            self.log(f"Session saved to {filepath}")
        except Exception as e:
            self.log(f"Failed to save session: {e}", LogLevel.ERROR)

    def log(self, message, level=LogLevel.INFO):
        self.app.log_with_timestamp(f"[Terminal] {message}", level)

class SSHClientSession(asyncssh.SSHClientSession if asyncssh else object):
    def __init__(self, screen):
        self.screen = screen

    def data_received(self, data, datatype):
        self.screen.feed_data(data)

    def connection_lost(self, exc):
        self.screen.disconnect()

class SerialProtocol(asyncio.Protocol):
    def __init__(self, screen):
        self.screen = screen

    def data_received(self, data):
        self.screen.feed_data(data)

    def connection_lost(self, exc):
        self.screen.disconnect()
