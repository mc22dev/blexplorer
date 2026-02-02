import asyncio
from typing import Optional, Callable, Any

from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.descriptor import BleakGATTDescriptor
from bleak.exc import BleakError

from models import LogLevel
from config_manager import ConfigManager
from ble_adapter import BLEAdapter


class BleakAdapter(BLEAdapter):
    """A Bleak-based BLE adapter."""

    @staticmethod
    def _crc16_modbus(data: bytes) -> int:
        crc = 0xFFFF
        for byte in data:
            crc ^= byte
            for _ in range(8):
                if crc & 0x0001:
                    crc = (crc >> 1) ^ 0xA001
                else:
                    crc >>= 1
        return crc

    def __init__(self,
                 device_discovered_callback: Callable[[BLEDevice, AdvertisementData], Any],
                 connection_status_callback: Callable[[bool], Any],
                 notification_callback: Callable[[BleakGATTCharacteristic, bytes], Any],
                 logger_callback: Callable[[str, LogLevel], Any],
                 config_manager: ConfigManager) -> None:
        """
        Initializes the BleakAdapter.

        Args:
            device_discovered_callback: Callback for when a device is discovered.
            connection_status_callback: Callback for connection status changes.
            notification_callback: Callback for characteristic notifications.
            logger_callback: Callback for logging messages.
        """
        self.client: Optional[BleakClient] = None
        self.scanner: Optional[BleakScanner] = None
        self.selected_device_address: Optional[str] = None
        self.adapter: Optional[str] = None
        self._manual_disconnect: bool = False

        self.device_discovered_callback = device_discovered_callback
        self.connection_status_callback = connection_status_callback
        self.notification_callback = notification_callback
        self.logger_callback = logger_callback
        self.config_manager = config_manager

    async def shutdown(self) -> None:
        """Shuts down the BLE manager."""
        if self.scanner:
            await self.scanner.stop()
        if self.client and self.client.is_connected:
            self.logger_callback("Disconnecting on shutdown...", LogLevel.INFO)
            try:
                await self.client.disconnect()
                self.logger_callback("Disconnected on shutdown.", LogLevel.INFO)
            except BleakError as e:
                self.logger_callback(f"Error during shutdown disconnect: {e}", LogLevel.ERROR)

    async def scan_for_devices(self, adapter: Optional[str]) -> None:
        """Starts a non-blocking BLE scan."""
        scanner_kwargs = {"adapter": adapter} if adapter else {}
        # Use "passive" scanning mode on Android to improve reliability
        if "android" in BleakScanner.__module__:
            scanner_kwargs["scanning_mode"] = "passive"

        self.scanner = BleakScanner(
            detection_callback=self._on_device_found,
            **scanner_kwargs
        )
        try:
            await self.scanner.start()
        except BleakError as e:
            self.logger_callback(f"Scanning Error: {e}", LogLevel.ERROR)

    def _on_device_found(self, device: BLEDevice, adv_data: AdvertisementData) -> None:
        """Callback for when BleakScanner discovers a device."""
        self.device_discovered_callback(device, adv_data)

    async def stop_scan(self) -> None:
        """Stops the BLE scan."""
        if self.scanner:
            try:
                await self.scanner.stop()
            except AssertionError:
                self.logger_callback(
                    "AssertionError during scan stop, possibly due to Wine environment. Ignoring.",
                    LogLevel.WARNING
                )

    async def connect_to_device(self, device_address: str, adapter: Optional[str]) -> Optional[BleakClient]:
        """Connects to a specified device by its address."""
        if self.client and self.client.is_connected and self.selected_device_address == device_address:
            self.logger_callback(f"Already connected to {device_address}. Ignoring.", LogLevel.DEBUG)
            return self.client

        self.selected_device_address = device_address
        self.adapter = adapter
        self._manual_disconnect = False

        if not self.selected_device_address:
            return None

        # Disconnect from any existing connection
        if self.client and self.client.is_connected:
            await self.client.disconnect()

        client_kwargs = {"adapter": self.adapter} if self.adapter else {}
        self.client = BleakClient(self.selected_device_address, disconnected_callback=self._on_disconnect, **client_kwargs)

        try:
            await self.client.connect()
            self.connection_status_callback(True)
            return self.client
        except (BleakError, asyncio.TimeoutError) as e:
            self.logger_callback(f"Connection Error: {e}", LogLevel.ERROR)
            self.connection_status_callback(False)
            return None

    async def disconnect_from_device(self) -> None:
        """Disconnects from the currently connected device."""
        self._manual_disconnect = True
        if self.client and self.client.is_connected:
            self.logger_callback(f"Disconnecting from {self.client.address}...", LogLevel.INFO)
            await self.client.disconnect()

    def _on_disconnect(self, client: BleakClient) -> None:
        """Handles the device disconnection event."""
        if self._manual_disconnect:
            self.logger_callback(f"Device {client.address} disconnected.", LogLevel.INFO)
        else:
            self.logger_callback(f"Device {client.address} disconnected unexpectedly.", LogLevel.WARNING)

        self.connection_status_callback(False)
        # Reconnect automatically only if the disconnection was not manual
        if not self._manual_disconnect and self.selected_device_address:
            self.logger_callback("Connection lost, attempting to reconnect...", LogLevel.INFO)
            asyncio.create_task(self.connect_to_device(self.selected_device_address, self.adapter))
        else:
            self.selected_device_address = None

    async def read_characteristic(self, characteristic_uuid: str) -> Optional[bytes]:
        """Reads the value of a characteristic."""
        value = None
        if self.client:
            try:
                value = await self.client.read_gatt_char(characteristic_uuid)
            except BleakError as e:
                self.logger_callback(f"Read Error on {characteristic_uuid}: {e}", LogLevel.ERROR)
        return value

    async def write_characteristic(self, characteristic_uuid: str, value: bytes) -> bool:
        """Writes a value to a characteristic."""
        success = False
        if self.client:
            try:
                await self.client.write_gatt_char(characteristic_uuid, value)
                success = True
            except BleakError as e:
                self.logger_callback(f"Write Error on {characteristic_uuid}: {e}", LogLevel.ERROR)
        return success

    async def subscribe_to_characteristic(self, characteristic_uuid: str) -> None:
        """Subscribes to notifications for a characteristic."""
        if self.client:
            try:
                await self.client.start_notify(characteristic_uuid, self._internal_notification_handler)
            except BleakError as e:
                self.logger_callback(f"Subscribe Error on {characteristic_uuid}: {e}", LogLevel.ERROR)

    async def unsubscribe_from_characteristic(self, characteristic_uuid: str) -> None:
        """Unsubscribes from notifications for a characteristic."""
        if self.client:
            try:
                await self.client.stop_notify(characteristic_uuid)
            except BleakError as e:
                self.logger_callback(f"Unsubscribe Error on {characteristic_uuid}: {e}", LogLevel.ERROR)

    def _internal_notification_handler(self, characteristic: BleakGATTCharacteristic, data: bytes) -> None:
        """Internal handler to pass notifications to the main app."""
        ota_characteristic_uuid = self.config_manager.get_setting('ota', 'characteristic_uuid')
        if characteristic.uuid == ota_characteristic_uuid and hasattr(self, 'ota_notification_queue') and self.ota_notification_queue:
            self.ota_notification_queue.put_nowait(data)
        else:
            self.notification_callback(characteristic, data)

    def get_descriptor(self, descriptor_uuid: str):
        for service in self.client.services:
            for characteristic in service.characteristics:
                for descriptor in characteristic.descriptors:
                    if descriptor.uuid == descriptor_uuid:
                        return descriptor
        return None

    async def read_descriptor(self, descriptor_uuid: str) -> Optional[bytes]:
        """Reads the value of a descriptor."""
        value = None
        if self.client:
            try:
                descriptor = self.get_descriptor(descriptor_uuid)
                if descriptor:
                    value = await self.client.read_gatt_descriptor(descriptor.handle)
            except BleakError as e:
                self.logger_callback(f"Read Error on descriptor uuid {descriptor_uuid}: {e}", LogLevel.ERROR)
        return value

    async def write_descriptor(self, descriptor_uuid: str, value: bytes) -> bool:
        """Writes a value to a descriptor."""
        success = False
        if self.client:
            try:
                descriptor = self.get_descriptor(descriptor_uuid)
                if descriptor:
                    await self.client.write_gatt_descriptor(descriptor.handle, value)
                    success = True
            except BleakError as e:
                self.logger_callback(f"Write Error on descriptor uuid {descriptor_uuid}: {e}", LogLevel.ERROR)
        return success

    async def start_ota_upload(self, filepath: str, progress_callback: Callable[[int], Any]) -> None:
        """The core logic for the OTA upload, following the Telink protocol."""
        self.logger_callback(f"Starting OTA upload for {filepath}", LogLevel.INFO)
        self.ota_notification_queue = asyncio.Queue()
        ota_service_uuid = self.config_manager.get_setting('ota', 'service_uuid')
        ota_characteristic_uuid = self.config_manager.get_setting('ota', 'characteristic_uuid')

        # Verify that the service and characteristic exist on the device
        ota_service = self.client.services.get_service(ota_service_uuid)
        if not ota_service:
            self.logger_callback(f"OTA service {ota_service_uuid} not found on the device.", LogLevel.ERROR)
            return

        ota_characteristic = ota_service.get_characteristic(ota_characteristic_uuid)
        if not ota_characteristic:
            self.logger_callback(f"OTA characteristic {ota_characteristic_uuid} not found within the OTA service.", LogLevel.ERROR)
            return

        try:
            with open(filepath, "rb") as f:
                firmware = f.read()

            await self.client.start_notify(ota_characteristic_uuid, self._internal_notification_handler)
            self.logger_callback("OTA notifications started.", LogLevel.DEBUG)

            # Start command
            start_command = b'\x01\xff\xff\xff'
            await self.client.write_gatt_char(ota_characteristic_uuid, start_command, response=True)
            self.logger_callback(f"Sent OTA start command: {start_command.hex()}", LogLevel.DEBUG)

            # Wait for ACK
            ack = await asyncio.wait_for(self.ota_notification_queue.get(), timeout=5.0)
            if ack[0] != 0x01:
                raise BleakError(f"OTA Start ACK failed. Expected 0x01, got {ack.hex()}")
            self.logger_callback("Received OTA start ACK.", LogLevel.DEBUG)

            # Send firmware chunks
            total_size = len(firmware)
            chunk_size = 16
            for i in range(0, total_size, chunk_size):
                chunk = firmware[i:i+chunk_size]
                packet_index = i // chunk_size

                # Pad chunk if it's smaller than chunk_size
                if len(chunk) < chunk_size:
                    chunk += b'\xff' * (chunk_size - len(chunk))

                # Packet format: [index (2 bytes LE), data (16 bytes)]
                header = packet_index.to_bytes(2, 'little')
                packet_data = header + chunk

                # Calculate CRC and append
                crc = self._crc16_modbus(packet_data).to_bytes(2, 'little')
                packet_to_send = packet_data + crc

                await self.client.write_gatt_char(ota_characteristic_uuid, packet_to_send, response=True)

                # Wait for ACK for the current packet index
                ack_index_data = await asyncio.wait_for(self.ota_notification_queue.get(), timeout=2.0)
                ack_index = int.from_bytes(ack_index_data[:2], 'little')

                if ack_index != packet_index:
                    raise BleakError(f"OTA data ACK mismatch. Expected {packet_index}, got {ack_index}")

                progress = int((i + len(chunk)) / total_size * 100)
                progress_callback(progress)

            # End command
            end_command = b'\x02\x00'
            await self.client.write_gatt_char(ota_characteristic_uuid, end_command, response=True)
            self.logger_callback(f"Sent OTA end command: {end_command.hex()}", LogLevel.DEBUG)

            # Wait for final ACK
            final_ack = await asyncio.wait_for(self.ota_notification_queue.get(), timeout=5.0)
            if final_ack[0] != 0x02:
                raise BleakError(f"OTA End ACK failed. Expected 0x02, got {final_ack.hex()}")
            self.logger_callback("Received OTA end ACK.", LogLevel.DEBUG)

            progress_callback(100)
            self.logger_callback("OTA upload completed successfully.", LogLevel.SUCCESS)

        except FileNotFoundError:
            self.logger_callback(f"Firmware file not found at {filepath}", LogLevel.ERROR)
        except asyncio.TimeoutError:
            self.logger_callback("OTA operation timed out waiting for ACK.", LogLevel.ERROR)
        except BleakError as e:
            self.logger_callback(f"OTA Upload Error: {e}", LogLevel.ERROR)
        except Exception as e:
            self.logger_callback(f"An unexpected error occurred during OTA upload: {e}", LogLevel.ERROR)
        finally:
            if self.client and self.client.is_connected:
                await self.client.stop_notify(ota_characteristic_uuid)
                self.logger_callback("OTA notifications stopped.", LogLevel.DEBUG)
            self.ota_notification_queue = None
