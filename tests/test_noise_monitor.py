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
    screen.num_bars = 10
    # Mock data: some constant values
    # RMS of constant C is C.
    data = np.full(1024, 0.05, dtype=np.float32)
    screen._buffer = data
    screen._new_data = True

    # target_level = 0.05 * (10 * 10) * 1.0 = 5.0
    # noise_level starts at 0. EMA: 0 * 0.5 + 5.0 * 0.5 = 2.5
    screen.update_noise_level(0)
    assert screen.noise_level == pytest.approx(2.5)

def test_noise_alert_threshold():
    screen = NoiseMonitorScreen()
    screen.num_bars = 10
    screen.alert_sound = MagicMock()
    screen._last_alert_time = 0 # Ensure no cooldown

    # level 7 should not trigger anymore
    screen.noise_level = 7.0
    # Target level below threshold: 0.08 * 100 = 8.0. EMA: 7.0*0.5 + 8.0*0.5 = 7.5
    data = np.full(1024, 0.08, dtype=np.float32)
    screen._buffer = data
    screen._new_data = True
    screen.update_noise_level(0)
    assert not screen.alert_sound.play.called

    # Reset buffer to avoid interference from previous call
    screen._rms_buffer.clear()

    # level 10 should trigger (threshold is num_bars - 0.5 = 9.5)
    screen.noise_level = 9.5
    data = np.full(1024, 0.11, dtype=np.float32) # 0.11 * 100 = 11.0 -> clipped to 10.0
    screen._buffer = data
    screen._new_data = True
    screen.update_noise_level(0)
    # Target level: 0.11 * 100 = 11.0 -> EMA uses min(10.0, 11.0) = 10.0
    # EMA: 9.5*0.5 + 10.0*0.5 = 9.75 >= 9.5
    assert screen.alert_sound.play.called

def test_averaging_logic():
    screen = NoiseMonitorScreen()
    screen.num_bars = 10
    screen.average_time = 100 # 2 samples

    # First sample: 0.1
    data = np.full(1024, 0.1, dtype=np.float32)
    screen._buffer = data
    screen._new_data = True
    screen.update_noise_level(0)
    # avg_rms = 0.1. target_level = 10.0. noise_level = 0.5 * 0 + 0.5 * 10.0 = 5.0
    assert screen.noise_level == pytest.approx(5.0)

    # Second sample: 0.2
    data = np.full(1024, 0.2, dtype=np.float32)
    screen._buffer = data
    screen._new_data = True
    screen.update_noise_level(0)
    # avg_rms = (0.1 + 0.2) / 2 = 0.15. target_level = 15.0 -> clipped to 10.0
    # noise_level = 0.5 * 5.0 + 0.5 * 10.0 = 7.5
    assert screen.noise_level == pytest.approx(7.5)

    # Third sample: 0.3. Window is 2 samples, so window is [0.2, 0.3]
    data = np.full(1024, 0.3, dtype=np.float32)
    screen._buffer = data
    screen._new_data = True
    screen.update_noise_level(0)
    # avg_rms = (0.2 + 0.3) / 2 = 0.25. target_level = 25.0 -> clipped to 10.0
    # noise_level = 0.5 * 7.5 + 0.5 * 10.0 = 8.75
    assert screen.noise_level == pytest.approx(8.75)

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
    screen.alarm_cooldown = 10

    # First alert
    screen.trigger_alert()
    assert screen.alert_sound.play.call_count == 1

    # Second alert immediately after
    screen.trigger_alert()
    assert screen.alert_sound.play.call_count == 1 # Still 1 due to cooldown (10s)
