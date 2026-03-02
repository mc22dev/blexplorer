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

    mock_iface_output = (
        "There is 1 interface on the system: \n"
        "    Name                   : Wi-Fi\n"
        "    Description            : Intel(R) Wi-Fi 6 AX201 160MHz\n"
        "    State                  : connected\n"
        "    BSSID                  : 00:11:22:33:44:55\n"
        "    Receive rate (Mbps)    : 866.7\n"
    )

    with patch('platform.system', return_value="Windows"):
        loop = asyncio.get_running_loop()

        # We need to return different values for different calls to run_in_executor
        def mock_run_in_executor(executor, func, *args):
            # The func is a lambda that calls subprocess.check_output
            # We can't easily check the cmd inside func without more complex mocks
            # But we know the order: show interfaces then show networks
            fut = asyncio.Future()
            if not hasattr(mock_run_in_executor, 'call_count'):
                mock_run_in_executor.call_count = 0

            if mock_run_in_executor.call_count == 0:
                fut.set_result(mock_iface_output)
            else:
                fut.set_result(mock_output)

            mock_run_in_executor.call_count += 1
            return fut

        with patch.object(loop, 'run_in_executor', side_effect=mock_run_in_executor):
            aps = await utils.scan_wifi()

            assert len(aps) == 2

            assert aps[0].ssid == "MyWiFi"
            assert aps[0].bssid == "00:11:22:33:44:55"
            assert aps[0].rssi == -60 # (80/2) - 100
            assert aps[0].channel == 6
            assert aps[0].frequency == 2437
            assert aps[0].is_connected == True
            assert aps[0].rate == "866.7 Mbps"

            assert aps[1].ssid == "Guest"
            assert aps[1].bssid == "aa:bb:cc:dd:ee:ff"
            assert aps[1].rssi == -80 # (40/2) - 100
            assert aps[1].channel == 36
            assert aps[1].frequency == 5180
            assert aps[1].is_connected == False
