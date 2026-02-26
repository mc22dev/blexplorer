
import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Callable, Tuple


@dataclass
class BondedDevice:
    """A class to represent a bonded Bluetooth device."""
    name: str
    address: str
    bond_state: str


@dataclass
class SerialPort:
    """A class to represent a serial port."""
    device: str
    description: str


@dataclass
class WifiAccessPoint:
    """A class to represent a Wi-Fi access point."""
    ssid: str
    bssid: str
    rssi: int
    channel: int
    frequency: int  # MHz
    security: str
    mode: str = ""
    rate: str = ""
    is_connected: bool = False


class PlatformUtilsBase(ABC):
    """
    Abstract base class for platform-specific utility operations.
    """

    @abstractmethod
    def check_android_permissions(self) -> bool:
        """
        Checks if the necessary Android permissions for BLE scanning are granted.
        """
        raise NotImplementedError

    @abstractmethod
    def request_android_permissions(self, callback: Callable):
        """
        Requests BLE scanning permissions on Android.
        """
        raise NotImplementedError

    @abstractmethod
    def is_bluetooth_enabled(self) -> bool:
        """
        Checks if the Bluetooth adapter is enabled.
        """
        raise NotImplementedError

    @abstractmethod
    def is_location_enabled(self) -> bool:
        """
        Checks if Location Services are enabled.
        """
        raise NotImplementedError

    @abstractmethod
    async def get_bonded_devices(self) -> List[BondedDevice]:
        """
        Retrieves a list of bonded Bluetooth devices.
        """
        raise NotImplementedError

    @abstractmethod
    def list_serial_ports(self) -> List[SerialPort]:
        """
        Lists available serial ports.
        """
        raise NotImplementedError

    @abstractmethod
    async def create_serial_connection(
        self,
        loop: asyncio.AbstractEventLoop,
        protocol_factory: Callable[[], asyncio.Protocol],
        url: str,
        **kwargs
    ) -> Tuple[asyncio.Transport, asyncio.Protocol]:
        """
        Creates a platform-specific serial connection.
        """
        raise NotImplementedError

    @abstractmethod
    def get_local_ip_and_mask(self) -> Tuple[str, str]:
        """
        Retrieves the local IP address and netmask.
        """
        raise NotImplementedError

    @abstractmethod
    def get_arp_table(self) -> dict:
        """
        Retrieves the ARP table as a dictionary mapping IP addresses to MAC addresses.
        """
        raise NotImplementedError

    @abstractmethod
    async def scan_wifi(self) -> List[WifiAccessPoint]:
        """
        Scans for available Wi-Fi access points.
        """
        raise NotImplementedError

    @abstractmethod
    def keep_screen_on(self, on: bool = True):
        """
        Keeps the screen on.
        """
        raise NotImplementedError
