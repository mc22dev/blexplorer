from typing import Optional, Callable, Any
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
from bleak.backends.characteristic import BleakGATTCharacteristic
from models import LogLevel
from config_manager import ConfigManager
from ble_adapter import BLEAdapter
from bleak_adapter import BleakAdapter
from able_adapter import AbleAdapter

class BLEManager:
    """A manager for handling BLE communications."""

    def __init__(self,
                 device_discovered_callback: Callable[[BLEDevice, AdvertisementData], Any],
                 connection_status_callback: Callable[[bool], Any],
                 notification_callback: Callable[[BleakGATTCharacteristic, bytes], Any],
                 logger_callback: Callable[[str, LogLevel], Any],
                 config_manager: ConfigManager) -> None:
        """
        Initializes the BLEManager.
        """
        self.logger_callback = logger_callback
        self.config_manager = config_manager
        self.connection_status_callback = connection_status_callback
        self.client = None
        ble_library = self.config_manager.get_setting('ble', 'library')

        if ble_library == 'able':
            self.adapter: BLEAdapter = AbleAdapter(
                device_discovered_callback,
                connection_status_callback,
                notification_callback,
                logger_callback,
                config_manager
            )
        else:
            self.adapter: BLEAdapter = BleakAdapter(
                device_discovered_callback,
                connection_status_callback,
                notification_callback,
                logger_callback,
                config_manager
            )

    async def shutdown(self) -> None:
        await self.adapter.shutdown()

    async def scan_for_devices(self, adapter: Optional[str]) -> None:
        await self.adapter.scan_for_devices(adapter)

    async def stop_scan(self) -> None:
        await self.adapter.stop_scan()

    async def connect_to_device(self, device_address: str, adapter: Optional[str]) -> None:
        self.client = await self.adapter.connect_to_device(device_address, adapter)
        if self.client:
            self.connection_status_callback(True)
        # The adapter will call the connection_status_callback with False on failure.

    async def disconnect_from_device(self) -> None:
        await self.adapter.disconnect_from_device()
        self.client = None

    async def read_characteristic(self, characteristic_uuid: str) -> Optional[bytes]:
        return await self.adapter.read_characteristic(characteristic_uuid)

    async def write_characteristic(self, characteristic_uuid: str, value: bytes) -> bool:
        return await self.adapter.write_characteristic(characteristic_uuid, value)

    async def subscribe_to_characteristic(self, characteristic_uuid: str) -> None:
        await self.adapter.subscribe_to_characteristic(characteristic_uuid)

    async def unsubscribe_from_characteristic(self, characteristic_uuid: str) -> None:
        await self.adapter.unsubscribe_from_characteristic(characteristic_uuid)

    async def read_descriptor(self, descriptor_handle: int) -> Optional[bytes]:
        return await self.adapter.read_descriptor(descriptor_handle)

    async def write_descriptor(self, descriptor_handle: int, value: bytes) -> bool:
        return await self.adapter.write_descriptor(descriptor_handle, value)

    async def start_ota_upload(self, filepath: str, progress_callback: Callable[[int], Any]) -> None:
        await self.adapter.start_ota_upload(filepath, progress_callback)
