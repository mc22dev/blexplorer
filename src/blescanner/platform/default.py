
import asyncio
from typing import List, Callable, Tuple

import serial_asyncio

from .base import PlatformUtilsBase, BondedDevice, SerialPort


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
