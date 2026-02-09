import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from blescanner.platform.default import DefaultPlatformUtils
import platform

@pytest.mark.asyncio
async def test_windows_wifi_scan_parsing():
    utils = DefaultPlatformUtils()

    mock_output = (
        "Interface name : Wi-Fi \n"
        "There are 2 networks currently visible. \n"
        "\n"
        "SSID 1 : MyWiFi\n"
        "    Network type            : Infrastructure\n"
        "    Authentication          : WPA2-Personal\n"
        "    Encryption              : CCMP \n"
        "    BSSID 1                 : 00:11:22:33:44:55\n"
        "         Signal             : 80% \n"
        "         Radio type         : 802.11n\n"
        "         Channel            : 6 \n"
        "\n"
        "SSID 2 : Guest\n"
        "    Network type            : Infrastructure\n"
        "    Authentication          : Open\n"
        "    Encryption              : None \n"
        "    BSSID 1                 : AA:BB:CC:DD:EE:FF\n"
        "         Signal             : 40% \n"
        "         Radio type         : 802.11ac\n"
        "         Channel            : 36 \n"
    )

    with patch('platform.system', return_value="Windows"):
        # subprocess.check_output is called inside run_in_executor
        # For simplicity, we can mock the executor or just subprocess.check_output if we use a synchronous mock executor

        loop = asyncio.get_running_loop()
        mock_future = asyncio.Future()
        mock_future.set_result(mock_output)
        with patch.object(loop, 'run_in_executor', return_value=mock_future):
            aps = await utils.scan_wifi()

            assert len(aps) == 2

            assert aps[0].ssid == "MyWiFi"
            assert aps[0].bssid == "00:11:22:33:44:55"
            assert aps[0].rssi == -60 # (80/2) - 100
            assert aps[0].channel == 6
            assert aps[0].frequency == 2437

            assert aps[1].ssid == "Guest"
            assert aps[1].bssid == "aa:bb:cc:dd:ee:ff"
            assert aps[1].rssi == -80 # (40/2) - 100
            assert aps[1].channel == 36
            assert aps[1].frequency == 5180
