import pytest
from unittest.mock import MagicMock, Mock, patch, AsyncMock
from kivy.uix.boxlayout import BoxLayout
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
from device_manager import DeviceManager
from models import DeviceScanStats

@pytest.fixture
def device_manager():
    ui_container = Mock(spec=BoxLayout)
    config_manager = MagicMock()
    config_manager.get_device_name.return_value = "Test Device"
    theme_manager = MagicMock()
    theme_manager.primary = [1, 1, 1, 1]
    theme_manager.secondary = [0, 0, 0, 0]
    log_callback = MagicMock()
    on_graph_selection_change_callback = MagicMock()
    connect_callback = MagicMock()
    auto_connect_callback = MagicMock()
    update_graph_data_callback = MagicMock()
    get_graph_device_color_callback = MagicMock(return_value=(1, 1, 1, 1))
    clear_graph_callback = MagicMock()

    manager = DeviceManager(
        ui_container=ui_container,
        config_manager=config_manager,
        theme_manager=theme_manager,
        log_callback=log_callback,
        on_graph_selection_change_callback=on_graph_selection_change_callback,
        connect_callback=connect_callback,
        auto_connect_callback=auto_connect_callback,
        update_graph_data_callback=update_graph_data_callback,
        get_graph_device_color_callback=get_graph_device_color_callback,
        clear_graph_callback=clear_graph_callback,
    )
    # Attach mocks to the manager instance so they can be accessed in tests
    manager.ui_container = ui_container
    manager.update_graph_data_callback = update_graph_data_callback
    return manager

@pytest.mark.asyncio
async def test_clear(device_manager):
    with patch('platform_utils.PlatformUtils.get_bonded_devices', new_callable=AsyncMock) as mock_get_bonded:
        mock_get_bonded.return_value = []
        await device_manager.clear()
        device_manager.ui_container.clear_widgets.assert_called_once()
        assert len(device_manager.device_frames) == 0

def test_add_discovered_device(device_manager):
    device = BLEDevice("address", "name", details={})
    adv_data = AdvertisementData(local_name="", manufacturer_data={}, service_data={}, service_uuids=[], tx_power=0, rssi=-60, platform_data=())
    device_manager.add_discovered_device(device, adv_data)
    assert len(device_manager.discovered_devices_batch) == 1

def test_process_device_batch(device_manager):
    device1 = BLEDevice("address1", "name1", details={})
    adv_data1 = AdvertisementData(local_name="", manufacturer_data={}, service_data={}, service_uuids=[], tx_power=0, rssi=-60, platform_data=())
    device2 = BLEDevice("address2", "name2", details={})
    adv_data2 = AdvertisementData(local_name="", manufacturer_data={}, service_data={}, service_uuids=[], tx_power=0, rssi=-70, platform_data=())

    device_manager.add_discovered_device(device1, adv_data1)
    device_manager.add_discovered_device(device2, adv_data2)

    device_manager.process_device_batch()

    assert len(device_manager.device_frames) == 2
    assert device_manager.ui_container.add_widget.call_count == 2
    device_manager.update_graph_data_callback.assert_called_once()

def test_filter_devices(device_manager):
    # This test requires a more complex setup to mock Kivy widgets and properties
    device1 = BLEDevice("11:22:33:44:55:66", "Device A", details={})
    adv_data1 = AdvertisementData(local_name="Device A", manufacturer_data={}, service_data={}, service_uuids=[], tx_power=0, rssi=-60, platform_data=())
    device_manager.add_discovered_device(device1, adv_data1)

    device2 = BLEDevice("AA:BB:CC:DD:EE:FF", "Device B", details={})
    adv_data2 = AdvertisementData(local_name="Device B", manufacturer_data={}, service_data={}, service_uuids=[], tx_power=0, rssi=-70, platform_data=())
    device_manager.add_discovered_device(device2, adv_data2)

    device_manager.process_device_batch()

    # Mock the parent attribute for the frames
    for frame in device_manager.device_frames.values():
        frame.parent = device_manager.ui_container

    # Reset mock before testing filtering
    device_manager.ui_container.reset_mock()

    # Filter for "Device A"
    device_manager.filter_devices("Device A")
    device_manager.ui_container.add_widget.assert_not_called()
    device_manager.ui_container.remove_widget.assert_called_once()

    # Reset mocks and filter for "Device B"
    device_manager.ui_container.reset_mock()
    for frame in device_manager.device_frames.values():
        frame.parent = None
    device_manager.device_frames["11:22:33:44:55:66"].parent = device_manager.ui_container

    device_manager.filter_devices("Device B")
    device_manager.ui_container.add_widget.assert_called_once()
    device_manager.ui_container.remove_widget.assert_called_once()
