from kivy.uix.screenmanager import Screen
from kivy.properties import DictProperty, NumericProperty
from kivy.core.window import Window
from kivy.uix.label import Label
from kivy.factory import Factory

class JoystickTesterScreen(Screen):
    joysticks = DictProperty({})  # stick_id -> { 'axes': [], 'buttons': [], 'hats': [], 'name': str }
    selected_stick_id = NumericProperty(-1)

    def on_enter(self, *args):
        # Bind joystick events when entering the screen
        Window.bind(on_joy_axis=self._on_joy_axis)
        Window.bind(on_joy_button_down=self._on_joy_button_down)
        Window.bind(on_joy_button_up=self._on_joy_button_up)
        Window.bind(on_joy_hat=self._on_joy_hat)
        self.update_display()

    def on_leave(self, *args):
        # Unbind joystick events when leaving the screen
        Window.unbind(on_joy_axis=self._on_joy_axis)
        Window.unbind(on_joy_button_down=self._on_joy_button_down)
        Window.unbind(on_joy_button_up=self._on_joy_button_up)
        Window.unbind(on_joy_hat=self._on_joy_hat)

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
        self._ensure_joystick(stick_id)
        normalized_value = value / 32767.0

        if axis_id >= len(self.joysticks[stick_id]['axes']):
             self.joysticks[stick_id]['axes'].extend([0.0] * (axis_id - len(self.joysticks[stick_id]['axes']) + 1))

        self.joysticks[stick_id]['axes'][axis_id] = normalized_value
        self.joysticks = dict(self.joysticks)

    def _on_joy_button_down(self, window, stick_id, button_id):
        self._ensure_joystick(stick_id)
        if button_id >= len(self.joysticks[stick_id]['buttons']):
            self.joysticks[stick_id]['buttons'].extend([False] * (button_id - len(self.joysticks[stick_id]['buttons']) + 1))
        self.joysticks[stick_id]['buttons'][button_id] = True
        self.joysticks = dict(self.joysticks)

    def _on_joy_button_up(self, window, stick_id, button_id):
        self._ensure_joystick(stick_id)
        if button_id >= len(self.joysticks[stick_id]['buttons']):
            self.joysticks[stick_id]['buttons'].extend([False] * (button_id - len(self.joysticks[stick_id]['buttons']) + 1))
        self.joysticks[stick_id]['buttons'][button_id] = False
        self.joysticks = dict(self.joysticks)

    def _on_joy_hat(self, window, stick_id, hat_id, value):
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
                indicator = Factory.AxisIndicator()
                indicator.axis_name = f"Axis {i}"
                axes_layout.add_widget(indicator)

        # children are in reverse order of addition
        for i, val in enumerate(data['axes']):
            axes_layout.children[len(data['axes']) - 1 - i].axis_value = val

        # Buttons
        buttons_layout = self.ids.buttons_container
        if len(buttons_layout.children) != len(data['buttons']):
            buttons_layout.clear_widgets()
            for i in range(len(data['buttons'])):
                indicator = Factory.ButtonIndicator()
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
