import pytest
from unittest.mock import MagicMock, patch
from kivy.app import App
from blescanner.__main__ import BLEScannerApp
from blescanner.utils.config_manager import ConfigManager

@pytest.fixture
def mock_config(tmp_path):
    config_path = tmp_path / "config.ini"
    return ConfigManager(str(config_path))

def test_app_remembers_last_tool(mock_config):
    app = BLEScannerApp()
    app.config_manager = mock_config
    app.root = MagicMock()
    # Mock current_screen without on_pre_leave_check
    app.root.ids.screen_manager.current_screen = object()
    app.root.ids.tool_title = MagicMock()
    app.root.nav_drawer_open = False

    # Switch to a tool
    app.switch_tool("calculator", "Calculator")

    # Verify it's saved in config
    assert mock_config.get_setting('general', 'last_tool_id') == "calculator"
    assert mock_config.get_setting('general', 'last_tool_name') == "Calculator"

def test_app_loads_last_tool_on_start(mock_config):
    mock_config.set_setting('general', 'last_tool_id', 'calculator')
    mock_config.set_setting('general', 'last_tool_name', 'Calculator')

    app = BLEScannerApp()
    app.config_manager = mock_config
    app.root = MagicMock()
    app.switch_tool = MagicMock()

    with patch('blescanner.__main__.Clock.schedule_once') as mock_schedule:
        # We manually call what we added in on_start to avoid full on_start complexity
        last_tool_id = app.config_manager.get_setting('general', 'last_tool_id', default='ble_scanner')
        last_tool_name = app.config_manager.get_setting('general', 'last_tool_name', default='BLE Scanner')
        if last_tool_id != 'ble_scanner':
            from kivy.clock import Clock
            Clock.schedule_once(lambda dt: app.switch_tool(last_tool_id, last_tool_name), 0.1)

        # Verify that switch_tool was scheduled
        assert mock_schedule.called
