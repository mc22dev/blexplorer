import pytest
from blescanner.tools.wifi_scanner.wifi_scanner import WifiScannerScreen, WifiGraph
from blescanner.platform.base import WifiAccessPoint

def test_wifi_access_point_creation():
    ap = WifiAccessPoint(ssid="TestWiFi", bssid="00:11:22:33:44:55", rssi=-50, channel=6, frequency=2437, security="WPA2")
    assert ap.ssid == "TestWiFi"
    assert ap.bssid == "00:11:22:33:44:55"
    assert ap.rssi == -50
    assert ap.channel == 6
    assert ap.frequency == 2437
    assert ap.security == "WPA2"

def test_wifi_graph_initialization():
    graph = WifiGraph()
    assert graph.aps == []
    assert graph.min_freq == 2400
    assert graph.max_freq == 2500

def test_wifi_scanner_screen_initialization():
    screen = WifiScannerScreen()
    assert screen.is_scanning == False
    assert screen.aps == []
    assert screen.band == "2.4GHz"

def test_wifi_scanner_screen_band_switch():
    screen = WifiScannerScreen()
    # Need to mock the ids because KV is not loaded in this unit test
    wifi_graph = WifiGraph()
    screen.ids = {'wifi_graph': wifi_graph}

    screen.on_band(None, "5GHz")
    assert screen.ids.wifi_graph.min_freq == 5100
    assert screen.ids.wifi_graph.max_freq == 5900

    screen.on_band(None, "2.4GHz")
    assert screen.ids.wifi_graph.min_freq == 2400
    assert screen.ids.wifi_graph.max_freq == 2500
