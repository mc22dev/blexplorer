import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from blescanner.platform.linux import LinuxPlatformUtils
from blescanner.platform.base import WifiAccessPoint

@pytest.mark.asyncio
async def test_linux_wifi_scan_parsing():
    utils = LinuxPlatformUtils()

    # Mock output from nmcli -t -f IN-USE,SSID,BSSID,SIGNAL,CHAN,FREQ,RATE,MODE,SECURITY device wifi list
    # nmcli -t escapes ':' with '\'
    mock_output = (
        "*:MySSID:00\\:11\\:22\\:33\\:44\\:55:80:6:2437 MHz:54 Mbit/s:Infrastructure:WPA2\n"
        " :Other SSID:AA\\:BB\\:CC\\:DD\\:EE\\:FF:50:36:5180 MHz:44 Mbit/s:Infrastructure:WPA1 WPA2\n"
    ).encode('utf-8')

    mock_process = MagicMock()
    mock_process.communicate = AsyncMock(return_value=(mock_output, b""))
    mock_process.returncode = 0

    with patch('asyncio.create_subprocess_exec', new_callable=AsyncMock) as mock_exec:
        mock_exec.return_value = mock_process
        aps = await utils.scan_wifi()

        assert len(aps) == 2

        assert aps[0].ssid == "MySSID"
        assert aps[0].bssid == "00:11:22:33:44:55"
        assert aps[0].rssi == -60 # (80/2) - 100
        assert aps[0].channel == 6
        assert aps[0].frequency == 2437
        assert "WPA2" in aps[0].security
        assert aps[0].is_connected == True
        assert aps[0].rate == "54 Mbit/s"
        assert aps[0].mode == "Infrastructure"

        assert aps[1].ssid == "Other SSID"
        assert aps[1].bssid == "aa:bb:cc:dd:ee:ff"
        assert aps[1].rssi == -75 # (50/2) - 100
        assert aps[1].channel == 36
        assert aps[1].frequency == 5180
        assert aps[1].is_connected == False
        assert aps[1].rate == "44 Mbit/s"
