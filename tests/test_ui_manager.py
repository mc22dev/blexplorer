import unittest
from unittest.mock import MagicMock
from blescanner.ui.ui_manager import UIManager

class TestUIManager(unittest.TestCase):
    def setUp(self):
        self.log_callback = MagicMock()
        self.discover_attributes_callback = MagicMock()
        self.read_characteristic_callback = MagicMock()
        self.reset_char_color_callback = MagicMock()
        self.ui_manager = UIManager(
            self.log_callback,
            self.discover_attributes_callback,
            self.read_characteristic_callback,
            self.reset_char_color_callback
        )
        self.ui_manager.root = MagicMock()
        # Mock the screen manager and the ble_scanner screen
        self.ble_scanner_screen_mock = MagicMock()
        self.ui_manager.root.ids.screen_manager.get_screen.return_value = self.ble_scanner_screen_mock

    def test_switch_to_device_tab(self):
        self.ui_manager.switch_to_device_tab()
        self.ble_scanner_screen_mock.ids.bottom_nav.switch_to.assert_called_once_with(
            self.ble_scanner_screen_mock.ids.device_screen_tab
        )

    def test_clear_characteristic_list(self):
        self.ui_manager.clear_characteristic_list()
        self.ble_scanner_screen_mock.ids.device_screen.ids.characteristic_list.clear_widgets.assert_called_once()

if __name__ == '__main__':
    unittest.main()
