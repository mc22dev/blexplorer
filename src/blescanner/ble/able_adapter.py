from typing import Optional, Callable, Any
from blescanner.ble.ble_adapter import BLEAdapter
from blescanner.models import LogLevel
from kivy.utils import platform
import asyncio

if platform == 'android':
    from able import BluetoothDispatcher
    from able.scan_settings import ScanSettingsBuilder, ScanSettings

    class BLEDevice:
        def __init__(self, device):
            self.device = device
            self.name = device.getName()
            self.address = device.getAddress()

    class BleakGATTCharacteristic:
        def __init__(self, characteristic):
            self.characteristic = characteristic
            self.uuid = str(characteristic.getUuid())

    class AbleAdapter(BLEAdapter):
        """An Able-based BLE adapter for Android."""

        def __init__(self,
                     device_discovered_callback: Callable[[Any, Any], Any],
                     connection_status_callback: Callable[[bool], Any],
                     notification_callback: Callable[[Any, bytes], Any],
                     logger_callback: Callable[[str, Any], Any],
                     config_manager: Any) -> None:
            self.device_discovered_callback = device_discovered_callback
            self.connection_status_callback = connection_status_callback
            self.notification_callback = notification_callback
            self.logger_callback = logger_callback
            self.config_manager = config_manager
            self.dispatcher = BluetoothDispatcher()
            self.dispatcher.bind(
                on_device=self.on_device,
                on_connection_state_change=self.on_connection_state_change,
                on_services=self.on_services,
                on_characteristic_read=self.on_characteristic_read,
                on_characteristic_write=self.on_characteristic_write,
                on_characteristic_changed=self.on_characteristic_changed,
                on_descriptor_read=self.on_descriptor_read,
                on_descriptor_write=self.on_descriptor_write
            )
            self.futures = {}

        def on_device(self, device, rssi, advertisement):
            class AdvertisementData:
                def __init__(self, rssi, manufacturer_data, service_data, service_uuids, platform_data=None):
                    self.rssi = rssi
                    self.manufacturer_data = manufacturer_data
                    self.service_data = service_data
                    self.service_uuids = service_uuids
                    self.platform_data = platform_data

            adv_data = AdvertisementData(rssi, advertisement.manufacturer_data, advertisement.service_data, advertisement.service_uuids, None)
            self.device_discovered_callback(BLEDevice(device), adv_data)

        def on_connection_state_change(self, status, state):
            if state == 'connected':
                self.dispatcher.discover_services()
            else:
                self.connection_status_callback(False)
                future = self.futures.pop('connect', None)
                if future and not future.done():
                    future.set_result(None)

        def on_services(self, services, status):
            self.services = services
            future = self.futures.pop('connect', None)
            if future and not future.done():
                future.set_result(self.dispatcher.gatt)

        def on_characteristic_read(self, characteristic, status):
            future = self.futures.pop(f'read_{characteristic.getUuid()}', None)
            if future:
                future.set_result(characteristic.getValue())

        def on_characteristic_write(self, characteristic, status):
            future = self.futures.pop(f'write_{characteristic.getUuid()}', None)
            if future:
                future.set_result(status == 0)

        def on_characteristic_changed(self, characteristic):
            self.notification_callback(BleakGATTCharacteristic(characteristic), characteristic.getValue())

        def on_descriptor_read(self, descriptor, status):
            future = self.futures.pop(f'read_{descriptor.getUuid()}', None)
            if future:
                future.set_result(descriptor.getValue())

        def on_descriptor_write(self, descriptor, status):
            future = self.futures.pop(f'write_{descriptor.getUuid()}', None)
            if future:
                future.set_result(status == 0)

        async def shutdown(self) -> None:
            self.dispatcher.stop_scan()

        async def scan_for_devices(self, adapter: Optional[str]) -> None:
            settings = ScanSettingsBuilder().setScanMode(
                ScanSettings.SCAN_MODE_LOW_LATENCY
            )
            self.dispatcher.start_scan(settings=settings)

        async def stop_scan(self) -> None:
            self.dispatcher.stop_scan()

        async def connect_to_device(self, device_address: str, adapter: Optional[str]) -> Optional[Any]:
            future = asyncio.Future()
            self.futures['connect'] = future
            self.dispatcher.connect_by_device_address(device_address)
            try:
                return await asyncio.wait_for(future, timeout=10.0)
            except asyncio.TimeoutError:
                self.logger_callback("Connection timed out.", LogLevel.ERROR)
                self.connection_status_callback(False)
                return None

        async def disconnect_from_device(self) -> None:
            self.dispatcher.close_gatt()

        def get_characteristic(self, characteristic_uuid: str):
            for service in self.services:
                for characteristic in service.getCharacteristics():
                    if str(characteristic.getUuid()) == characteristic_uuid:
                        return characteristic
            return None

        async def read_characteristic(self, characteristic_uuid: str) -> Optional[bytes]:
            characteristic = self.get_characteristic(characteristic_uuid)
            if characteristic:
                future = asyncio.Future()
                self.futures[f'read_{characteristic.getUuid()}'] = future
                self.dispatcher.read_characteristic(characteristic)
                return await future
            return None

        async def write_characteristic(self, characteristic_uuid: str, value: bytes) -> bool:
            characteristic = self.get_characteristic(characteristic_uuid)
            if characteristic:
                future = asyncio.Future()
                self.futures[f'write_{characteristic.getUuid()}'] = future
                self.dispatcher.write_characteristic(characteristic, value)
                return await future
            return False

        async def subscribe_to_characteristic(self, characteristic_uuid: str) -> None:
            characteristic = self.get_characteristic(characteristic_uuid)
            if characteristic:
                self.dispatcher.enable_notifications(characteristic, True)

        async def unsubscribe_from_characteristic(self, characteristic_uuid: str) -> None:
            characteristic = self.get_characteristic(characteristic_uuid)
            if characteristic:
                self.dispatcher.enable_notifications(characteristic, False)

        def get_descriptor(self, descriptor_uuid: str):
            for service in self.services:
                for characteristic in service.getCharacteristics():
                    for descriptor in characteristic.getDescriptors():
                        if str(descriptor.getUuid()) == descriptor_uuid:
                            return descriptor
            return None

        async def read_descriptor(self, descriptor_uuid: str) -> Optional[bytes]:
            descriptor = self.get_descriptor(descriptor_uuid)
            if descriptor:
                future = asyncio.Future()
                self.futures[f'read_{descriptor.getUuid()}'] = future
                self.dispatcher.read_descriptor(descriptor)
                return await future
            return None

        async def write_descriptor(self, descriptor_uuid: str, value: bytes) -> bool:
            descriptor = self.get_descriptor(descriptor_uuid)
            if descriptor:
                future = asyncio.Future()
                self.futures[f'write_{descriptor.getUuid()}'] = future
                self.dispatcher.write_descriptor(descriptor, value)
                return await future
            return False

        async def start_ota_upload(self, filepath: str, progress_callback: Callable[[int], Any]) -> None:
            self.logger_callback("OTA upload is not implemented for the Able adapter.", LogLevel.WARNING)

else:
    class AbleAdapter(BLEAdapter):
        """A stub Able-based BLE adapter for non-Android platforms."""

        def __init__(self,
                     device_discovered_callback: Callable[[Any, Any], Any],
                     connection_status_callback: Callable[[bool], Any],
                     notification_callback: Callable[[Any, bytes], Any],
                     logger_callback: Callable[[str, Any], Any],
                     config_manager: Any) -> None:
            self.logger_callback = logger_callback
            self.logger_callback("Able adapter is only supported on Android.", LogLevel.WARNING)

        async def shutdown(self) -> None:
            pass

        async def scan_for_devices(self, adapter: Optional[str]) -> None:
            pass

        async def stop_scan(self) -> None:
            pass

        async def connect_to_device(self, device_address: str, adapter: Optional[str]) -> None:
            pass

        async def disconnect_from_device(self) -> None:
            pass

        async def read_characteristic(self, characteristic_uuid: str) -> Optional[bytes]:
            return None

        async def write_characteristic(self, characteristic_uuid: str, value: bytes) -> bool:
            return False

        async def subscribe_to_characteristic(self, characteristic_uuid: str) -> None:
            pass

        async def unsubscribe_from_characteristic(self, characteristic_uuid: str) -> None:
            pass

        async def read_descriptor(self, descriptor_uuid: str) -> Optional[bytes]:
            return None

        async def write_descriptor(self, descriptor_uuid: str, value: bytes) -> bool:
            return False

        async def start_ota_upload(self, filepath: str, progress_callback: Callable[[int], Any]) -> None:
            self.logger_callback("OTA upload is not implemented for the Able adapter.", LogLevel.WARNING)