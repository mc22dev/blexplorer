import asyncio
import threading
from typing import Optional, List, Tuple, Callable, Any

from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.descriptor import BleakGATTDescriptor
from bleak.exc import BleakError


from models import LogLevel

OTA_SERVICE_UUID = "00010203-0405-0607-0809-0a0b0c0d1912"
OTA_CHARACTERISTIC_UUID = "00010203-0405-0607-0809-0a0b0c0d2b12"


class BLEManager:
    """A manager for handling BLE communications."""

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
                 logger_callback: Callable[[str, LogLevel], Any]) -> None:
        """
        Initializes the BLEManager.

        Args:
            device_discovered_callback: Callback for when a device is discovered.
            connection_status_callback: Callback for connection status changes.
            notification_callback: Callback for characteristic notifications.
            logger_callback: Callback for logging messages.
        """
        self.client: Optional[BleakClient] = None
        self.selected_device_address: Optional[str] = None
        self.adapter: Optional[str] = None
        self._manual_disconnect: bool = False
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self.run_async_loop, daemon=True)
        self.thread.start()

        self.device_discovered_callback = device_discovered_callback
        self.connection_status_callback = connection_status_callback
        self.notification_callback = notification_callback
        self.logger_callback = logger_callback

    def run_async_loop(self) -> None:
        """Runs the asyncio event loop in a separate thread."""
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def shutdown(self) -> None:
        """Shuts down the BLE manager and the asyncio loop."""
        if self.client and self.client.is_connected:
            self.logger_callback("Disconnecting on shutdown...", LogLevel.INFO)
            future = asyncio.run_coroutine_threadsafe(self.client.disconnect(), self.loop)
            try:
                future.result(timeout=2.0)
                self.logger_callback("Disconnected on shutdown.", LogLevel.INFO)
            except (asyncio.TimeoutError, BleakError) as e:
                self.logger_callback(f"Error during shutdown disconnect: {e}", LogLevel.ERROR)
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.thread.join()

    def scan_for_devices(self, adapter: Optional[str], timeout: float) -> None:
        """Initiates a scan for nearby BLE devices."""
        asyncio.run_coroutine_threadsafe(self._discover_devices(adapter, timeout), self.loop)

    async def _discover_devices(self, adapter_name: Optional[str], timeout: float) -> None:
        """
        Scans for BLE devices and populates the UI with the results.

        Args:
            adapter_name: The name of the Bluetooth adapter to use.
            timeout: The duration of the scan in seconds.
        """
        scanner_kwargs = {"adapter": adapter_name} if adapter_name else {}
        try:
            discovered_devices_dict = await BleakScanner.discover(timeout=timeout, return_adv=True, **scanner_kwargs)
            sorted_devices = sorted(discovered_devices_dict.values(), key=lambda item: item[1].rssi, reverse=True)
            for device, adv_data in sorted_devices:
                self.device_discovered_callback(device, adv_data)
        except BleakError as e:
            self.logger_callback(f"Scanning Error: {e}", LogLevel.ERROR)

    def connect_to_device(self, device_address: str, adapter: Optional[str]) -> None:
        """Connects to a specified device by its address."""
        if self.client and self.client.is_connected and self.selected_device_address == device_address:
            self.logger_callback(f"Already connected to {device_address}. Ignoring.", LogLevel.DEBUG)
            return

        self.selected_device_address = device_address
        self.adapter = adapter
        self._manual_disconnect = False
        asyncio.run_coroutine_threadsafe(self._manage_connection(), self.loop)

    def disconnect_from_device(self) -> None:
        """Disconnects from the currently connected device."""
        self._manual_disconnect = True
        if self.client and self.client.is_connected:
            self.logger_callback(f"Disconnecting from {self.client.address}...", LogLevel.INFO)
            asyncio.run_coroutine_threadsafe(self.client.disconnect(), self.loop)

    async def _manage_connection(self) -> None:
        """Manages the connection to the selected device."""
        if not self.selected_device_address:
            return

        # Disconnect from any existing connection
        if self.client and self.client.is_connected:
            await self.client.disconnect()

        client_kwargs = {"adapter": self.adapter} if self.adapter else {}
        self.client = BleakClient(self.selected_device_address, disconnected_callback=self._on_disconnect, **client_kwargs)

        try:
            await self.client.connect()
            self.connection_status_callback(True)
        except (BleakError, asyncio.TimeoutError) as e:
            self.logger_callback(f"Connection Error: {e}", LogLevel.ERROR)
            self.connection_status_callback(False)

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
            asyncio.run_coroutine_threadsafe(self._manage_connection(), self.loop)
        else:
            self.selected_device_address = None

    def read_characteristic(self, characteristic_uuid: str, callback: Callable[[Optional[bytes]], Any]) -> None:
        """Reads the value of a characteristic."""
        asyncio.run_coroutine_threadsafe(self._read_characteristic(characteristic_uuid, callback), self.loop)

    async def _read_characteristic(self, characteristic_uuid: str, callback: Callable[[Optional[bytes]], Any]) -> None:
        """The core logic for reading a characteristic's value."""
        value = None
        if self.client:
            try:
                value = await self.client.read_gatt_char(characteristic_uuid)
            except BleakError as e:
                self.logger_callback(f"Read Error on {characteristic_uuid}: {e}", LogLevel.ERROR)
        callback(value)

    def write_characteristic(self, characteristic_uuid: str, value: bytes, callback: Callable[[bool], Any]) -> None:
        """Writes a value to a characteristic."""
        asyncio.run_coroutine_threadsafe(self._write_characteristic(characteristic_uuid, value, callback), self.loop)

    async def _write_characteristic(self, characteristic_uuid: str, value: bytes, callback: Callable[[bool], Any]) -> None:
        """The core logic for writing a characteristic's value."""
        success = False
        if self.client:
            try:
                await self.client.write_gatt_char(characteristic_uuid, value)
                success = True
            except BleakError as e:
                self.logger_callback(f"Write Error on {characteristic_uuid}: {e}", LogLevel.ERROR)
        callback(success)

    def subscribe_to_characteristic(self, characteristic_uuid: str) -> None:
        """Subscribes to notifications for a characteristic."""
        asyncio.run_coroutine_threadsafe(self._subscribe_to_characteristic(characteristic_uuid), self.loop)

    async def _subscribe_to_characteristic(self, characteristic_uuid: str) -> None:
        """The core logic for subscribing to a characteristic."""
        if self.client:
            try:
                await self.client.start_notify(characteristic_uuid, self._internal_notification_handler)
            except BleakError as e:
                self.logger_callback(f"Subscribe Error on {characteristic_uuid}: {e}", LogLevel.ERROR)

    def unsubscribe_from_characteristic(self, characteristic_uuid: str) -> None:
        """Unsubscribes from notifications for a characteristic."""
        asyncio.run_coroutine_threadsafe(self._unsubscribe_from_characteristic(characteristic_uuid), self.loop)

    async def _unsubscribe_from_characteristic(self, characteristic_uuid: str) -> None:
        """The core logic for unsubscribing from a characteristic."""
        if self.client:
            try:
                await self.client.stop_notify(characteristic_uuid)
            except BleakError as e:
                self.logger_callback(f"Unsubscribe Error on {characteristic_uuid}: {e}", LogLevel.ERROR)

    def _internal_notification_handler(self, characteristic: BleakGATTCharacteristic, data: bytes) -> None:
        """Internal handler to pass notifications to the main app."""
        if characteristic.uuid == OTA_CHARACTERISTIC_UUID and hasattr(self, 'ota_notification_queue') and self.ota_notification_queue:
            self.ota_notification_queue.put_nowait(data)
        else:
            self.notification_callback(characteristic, data)

    def read_descriptor(self, descriptor_handle: int, callback: Callable[[Optional[bytes]], Any]) -> None:
        """Reads the value of a descriptor."""
        asyncio.run_coroutine_threadsafe(self._read_descriptor(descriptor_handle, callback), self.loop)

    async def _read_descriptor(self, descriptor_handle: int, callback: Callable[[Optional[bytes]], Any]) -> None:
        """The core logic for reading a descriptor's value."""
        value = None
        if self.client:
            try:
                value = await self.client.read_gatt_descriptor(descriptor_handle)
            except BleakError as e:
                self.logger_callback(f"Read Error on descriptor handle {descriptor_handle}: {e}", LogLevel.ERROR)
        callback(value)

    def write_descriptor(self, descriptor_handle: int, value: bytes, callback: Callable[[bool], Any]) -> None:
        """Writes a value to a descriptor."""
        asyncio.run_coroutine_threadsafe(self._write_descriptor(descriptor_handle, value, callback), self.loop)

    async def _write_descriptor(self, descriptor_handle: int, value: bytes, callback: Callable[[bool], Any]) -> None:
        """The core logic for writing a descriptor's value."""
        success = False
        if self.client:
            try:
                await self.client.write_gatt_descriptor(descriptor_handle, value)
                success = True
            except BleakError as e:
                self.logger_callback(f"Write Error on descriptor handle {descriptor_handle}: {e}", LogLevel.ERROR)
        callback(success)

    def start_ota_upload(self, filepath: str, progress_callback: Callable[[int], Any]) -> None:
        """Starts the OTA firmware upload process."""
        self.logger_callback(f"start_ota_upload called for filepath: {filepath}", LogLevel.DEBUG)
        asyncio.run_coroutine_threadsafe(self._ota_upload(filepath, progress_callback), self.loop)

    async def _ota_upload(self, filepath: str, progress_callback: Callable[[int], Any]) -> None:
        """The core logic for the OTA upload, following the Telink protocol."""
        self.logger_callback(f"Starting OTA upload for {filepath}", LogLevel.INFO)
        self.ota_notification_queue = asyncio.Queue()

        try:
            with open(filepath, "rb") as f:
                firmware = f.read()

            await self.client.start_notify(OTA_CHARACTERISTIC_UUID, self._internal_notification_handler)
            self.logger_callback("OTA notifications started.", LogLevel.DEBUG)

            # Start command
            start_command = b'\x01\xff\xff\xff'
            await self.client.write_gatt_char(OTA_CHARACTERISTIC_UUID, start_command, response=True)
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

                await self.client.write_gatt_char(OTA_CHARACTERISTIC_UUID, packet_to_send, response=True)

                # Wait for ACK for the current packet index
                ack_index_data = await asyncio.wait_for(self.ota_notification_queue.get(), timeout=2.0)
                ack_index = int.from_bytes(ack_index_data[:2], 'little')

                if ack_index != packet_index:
                    raise BleakError(f"OTA data ACK mismatch. Expected {packet_index}, got {ack_index}")

                progress = int((i + len(chunk)) / total_size * 100)
                progress_callback(progress)

            # End command
            end_command = b'\x02\x00'
            await self.client.write_gatt_char(OTA_CHARACTERISTIC_UUID, end_command, response=True)
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
                await self.client.stop_notify(OTA_CHARACTERISTIC_UUID)
                self.logger_callback("OTA notifications stopped.", LogLevel.DEBUG)
            self.ota_notification_queue = None
