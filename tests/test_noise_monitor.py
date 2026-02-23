import pytest
from blescanner.tools.noise_monitor.noise_monitor import NoiseMonitorScreen, NoiseBarGraph
from unittest.mock import MagicMock
import numpy as np

def test_noise_monitor_instantiation():
    screen = NoiseMonitorScreen()
    assert not screen.is_running
    assert screen.noise_level == 0
    assert screen.status_text == "Stopped"

def test_noise_bar_graph_instantiation():
    graph = NoiseBarGraph()
    assert graph.level == 0

def test_noise_calculation():
    screen = NoiseMonitorScreen()
    # Mock data: some constant values
    # RMS of constant C is C.
    data = np.full(1024, 0.05, dtype=np.float32)
    screen._buffer = data
    screen._new_data = True

    # target_level = 0.05 * 90 * 1.0 = 4.5
    # noise_level starts at 0. EMA: 0 * 0.5 + 4.5 * 0.5 = 2.25
    screen.update_noise_level(0)
    assert screen.noise_level == pytest.approx(2.25)

def test_alert_trigger():
    screen = NoiseMonitorScreen()
    screen.alert_sound = MagicMock()
    # Set last alert time to far in the past to avoid cooldown
    screen._last_alert_time = 0

    screen.trigger_alert()
    assert screen.alert_sound.play.called

def test_alert_cooldown():
    from kivy.clock import Clock
    screen = NoiseMonitorScreen()
    screen.alert_sound = MagicMock()

    # First alert
    screen.trigger_alert()
    assert screen.alert_sound.play.call_count == 1

    # Second alert immediately after
    screen.trigger_alert()
    assert screen.alert_sound.play.call_count == 1 # Still 1 due to cooldown
