import pytest
from unittest.mock import MagicMock
from blescanner.tools.joystick_tester.joystick_tester import JoystickTesterScreen
from kivy.core.window import Window

@pytest.fixture
def joystick_tester():
    screen = JoystickTesterScreen(name='joystick_tester')
    # Mock ids because they are usually populated by KV
    screen.ids = MagicMock()
    screen.ids.axes_container = MagicMock()
    screen.ids.buttons_container = MagicMock()
    screen.ids.hats_container = MagicMock()
    screen.ids.visualizer = MagicMock()
    return screen

def test_joystick_tester_initial_state(joystick_tester):
    assert joystick_tester.joysticks == {}
    assert joystick_tester.selected_stick_id == -1

def test_joystick_axis_event(joystick_tester):
    joystick_tester.on_enter()
    # Simulate axis event
    joystick_tester._on_joy_axis(Window, 0, 1, 16383)
    assert 0 in joystick_tester.joysticks
    assert joystick_tester.selected_stick_id == 0
    # 16383 / 32767.0 approx 0.5
    assert abs(joystick_tester.joysticks[0]['axes'][1] - 0.5) < 0.01

def test_joystick_button_event(joystick_tester):
    joystick_tester.on_enter()
    joystick_tester._on_joy_button_down(Window, 0, 5)
    assert joystick_tester.joysticks[0]['buttons'][5] is True
    joystick_tester._on_joy_button_up(Window, 0, 5)
    assert joystick_tester.joysticks[0]['buttons'][5] is False

def test_joystick_hat_event(joystick_tester):
    joystick_tester.on_enter()
    joystick_tester._on_joy_hat(Window, 0, 0, (1, -1))
    assert joystick_tester.joysticks[0]['hats'][0] == (1, -1)
