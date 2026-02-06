import asyncio
import logging
import os
import pyte
from kivy.app import App
from kivy.uix.screenmanager import Screen
from kivy.properties import BooleanProperty, StringProperty, ListProperty, NumericProperty, ObjectProperty
from kivy.clock import Clock
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle
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
    'red': '#cd0000',
    'green': '#00cd00',
    'yellow': '#cdcd00',
    'blue': '#0000ee',
    'magenta': '#cd00cd',
    'cyan': '#00cdcd',
    'white': '#e5e5e5',
    # Bright versions
    'brightblack': '#7f7f7f',
    'brightred': '#ff0000',
    'brightgreen': '#00ff00',
    'brightyellow': '#ffff00',
    'brightblue': '#5c5cff',
    'brightmagenta': '#ff00ff',
    'brightcyan': '#00ffff',
    'brightwhite': '#ffffff',
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
    bg_data = ListProperty([])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(pos=self._draw_backgrounds, size=self._draw_backgrounds, char_width=self._draw_backgrounds)

    def refresh_view_attrs(self, rv, index, data):
        self.index = index
        res = super().refresh_view_attrs(rv, index, data)
        self._draw_backgrounds()
        return res

    def on_bg_data(self, instance, value):
        self._draw_backgrounds()

    def _draw_backgrounds(self, *args):
        if not self.canvas:
            return

        self.canvas.before.clear()
        if not self.bg_data:
            return

        with self.canvas.before:
            i = 0
            n = len(self.bg_data)
            while i < n:
                color_hex = self.bg_data[i]
                # Default background is handled by the app's theme or transparency
                # We only draw if it's not 'default' and not black (common terminal bg)
                if color_hex == 'default' or color_hex == '#000000':
                    i += 1
                    continue

                # Group adjacent same colors for better performance
                start_i = i
                while i < n and self.bg_data[i] == color_hex:
                    i += 1

                count = i - start_i

                try:
                    r = int(color_hex[1:3], 16) / 255.0
                    g = int(color_hex[3:5], 16) / 255.0
                    b = int(color_hex[5:7], 16) / 255.0
                    Color(r, g, b, 1)
                    Rectangle(
                        pos=(self.x + self.left_padding + start_i * self.char_width, self.y),
                        size=(count * self.char_width, self.height)
                    )
                except Exception:
                    pass

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
                # Using xterm-256color for better ncurses support.
                self.chan, self.session = await self.connection.create_session(
                    lambda: SSHClientSession(self),
                    term_type='xterm-256color',
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
                bytesize = int(self.ids.databits_spinner.text)
                parity = self.ids.parity_spinner.text
                stopbits = float(self.ids.stopbits_spinner.text)

                self.transport, self.protocol = await self.app.platform_utils.create_serial_connection(
                    asyncio.get_event_loop(),
                    lambda: SerialProtocol(self),
                    serial_port,
                    baudrate=baudrate,
                    bytesize=bytesize,
                    parity=parity,
                    stopbits=stopbits
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

    def _get_color_hex(self, color, is_bg=False):
        """Resolves a pyte color to a hex string."""
        if color == 'default':
            return '#000000' if is_bg else '#e5e5e5'

        if color in COLOR_MAP:
            return COLOR_MAP[color]

        # Check for 256-color hex from pyte
        if isinstance(color, str) and len(color) == 6 and all(c in '0123456789abcdefABCDEF' for c in color):
            return '#' + color

        return '#000000' if is_bg else '#d3d7cf'

    def get_line_markup(self, y):
        line_str = ""
        current_fg = None
        current_bold = False
        current_underscore = False

        row = self.pyte_screen.buffer[y]

        for x in range(self.pyte_screen.columns):
            char = row[x]

            fg = char.fg
            bg = char.bg
            bold = char.bold
            underscore = char.underscore

            if char.reverse:
                # Swap foreground and background for reverse video
                fg, bg = bg, fg

            # Note: Kivy's standard Label does not support a [background] tag in markup.
            # We skip background colors for now to avoid displaying literal tags.
            # We still track style changes for fg, bold, and underscore.
            style_changed = (fg != current_fg or bold != current_bold or
                             underscore != current_underscore)

            if style_changed:
                # Close previous tags in reverse order of opening
                if current_underscore: line_str += "[/u]"
                if current_bold: line_str += "[/b]"
                if current_fg is not None and current_fg != 'default': line_str += "[/color]"

                # Open new tags
                current_fg = fg
                current_bold = bold
                current_underscore = underscore

                if current_fg != 'default':
                    line_str += f"[color={self._get_color_hex(current_fg)}]"
                if current_bold:
                    line_str += "[b]"
                if current_underscore:
                    line_str += "[u]"

            # Escape markup characters
            c = char.data
            if c == '[': c = '[['
            elif c == ']': c = ']]'
            line_str += c

        # Close tags at end of line
        if current_underscore: line_str += "[/u]"
        if current_bold: line_str += "[/b]"
        if current_fg is not None and current_fg != 'default': line_str += "[/color]"

        return line_str

    def update_ui(self, dt):
        if not self.pyte_screen.dirty and not self.pyte_screen.any_changes:
            return

        self.pyte_screen.any_changes = False
        self.pyte_screen.dirty.clear()

        new_data = []
        cursor_x = self.pyte_screen.cursor.x
        cursor_y = self.pyte_screen.cursor.y

        for y in range(self.pyte_screen.lines):
            row_cursor_x = cursor_x if y == cursor_y else -1
            row = self.pyte_screen.buffer[y]
            bg_data = [self._get_color_hex(row[x].bg, is_bg=True) for x in range(self.columns)]
            new_data.append({
                'text': self.get_line_markup(y),
                'cursor_x': row_cursor_x,
                'bg_data': bg_data
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

        # DECCKM (Cursor Keys Mode) is private mode 1.
        # In pyte, private modes are stored shifted by 5: 1 << 5 = 32.
        application_mode = 32 in self.pyte_screen.mode

        # Mapping for some keys
        # Format: key_code: normal_sequence or (normal_sequence, app_mode_sequence)
        key_map = {
            273: ('\x1b[A', '\x1bOA'), # Up
            274: ('\x1b[B', '\x1bOB'), # Down
            275: ('\x1b[C', '\x1bOC'), # Right
            276: ('\x1b[D', '\x1bOD'), # Left
            13: '\r',      # Enter
            8: '\x7f',     # Backspace
            9: '\t',       # Tab
            27: '\x1b',    # Escape
            280: '\x1b[5~', # PageUp
            281: '\x1b[6~', # PageDown
            278: '\x1b[H',  # Home
            279: '\x1b[F',  # End
            277: '\x1b[2~', # Insert
            127: '\x1b[3~', # Delete
            282: '\x1bOP',  # F1
            283: '\x1bOQ',  # F2
            284: '\x1bOR',  # F3
            285: '\x1bOS',  # F4
            286: '\x1b[15~', # F5
            287: '\x1b[17~', # F6
            288: '\x1b[18~', # F7
            289: '\x1b[19~', # F8
            290: '\x1b[20~', # F9
            291: '\x1b[21~', # F10
            292: '\x1b[23~', # F11
            293: '\x1b[24~', # F12
        }

        if 'ctrl' in modifier:
            if codepoint:
                # Basic Ctrl+Key support (A=1, B=2, ...)
                val = ord(codepoint.lower()) - ord('a') + 1
                if 1 <= val <= 26:
                    self._send_to_connection(chr(val))
                    return True
            # Note: Removed explicit key == 99 (Ctrl+C) as it's covered by codepoint logic
            # on most platforms.

        if key in key_map:
            seq = key_map[key]
            if isinstance(seq, tuple):
                self._send_to_connection(seq[1] if application_mode else seq[0])
            else:
                self._send_to_connection(seq)
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

    def _on_save_session(self, path, selection):
        """
        Callback from the save dialog to write the terminal content to the chosen file.
        """
        if not selection:
            self.app.ui_manager.dismiss_popup()
            return

        filepath = os.path.join(path, selection[0])
        try:
            # Get the current display content from pyte screen
            # Strip trailing spaces from each line for a cleaner file
            content = "\n".join(line.rstrip() for line in self.pyte_screen.display)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            self.log(f"Session saved to {filepath}")
        except Exception as e:
            self.log(f"Failed to save session: {e}", LogLevel.ERROR)
        self.app.ui_manager.dismiss_popup()

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
