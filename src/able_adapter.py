from typing import Optional, Callable, Any
from ble_adapter import BLEAdapter
from models import LogLevel
from kivy.utils import platform

if platform == 'android':
    from jnius import autoclass, PythonJavaClass, java_method
    from android.permissions import request_permissions, Permission

    # Android BLE permissions
    BluetoothAdapter = autoclass('android.bluetooth.BluetoothAdapter')
    BluetoothDevice = autoclass('android.bluetooth.BluetoothDevice')
    BluetoothGatt = autoclass('android.bluetooth.BluetoothGatt')
    BluetoothGattCallback = autoclass('android.bluetooth.BluetoothGattCallback')
    BluetoothGattCharacteristic = autoclass('android.bluetooth.BluetoothGattCharacteristic')
    BluetoothGattDescriptor = autoclass('android.bluetooth.BluetoothGattDescriptor')
    BluetoothGattService = autoclass('android.bluetooth.BluetoothGattService')
    BluetoothManager = autoclass('android.bluetooth.BluetoothManager')
    BluetoothProfile = autoclass('android.bluetooth.BluetoothProfile')
    ScanCallback = autoclass('android.bluetooth.le.ScanCallback')
    ScanFilter = autoclass('android.bluetooth.le.ScanFilter')
    ScanResult = autoclass('android.bluetooth.le.ScanResult')
    ScanSettings = autoclass('android.bluetooth.le.ScanSettings')
    UUID = autoclass('java.util.UUID')

    class GattCallback(PythonJavaClass):
        __javainterfaces__ = ['android/bluetooth/BluetoothGattCallback']

        def __init__(self, adapter):
            super().__init__()
            self.adapter = adapter

        @java_method('(Landroid/bluetooth/BluetoothGatt;II)V')
        def onConnectionStateChange(self, gatt, status, newState):
            self.adapter.on_connection_state_change(gatt, status, newState)

        @java_method('(Landroid/bluetooth/BluetoothGatt;I)V')
        def onServicesDiscovered(self, gatt, status):
            self.adapter.on_services_discovered(gatt, status)

        @java_method('(Landroid/bluetooth/BluetoothGatt;Landroid/bluetooth/BluetoothGattCharacteristic;I)V')
        def onCharacteristicRead(self, gatt, characteristic, status):
            self.adapter.on_characteristic_read(gatt, characteristic, status)

        @java_method('(Landroid/bluetooth/BluetoothGatt;Landroid/bluetooth/BluetoothGattCharacteristic;I)V')
        def onCharacteristicWrite(self, gatt, characteristic, status):
            self.adapter.on_characteristic_write(gatt, characteristic, status)

        @java_method('(Landroid/bluetooth/BluetoothGatt;Landroid/bluetooth/BluetoothGattCharacteristic;)V')
        def onCharacteristicChanged(self, gatt, characteristic):
            self.adapter.on_characteristic_changed(gatt, characteristic)

    class AbleScanCallback(PythonJavaClass):
        __javainterfaces__ = ['android/bluetooth/le/ScanCallback']

        def __init__(self, adapter):
            super().__init__()
            self.adapter = adapter

        @java_method('(ILandroid/bluetooth/le/ScanResult;)V')
        def onScanResult(self, callbackType, result):
            self.adapter.on_scan_result(callbackType, result)

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
            self.gatt_callback = GattCallback(self)
            self.scan_callback = AbleScanCallback(self)
            self.bluetooth_adapter = BluetoothAdapter.getDefaultAdapter()
            self.scanner = self.bluetooth_adapter.getBluetoothLeScanner()

        def on_scan_result(self, callbackType, result):
            self.device_discovered_callback(result.getDevice(), result.getScanRecord().getBytes())

        def on_connection_state_change(self, gatt, status, newState):
            if newState == BluetoothProfile.STATE_CONNECTED:
                self.connection_status_callback(True)
                gatt.discoverServices()
            else:
                self.connection_status_callback(False)

        def on_services_discovered(self, gatt, status):
            # To be implemented
            pass

        def on_characteristic_read(self, gatt, characteristic, status):
            # To be implemented
            pass

        def on_characteristic_write(self, gatt, characteristic, status):
            # To be implemented
            pass

        def on_characteristic_changed(self, gatt, characteristic):
            self.notification_callback(characteristic, characteristic.getValue())

        async def shutdown(self) -> None:
            pass

        async def scan_for_devices(self, adapter: Optional[str]) -> None:
            request_permissions([Permission.BLUETOOTH, Permission.BLUETOOTH_ADMIN, Permission.ACCESS_FINE_LOCATION])
            self.scanner.startScan(None, ScanSettings.Builder().build(), self.scan_callback)

        async def stop_scan(self) -> None:
            self.scanner.stopScan(self.scan_callback)

        async def connect_to_device(self, device_address: str, adapter: Optional[str]) -> None:
            device = self.bluetooth_adapter.getRemoteDevice(device_address)
            device.connectGatt(None, False, self.gatt_callback)

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

        async def read_descriptor(self, descriptor_handle: int) -> Optional[bytes]:
            return None

        async def write_descriptor(self, descriptor_handle: int, value: bytes) -> bool:
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

        async def read_descriptor(self, descriptor_handle: int) -> Optional[bytes]:
            return None

        async def write_descriptor(self, descriptor_handle: int, value: bytes) -> bool:
            return False

        async def start_ota_upload(self, filepath: str, progress_callback: Callable[[int], Any]) -> None:
            self.logger_callback("OTA upload is not implemented for the Able adapter.", LogLevel.WARNING)