
import asyncio
from typing import List, Callable, Tuple

import serial_asyncio

from .base import PlatformUtilsBase, BondedDevice, SerialPort, WifiAccessPoint


class DefaultPlatformUtils(PlatformUtilsBase):
    """
    Default platform utility implementation for unsupported platforms.
    """

    def check_android_permissions(self) -> bool:
        """
        No-op on this platform.
        """
        return True

    def request_android_permissions(self, callback: Callable):
        """
        No-op on this platform.
        """
        pass

    def is_bluetooth_enabled(self) -> bool:
        """
        No-op on this platform, assuming enabled.
        """
        return True

    def is_location_enabled(self) -> bool:
        """
        No-op on this platform, assuming enabled.
        """
        return True

    async def get_bonded_devices(self) -> List[BondedDevice]:
        """
        No-op on this platform.
        """
        return []

    def list_serial_ports(self) -> List[SerialPort]:
        """
        Lists available serial ports using pyserial.
        """
        import serial.tools.list_ports
        ports = serial.tools.list_ports.comports()
        return [SerialPort(device=p.device, description=p.description) for p in ports]

    async def create_serial_connection(
        self,
        loop: asyncio.AbstractEventLoop,
        protocol_factory: Callable[[], asyncio.Protocol],
        url: str,
        **kwargs
    ) -> Tuple[asyncio.Transport, asyncio.Protocol]:
        """
        Creates a serial connection using pyserial-asyncio.
        """
        return await serial_asyncio.create_serial_connection(
            loop, protocol_factory, url, **kwargs
        )

    def get_local_ip_and_mask(self) -> Tuple[str, str]:
        """
        Retrieves the local IP address and netmask using psutil.
        """
        import psutil
        import socket
        for interface, addrs in psutil.net_if_addrs().items():
            for addr in addrs:
                if addr.family == socket.AF_INET and not addr.address.startswith("127."):
                    return addr.address, addr.netmask
        return None, None

    def get_arp_table(self) -> dict:
        """
        Retrieves the ARP table by running the 'arp -a' command.
        """
        import subprocess
        import re
        import platform

        arp_table = {}
        try:
            if platform.system() == "Windows":
                output = subprocess.check_output(["arp", "-a"]).decode("ascii", errors="ignore")
                # Format: 192.168.1.1         00-11-22-33-44-55     dynamic
                for line in output.splitlines():
                    match = re.search(r"(\d+\.\d+\.\d+\.\d+)\s+([0-9a-fA-F:-]{17})", line)
                    if match:
                        ip, mac = match.groups()
                        arp_table[ip] = mac.replace("-", ":").lower()
            else:
                # Assuming generic Unix if not specifically handled
                output = subprocess.check_output(["arp", "-n"]).decode("ascii", errors="ignore")
                for line in output.splitlines():
                    match = re.search(r"(\d+\.\d+\.\d+\.\d+)\s+.*?\s+([0-9a-fA-F:]{17})", line)
                    if match:
                        ip, mac = match.groups()
                        arp_table[ip] = mac.lower()
        except Exception:
            pass
        return arp_table

    async def scan_wifi(self) -> List[WifiAccessPoint]:
        """
        Scans for available Wi-Fi access points on Windows using netsh.
        """
        import subprocess
        import re
        import platform

        aps = []
        if platform.system() == "Windows":
            try:
                cmd = ["netsh", "wlan", "show", "networks", "mode=bssid"]
                # We use run_in_executor because netsh is blocking and doesn't have an easy async way here
                loop = asyncio.get_running_loop()
                output = await loop.run_in_executor(None, lambda: subprocess.check_output(cmd).decode("ascii", errors="ignore"))

                current_ssid = ""
                current_security = ""

                # Parse netsh output
                # SSID 1 : MyWiFi
                #     Network type            : Infrastructure
                #     Authentication          : WPA2-Personal
                #     Encryption              : CCMP
                #     BSSID 1                 : 00:11:22:33:44:55
                #          Signal             : 80%
                #          Radio type         : 802.11n
                #          Channel            : 6

                # Split by "SSID " at the beginning of a line to avoid matching "BSSID"
                sections = re.split(r"^\s*SSID\s+\d+\s*:\s*", output, flags=re.MULTILINE)
                # The first section is the header before the first SSID
                for section in sections[1:]:
                    lines = section.splitlines()
                    if not lines: continue

                    ssid = lines[0].strip()
                    security = ""
                    for line in lines:
                        if "Authentication" in line:
                            security = line.split(":", 1)[1].strip()
                            break

                    # Find BSSIDs in this SSID section
                    bssids_data = re.split(r"^\s*BSSID\s+\d+\s*:\s*", section, flags=re.MULTILINE)
                    for bssid_section in bssids_data[1:]:
                        b_lines = bssid_section.splitlines()
                        if not b_lines: continue

                        bssid_match = re.search(r"([0-9a-fA-F:]{17})", b_lines[0])
                        if not bssid_match: continue
                        bssid = bssid_match.group(1)

                        rssi = -100
                        channel = 0
                        for bl in b_lines:
                            if "Signal" in bl:
                                try:
                                    sig_pct = int(bl.split(":", 1)[1].strip().replace("%", ""))
                                    rssi = (sig_pct / 2) - 100
                                except:
                                    pass
                            if "Channel" in bl:
                                try:
                                    channel = int(bl.split(":", 1)[1].strip())
                                except:
                                    pass

                        # Derive frequency from channel
                        frequency = 0
                        if 1 <= channel <= 14:
                            frequency = 2407 + (channel * 5)
                            if channel == 14: frequency = 2484
                        elif channel >= 36:
                            frequency = 5000 + (channel * 5)

                        aps.append(WifiAccessPoint(
                            ssid=ssid,
                            bssid=bssid.lower(),
                            rssi=int(rssi),
                            channel=channel,
                            frequency=frequency,
                            security=security
                        ))
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Error scanning Wi-Fi on Windows: {e}")
        return aps
