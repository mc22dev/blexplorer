import pytest
import time
from unittest.mock import MagicMock, patch
from blescanner.__main__ import BLEScannerApp
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

@pytest.fixture
def app():
    # Mocking necessary parts of the App for initialization
    with patch('blescanner.__main__.ConfigManager'), \
         patch('blescanner.__main__.UIManager'), \
         patch('blescanner.__main__.DeviceManager'), \
         patch('blescanner.__main__.BLEManager'), \
         patch('blescanner.__main__.Builder'):
        app = BLEScannerApp()
        # Initialize internal state normally set during build/on_start
        app.last_discovery_times = {}
        app.wireshark_data = []
        app.device_manager = MagicMock()
        app.root = MagicMock()
        return app

def create_adv_data(rssi):
    return AdvertisementData(
        local_name='Test Device',
        manufacturer_data={},
        service_data={},
        service_uuids=[],
        rssi=rssi,
        tx_power=0,
        platform_data=()
    )

def test_wireshark_delay_calculation(app):
    device = BLEDevice("AA:BB:CC:DD:EE:FF", "Test", details={}, rssi=-60)
    adv = create_adv_data(-60)

    # First discovery
    with patch('time.monotonic', return_value=100.0), \
         patch('blescanner.__main__.Clock.schedule_once', side_effect=lambda f, *a, **k: f(0)):
        app._on_device_discovered(device, adv)

    # Verify that log entry is added to wireshark_data list directly
    assert len(app.wireshark_data) == 1
    assert app.wireshark_data[0]['delay'] == ""
    assert app.last_discovery_times[device.address] == 100.0

    # Second discovery 500ms later
    with patch('time.monotonic', return_value=100.5), \
         patch('blescanner.__main__.Clock.schedule_once', side_effect=lambda f, *a, **k: f(0)):
        app._on_device_discovered(device, adv)

    # Manually trigger the log execution as Clock.schedule_once might be tricky in this setup
    # Wait, side_effect=lambda f, *a, **k: f(0) should have handled it.

    assert len(app.wireshark_data) == 2
    assert app.wireshark_data[1]['delay'] == "500.0ms"
    assert app.last_discovery_times[device.address] == 100.5

def test_wireshark_delay_reset_on_clear(app):
    device = BLEDevice("AA:BB:CC:DD:EE:FF", "Test", details={}, rssi=-60)
    adv = create_adv_data(-60)

    app.last_discovery_times[device.address] = 100.0
    app.clear_wireshark_log()

    assert app.last_discovery_times == {}

    with patch('time.monotonic', return_value=101.0), \
         patch('blescanner.__main__.Clock.schedule_once', side_effect=lambda f, *a, **k: f(0)):
        app._on_device_discovered(device, adv)

    assert app.wireshark_data[0]['delay'] == ""

def test_wireshark_log_entry_has_delay_property():
    from blescanner.ui.wireshark_log_entry import WiresharkLogEntry
    # Mocking app and theme to avoid BuilderException during widget init
    mock_app = MagicMock()
    mock_app.theme.secondary = [0, 0, 0, 1]
    with patch('kivy.app.App.get_running_app', return_value=mock_app):
        entry = WiresharkLogEntry()
        assert hasattr(entry, 'delay')
        assert entry.delay == ""
