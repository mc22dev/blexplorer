from kivy.uix.screenmanager import Screen
from kivy.properties import DictProperty, NumericProperty, StringProperty, BooleanProperty
from kivy.core.window import Window
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.factory import Factory
from kivy.logger import Logger
import ctypes

class AxisIndicator(BoxLayout):
    axis_name = StringProperty("Axis")
    axis_value = NumericProperty(0.0)

class ButtonIndicator(Label):
    button_name = StringProperty("0")
    is_down = BooleanProperty(False)

class JoystickTesterScreen(Screen):
    joysticks = DictProperty({})  # stick_id -> { 'axes': [], 'buttons': [], 'hats': [], 'name': str }
    selected_stick_id = NumericProperty(-1)

    def on_enter(self, *args):
        # Bind joystick events when entering the screen
        # Using fbind as seen in Kivy modules
        Window.fbind('on_joy_axis', self._on_joy_axis)
        Window.fbind('on_joy_button_down', self._on_joy_button_down)
        Window.fbind('on_joy_button_up', self._on_joy_button_up)
        Window.fbind('on_joy_hat', self._on_joy_hat)
        self.probe_joysticks()
        self.update_display()

    def on_leave(self, *args):
        # Unbind joystick events when leaving the screen
        Window.funbind('on_joy_axis', self._on_joy_axis)
        Window.funbind('on_joy_button_down', self._on_joy_button_down)
        Window.funbind('on_joy_button_up', self._on_joy_button_up)
        Window.funbind('on_joy_hat', self._on_joy_hat)

    def probe_joysticks(self):
        """
        Attempts to discover connected joysticks by querying SDL2 directly via ctypes.
        """
        Logger.info("JoystickTester: Probing for joysticks...")
        try:
            # Try to load SDL2
            import os
            sdl2 = None
            if os.name == 'nt':
                sdl2 = ctypes.cdll.LoadLibrary('SDL2.dll')
            elif os.name == 'posix':
                try:
                    sdl2 = ctypes.cdll.LoadLibrary('libSDL2-2.0.so.0')
                except OSError:
                    sdl2 = ctypes.cdll.LoadLibrary('libSDL2.so')

            if sdl2:
                # Initialize Joystick subsystem if not already
                sdl2.SDL_InitSubSystem(0x00000200) # SDL_INIT_JOYSTICK

                num_joysticks = sdl2.SDL_NumJoysticks()
                Logger.info(f"JoystickTester: SDL2 reports {num_joysticks} joysticks.")

                for i in range(num_joysticks):
                    self._ensure_joystick(i)

                    # Get name
                    sdl2.SDL_JoystickNameForIndex.restype = ctypes.c_char_p
                    name = sdl2.SDL_JoystickNameForIndex(i)
                    if name:
                        self.joysticks[i]['name'] = name.decode('utf-8')

                self.joysticks = dict(self.joysticks)
        except Exception as e:
            Logger.error(f"JoystickTester: Error probing joysticks: {e}")

    def _ensure_joystick(self, stick_id):
        if stick_id not in self.joysticks:
            self.joysticks[stick_id] = {
                'axes': [0.0] * 6,
                'buttons': [False] * 16,
                'hats': [(0, 0)] * 1,
                'name': f"Joystick {stick_id}"
            }
            if self.selected_stick_id == -1:
                self.selected_stick_id = stick_id
            return True
        return False

    def _on_joy_axis(self, window, stick_id, axis_id, value):
        # Logger.debug(f"JoystickTester: Axis event - stick: {stick_id}, axis: {axis_id}, value: {value}")
        self._ensure_joystick(stick_id)
        normalized_value = value / 32767.0

        if axis_id >= len(self.joysticks[stick_id]['axes']):
             self.joysticks[stick_id]['axes'].extend([0.0] * (axis_id - len(self.joysticks[stick_id]['axes']) + 1))

        self.joysticks[stick_id]['axes'][axis_id] = normalized_value
        self.joysticks = dict(self.joysticks)

    def _on_joy_button_down(self, window, stick_id, button_id):
        Logger.info(f"JoystickTester: Button DOWN - stick: {stick_id}, button: {button_id}")
        self._ensure_joystick(stick_id)
        if button_id >= len(self.joysticks[stick_id]['buttons']):
            self.joysticks[stick_id]['buttons'].extend([False] * (button_id - len(self.joysticks[stick_id]['buttons']) + 1))
        self.joysticks[stick_id]['buttons'][button_id] = True
        self.joysticks = dict(self.joysticks)

    def _on_joy_button_up(self, window, stick_id, button_id):
        Logger.info(f"JoystickTester: Button UP - stick: {stick_id}, button: {button_id}")
        self._ensure_joystick(stick_id)
        if button_id >= len(self.joysticks[stick_id]['buttons']):
            self.joysticks[stick_id]['buttons'].extend([False] * (button_id - len(self.joysticks[stick_id]['buttons']) + 1))
        self.joysticks[stick_id]['buttons'][button_id] = False
        self.joysticks = dict(self.joysticks)

    def _on_joy_hat(self, window, stick_id, hat_id, value):
        Logger.info(f"JoystickTester: Hat event - stick: {stick_id}, hat: {hat_id}, value: {value}")
        self._ensure_joystick(stick_id)
        if hat_id >= len(self.joysticks[stick_id]['hats']):
            self.joysticks[stick_id]['hats'].extend([(0, 0)] * (hat_id - len(self.joysticks[stick_id]['hats']) + 1))
        self.joysticks[stick_id]['hats'][hat_id] = value
        self.joysticks = dict(self.joysticks)

    def select_joystick(self, text):
        if text.startswith("Joystick "):
            try:
                sid = int(text.split(" ")[1])
                self.selected_stick_id = sid
            except (ValueError, IndexError):
                pass

    def update_display(self, *args):
        if self.selected_stick_id not in self.joysticks:
            return

        data = self.joysticks[self.selected_stick_id]

        # Axes
        axes_layout = self.ids.axes_container
        if len(axes_layout.children) != len(data['axes']):
            axes_layout.clear_widgets()
            for i in range(len(data['axes'])):
                indicator = AxisIndicator()
                indicator.axis_name = f"Axis {i}"
                axes_layout.add_widget(indicator)

        for i, val in enumerate(data['axes']):
            axes_layout.children[len(data['axes']) - 1 - i].axis_value = val

        # Buttons
        buttons_layout = self.ids.buttons_container
        if len(buttons_layout.children) != len(data['buttons']):
            buttons_layout.clear_widgets()
            for i in range(len(data['buttons'])):
                indicator = ButtonIndicator()
                indicator.button_name = f"{i}"
                buttons_layout.add_widget(indicator)

        for i, is_down in enumerate(data['buttons']):
            buttons_layout.children[len(data['buttons']) - 1 - i].is_down = is_down

        # Hats
        hats_layout = self.ids.hats_container
        if len(hats_layout.children) != len(data['hats']):
            hats_layout.clear_widgets()
            for i in range(len(data['hats'])):
                label = Label(text=f"Hat {i}: (0, 0)", size_hint_y=None, height="30dp", color=self.app.theme.text)
                hats_layout.add_widget(label)

        for i, val in enumerate(data['hats']):
            hats_layout.children[len(data['hats']) - 1 - i].text = f"Hat {i}: {val}"

    @property
    def app(self):
        from kivy.app import App
        return App.get_running_app()

Factory.register('AxisIndicator', cls=AxisIndicator)
Factory.register('ButtonIndicator', cls=ButtonIndicator)
