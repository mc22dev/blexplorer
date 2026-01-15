import unittest
from unittest.mock import MagicMock, Mock
from kivy.uix.boxlayout import BoxLayout
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
from device_manager import DeviceManager
from models import DeviceScanStats

class TestDeviceManager(unittest.TestCase):
    def setUp(self):
        self.app_callback = MagicMock()
        self.ui_container = Mock(spec=BoxLayout)
        self.config_manager = MagicMock()
        self.config_manager.get_device_name.return_value = "Test Device"
        self.theme_manager = MagicMock()
        self.theme_manager.primary = [1, 1, 1, 1]
        self.theme_manager.secondary = [0, 0, 0, 0]
        self.device_manager = DeviceManager(self.app_callback, self.ui_container, self.config_manager, self.theme_manager)

    def test_clear(self):
        self.device_manager.clear()
        self.ui_container.clear_widgets.assert_called_once()
        self.assertEqual(len(self.device_manager.device_frames), 0)

    def test_add_discovered_device(self):
        device = BLEDevice("address", "name", details={})
        adv_data = AdvertisementData(local_name="", manufacturer_data={}, service_data={}, service_uuids=[], tx_power=0, rssi=-60, platform_data=())
        self.device_manager.add_discovered_device(device, adv_data)
        self.assertEqual(len(self.device_manager.discovered_devices_batch), 1)

    def test_process_device_batch(self):
        device = BLEDevice("address", "name", details={})
        adv_data = AdvertisementData(local_name="", manufacturer_data={}, service_data={}, service_uuids=[], tx_power=0, rssi=-60, platform_data=())
        self.device_manager.add_discovered_device(device, adv_data)
        self.device_manager.process_device_batch()
        self.assertEqual(len(self.device_manager.device_frames), 1)
        self.app_callback.update_graph_data.assert_called_once()

    def test_filter_devices(self):
        # This test requires a more complex setup to mock Kivy widgets and properties
        device1 = BLEDevice("11:22:33:44:55:66", "Device A", details={})
        adv_data1 = AdvertisementData(local_name="Device A", manufacturer_data={}, service_data={}, service_uuids=[], tx_power=0, rssi=-60, platform_data=())
        self.device_manager.add_discovered_device(device1, adv_data1)

        device2 = BLEDevice("AA:BB:CC:DD:EE:FF", "Device B", details={})
        adv_data2 = AdvertisementData(local_name="Device B", manufacturer_data={}, service_data={}, service_uuids=[], tx_power=0, rssi=-70, platform_data=())
        self.device_manager.add_discovered_device(device2, adv_data2)

        self.device_manager.process_device_batch()

        # Mock the parent attribute for the frames
        for frame in self.device_manager.device_frames.values():
            frame.parent = self.ui_container

        # Reset mock before testing filtering
        self.ui_container.reset_mock()

        # Filter for "Device A"
        self.device_manager.filter_devices("Device A")
        self.ui_container.add_widget.assert_not_called()
        self.ui_container.remove_widget.assert_called_once()

        # Reset mocks and filter for "Device B"
        self.ui_container.reset_mock()
        for frame in self.device_manager.device_frames.values():
            frame.parent = None
        self.device_manager.device_frames["11:22:33:44:55:66"].parent = self.ui_container

        self.device_manager.filter_devices("Device B")
        self.ui_container.add_widget.assert_called_once()
        self.ui_container.remove_widget.assert_called_once()

if __name__ == '__main__':
    unittest.main()
