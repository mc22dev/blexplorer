
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
