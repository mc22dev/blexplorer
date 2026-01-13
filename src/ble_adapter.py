from abc import ABC, abstractmethod
from typing import Optional, Callable, Any

class BLEAdapter(ABC):
    @abstractmethod
    def __init__(self,
                 device_discovered_callback: Callable[[Any, Any], Any],
                 connection_status_callback: Callable[[bool], Any],
                 notification_callback: Callable[[Any, bytes], Any],
                 logger_callback: Callable[[str, Any], Any],
                 config_manager: Any) -> None:
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        pass

    @abstractmethod
    async def scan_for_devices(self, adapter: Optional[str]) -> None:
        pass

    @abstractmethod
    async def stop_scan(self) -> None:
        pass

    @abstractmethod
    async def connect_to_device(self, device_address: str, adapter: Optional[str]) -> None:
        pass

    @abstractmethod
    async def disconnect_from_device(self) -> None:
        pass

    @abstractmethod
    async def read_characteristic(self, characteristic_uuid: str) -> Optional[bytes]:
        pass

    @abstractmethod
    async def write_characteristic(self, characteristic_uuid: str, value: bytes) -> bool:
        pass

    @abstractmethod
    async def subscribe_to_characteristic(self, characteristic_uuid: str) -> None:
        pass

    @abstractmethod
    async def unsubscribe_from_characteristic(self, characteristic_uuid: str) -> None:
        pass

    @abstractmethod
    async def read_descriptor(self, descriptor_handle: int) -> Optional[bytes]:
        pass

    @abstractmethod
    async def write_descriptor(self, descriptor_handle: int, value: bytes) -> bool:
        pass

    @abstractmethod
    async def start_ota_upload(self, filepath: str, progress_callback: Callable[[int], Any]) -> None:
        pass
