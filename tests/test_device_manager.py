import unittest
from unittest.mock import MagicMock, Mock
from kivy.uix.boxlayout import BoxLayout
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
from src.device_manager import DeviceManager
from src.models import DeviceScanStats

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
        pass

if __name__ == '__main__':
    unittest.main()
