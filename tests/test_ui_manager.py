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

    def test_switch_to_device_tab(self):
        self.ui_manager.switch_to_device_tab()
        self.ui_manager.root.ids.bottom_nav.switch_to.assert_called_once()

    def test_clear_characteristic_list(self):
        self.ui_manager.clear_characteristic_list()
        self.ui_manager.root.ids.device_screen.ids.characteristic_list.clear_widgets.assert_called_once()

if __name__ == '__main__':
    unittest.main()
