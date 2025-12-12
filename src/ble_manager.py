import asyncio
import threading
from typing import Optional, List, Tuple, Callable, Any

from bleak import BleakClient, BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.descriptor import BleakGATTDescriptor
from bleak.exc import BleakError


class BLEManager:
    """A manager for handling BLE communications."""

    def __init__(self,
                 device_discovered_callback: Callable[[BLEDevice, AdvertisementData], Any],
                 connection_status_callback: Callable[[bool], Any],
                 notification_callback: Callable[[BleakGATTCharacteristic, bytes], Any],
                 logger_callback: Callable[[str], Any]) -> None:
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
            self.logger_callback("Disconnecting on shutdown...")
            future = asyncio.run_coroutine_threadsafe(self.client.disconnect(), self.loop)
            try:
                future.result(timeout=2.0)
                self.logger_callback("Disconnected on shutdown.")
            except (asyncio.TimeoutError, BleakError) as e:
                self.logger_callback(f"Error during shutdown disconnect: {e}")
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
            self.logger_callback(f"Scanning Error: {e}")

    def connect_to_device(self, device_address: str, adapter: Optional[str]) -> None:
        """Connects to a specified device by its address."""
        if self.client and self.client.is_connected and self.selected_device_address == device_address:
            self.logger_callback(f"Already connected to {device_address}. Ignoring.")
            return

        self.selected_device_address = device_address
        self.adapter = adapter
        self._manual_disconnect = False
        asyncio.run_coroutine_threadsafe(self._manage_connection(), self.loop)

    def disconnect_from_device(self) -> None:
        """Disconnects from the currently connected device."""
        self._manual_disconnect = True
        if self.client and self.client.is_connected:
            self.logger_callback(f"Disconnecting from {self.client.address}...")
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
            self.logger_callback(f"Connection Error: {e}")
            self.connection_status_callback(False)

    def _on_disconnect(self, client: BleakClient) -> None:
        """Handles the device disconnection event."""
        self.logger_callback(f"Device {client.address} disconnected.")
        self.connection_status_callback(False)
        # Reconnect automatically only if the disconnection was not manual
        if not self._manual_disconnect and self.selected_device_address:
            self.logger_callback("Connection lost, attempting to reconnect...")
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
                self.logger_callback(f"Read Error on {characteristic_uuid}: {e}")
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
                self.logger_callback(f"Write Error on {characteristic_uuid}: {e}")
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
                self.logger_callback(f"Subscribe Error on {characteristic_uuid}: {e}")

    def unsubscribe_from_characteristic(self, characteristic_uuid: str) -> None:
        """Unsubscribes from notifications for a characteristic."""
        asyncio.run_coroutine_threadsafe(self._unsubscribe_from_characteristic(characteristic_uuid), self.loop)

    async def _unsubscribe_from_characteristic(self, characteristic_uuid: str) -> None:
        """The core logic for unsubscribing from a characteristic."""
        if self.client:
            try:
                await self.client.stop_notify(characteristic_uuid)
            except BleakError as e:
                self.logger_callback(f"Unsubscribe Error on {characteristic_uuid}: {e}")

    def _internal_notification_handler(self, characteristic: BleakGATTCharacteristic, data: bytes) -> None:
        """Internal handler to pass notifications to the main app."""
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
                self.logger_callback(f"Read Error on descriptor handle {descriptor_handle}: {e}")
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
                self.logger_callback(f"Write Error on descriptor handle {descriptor_handle}: {e}")
        callback(success)
