
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Callable


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
