import pytest
from unittest.mock import MagicMock
from blescanner.tools.ftp_server.ftp_server import FTPServerScreen

@pytest.fixture
def app_mock():
    app = MagicMock()
    app.config_manager.get_setting.side_effect = lambda section, option, default=None: {
        ('ftp_server', 'port'): '2121',
        ('ftp_server', 'user'): 'user',
        ('ftp_server', 'password'): 'password',
        ('ftp_server', 'directory'): '.',
        ('ftp_server', 'read_only'): 'False'
    }.get((section, option), default)
    return app

def test_ftp_server_screen_init(app_mock, monkeypatch):
    monkeypatch.setattr("kivy.app.App.get_running_app", lambda: app_mock)
    screen = FTPServerScreen(name='ftp_server')
    assert screen.server_status == "Stopped"
    assert not screen.is_running
    assert screen.log_data == []

def test_ftp_server_update_info(app_mock, monkeypatch):
    monkeypatch.setattr("kivy.app.App.get_running_app", lambda: app_mock)
    # Mock platform_utils.get_local_ip_and_mask
    mock_utils = MagicMock()
    mock_utils.get_local_ip_and_mask.return_value = ("192.168.1.10", "255.255.255.0")
    monkeypatch.setattr("blescanner.tools.ftp_server.ftp_server.platform_utils", mock_utils)

    screen = FTPServerScreen(name='ftp_server')
    screen.update_server_info()
    assert screen.server_address == "ftp://192.168.1.10:2121"

def test_ftp_server_log_message(app_mock, monkeypatch):
    monkeypatch.setattr("kivy.app.App.get_running_app", lambda: app_mock)
    screen = FTPServerScreen(name='ftp_server')
    screen.log_message("Test message")
    # Logs are batched now, so we need to flush them
    screen._flush_logs(0)
    assert any("Test message" in d['text'] for d in screen.log_data)

def test_ftp_server_clear_log(app_mock, monkeypatch):
    monkeypatch.setattr("kivy.app.App.get_running_app", lambda: app_mock)
    screen = FTPServerScreen(name='ftp_server')
    screen.log_data = [{'text': "Some logs"}]
    screen.clear_log()
    assert screen.log_data == []
