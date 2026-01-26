
import logging
from typing import List, Callable

import serial.tools.list_ports
from .base import PlatformUtilsBase, BondedDevice, SerialPort

logger = logging.getLogger(__name__)


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
        Default implementation for listing serial ports using pyserial.
        """
        try:
            ports = serial.tools.list_ports.comports()
            return [SerialPort(device=port.device, description=port.description) for port in ports]
        except Exception as e:
            # Log the error, but don't crash the app
            logger.error(f"Error listing serial ports: {e}")
            return []
