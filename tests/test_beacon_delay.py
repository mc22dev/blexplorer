import pytest
import time
from unittest.mock import MagicMock, Mock
from blescanner.models import DeviceScanStats
from blescanner.core.device_manager import DeviceManager
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

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

def test_device_scan_stats_with_explicit_timestamp():
    stats = DeviceScanStats()
    adv1 = create_adv_data(-50)
    t1 = 1000.0
    stats.update(adv1, timestamp=t1)

    adv2 = create_adv_data(-60)
    t2 = 1000.5 # 500ms later
    stats.update(adv2, timestamp=t2)

    assert stats.last_period == 500.0
    assert stats.avg_period == 500.0
    assert stats.timestamps == [1000.0, 1000.5]

def test_device_manager_timestamp_propagation():
    ui_container = Mock()
    config_manager = MagicMock()
    config_manager.get_device_name.return_value = ""
    theme_manager = MagicMock()
    theme_manager.primary = [1, 1, 1, 1]
    theme_manager.secondary = [0, 0, 0, 1]
    manager = DeviceManager(
        ui_container=ui_container,
        config_manager=config_manager,
        theme_manager=theme_manager,
        log_callback=MagicMock(),
        on_graph_selection_change_callback=MagicMock(),
        connect_callback=MagicMock(),
        auto_connect_callback=MagicMock(),
        update_graph_data_callback=MagicMock(),
        get_graph_device_color_callback=MagicMock(return_value=(1,1,1,1)),
        clear_graph_callback=MagicMock()
    )

    device = BLEDevice("address", "name", details={})
    adv_data = create_adv_data(-60)
    t1 = 2000.0

    manager.add_discovered_device(device, adv_data, timestamp=t1)
    assert manager.discovered_devices_batch == [(device, adv_data, t1)]

    manager.process_device_batch()

    assert device.address in manager.scan_stats
    stats = manager.scan_stats[device.address]
    assert stats.timestamps == [2000.0]
