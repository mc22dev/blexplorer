
import logging
from dataclasses import dataclass
from typing import List

from kivy.utils import platform as kivy_platform

logger = logging.getLogger(__name__)

if kivy_platform == 'android':
    from jnius import autoclass
    from android.permissions import request_permissions as android_request_permissions
    PythonActivity = autoclass('org.kivy.android.PythonActivity')
    Build = autoclass('android.os.Build$VERSION')
    PackageManager = autoclass('android.content.pm.PackageManager')
    Context = autoclass('android.content.Context')
    BluetoothAdapter = autoclass('android.bluetooth.BluetoothAdapter')
    BluetoothDevice = autoclass('android.bluetooth.BluetoothDevice')
    LocationManager = autoclass('android.location.LocationManager')
elif kivy_platform == 'linux':
    import asyncio
    from dbus_fast.aio import MessageBus
    from dbus_fast import Variant
    # Mock classes for non-Android platforms to avoid import errors
    PythonActivity = None
    Build = None
    PackageManager = None
    android_request_permissions = None
    Context = None
    BluetoothAdapter = None
    BluetoothDevice = None
    LocationManager = None
else:
    # Create mock classes for non-Android platforms to avoid import errors
    PythonActivity = None
    Build = None
    PackageManager = None
    android_request_permissions = None
    Context = None
    BluetoothAdapter = None
    BluetoothDevice = None
    LocationManager = None


@dataclass
class BondedDevice:
    """A class to represent a bonded Bluetooth device."""
    name: str
    address: str
    bond_state: str


class PlatformUtils:
    """
    Utility class for handling platform-specific operations, such as Android permissions.
    """

    @staticmethod
    def _get_android_permissions() -> list[str]:
        """
        Returns the appropriate list of Android permissions based on the API level.
        """
        if not Build:
            return []

        sdk_int = Build.SDK_INT
        if sdk_int >= 31:  # Android 12 (API 31) and above
            return [
                "android.permission.BLUETOOTH_SCAN",
                "android.permission.BLUETOOTH_CONNECT",
                "android.permission.ACCESS_FINE_LOCATION",
            ]
        else:  # Older Android versions
            return [
                "android.permission.BLUETOOTH",
                "android.permission.BLUETOOTH_ADMIN",
                "android.permission.ACCESS_FINE_LOCATION",
            ]

    @staticmethod
    def check_android_permissions() -> bool:
        """
        Checks if the necessary Android permissions for BLE scanning are granted.
        """
        if kivy_platform != 'android':
            return True

        context = PythonActivity.mActivity
        permissions_to_check = PlatformUtils._get_android_permissions()

        granted = all(
            context.checkSelfPermission(p) == PackageManager.PERMISSION_GRANTED
            for p in permissions_to_check
        )
        logger.debug(f"Permission check for {permissions_to_check}: {granted}")
        return granted

    @staticmethod
    def request_android_permissions(callback):
        """
        Requests BLE scanning permissions on Android.
        """
        if kivy_platform != 'android':
            return

        permissions = PlatformUtils._get_android_permissions()
        logger.info(f"Requesting Android permissions: {permissions}")
        android_request_permissions(permissions, callback)

    @staticmethod
    def is_bluetooth_enabled() -> bool:
        """
        Checks if the Bluetooth adapter is enabled on Android.
        """
        if kivy_platform != 'android':
            return True

        adapter = BluetoothAdapter.getDefaultAdapter()
        if adapter is None:
            logger.warning("Device does not support Bluetooth.")
            return False
        return adapter.isEnabled()

    @staticmethod
    def is_location_enabled() -> bool:
        """
        Checks if Location Services are enabled on Android.
        """
        if kivy_platform != 'android':
            return True

        context = PythonActivity.mActivity
        location_manager = context.getSystemService(Context.LOCATION_SERVICE)
        if not location_manager:
            return False

        try:
            gps_enabled = location_manager.isProviderEnabled(LocationManager.GPS_PROVIDER)
            network_enabled = location_manager.isProviderEnabled(LocationManager.NETWORK_PROVIDER)
            return gps_enabled or network_enabled
        except Exception as e:
            logger.error(f"Error checking location status: {e}")
            return False

    @staticmethod
    async def get_bonded_devices() -> List[BondedDevice]:
        """
        Retrieves a list of bonded Bluetooth devices.
        This feature is currently implemented for Android and Linux only.
        """
        if kivy_platform == 'android':
            return PlatformUtils._get_bonded_devices_android()
        elif kivy_platform == 'linux':
            return await PlatformUtils._get_bonded_devices_linux()
        return []

    @staticmethod
    def _get_bonded_devices_android() -> List[BondedDevice]:
        """
        Retrieves a list of bonded Bluetooth devices on Android.
        """
        adapter = BluetoothAdapter.getDefaultAdapter()
        if not adapter:
            return []

        bonded_devices = adapter.getBondedDevices()
        if not bonded_devices:
            return []

        devices = []
        for device in bonded_devices.toArray():
            bond_state_int = device.getBondState()
            bond_state = "Unknown"
            if bond_state_int == BluetoothDevice.BOND_BONDED:
                bond_state = "Bonded"
            elif bond_state_int == BluetoothDevice.BOND_BONDING:
                bond_state = "Bonding"
            elif bond_state_int == BluetoothDevice.BOND_NONE:
                bond_state = "Not Bonded"

            devices.append(
                BondedDevice(
                    name=device.getName() or "Unnamed",
                    address=device.getAddress(),
                    bond_state=bond_state,
                )
            )

        return devices

    @staticmethod
    async def _get_bonded_devices_linux() -> List[BondedDevice]:
        """
        Retriees a list of bonded Bluetooth devices on Linux via D-Bus.
        """
        devices = []
        try:
            bus = await MessageBus().connect()
            introspection = await bus.introspect('org.bluez', '/')
            obj = bus.get_proxy_object('org.bluez', '/', introspection)
            iface = obj.get_interface('org.freedesktop.DBus.ObjectManager')
            managed_objects = await iface.call_get_managed_objects()

            for path, interfaces in managed_objects.items():
                if 'org.bluez.Device1' in interfaces:
                    device_props = interfaces['org.bluez.Device1']
                    if device_props.get('Paired', Variant('b', False)).value:
                        devices.append(
                            BondedDevice(
                                name=device_props.get('Name', Variant('s', 'Unknown')).value,
                                address=device_props.get('Address', Variant('s', '')).value,
                                bond_state="Bonded",
                            )
                        )
        except Exception as e:
            logger.error(f"Error getting bonded devices on Linux: {e}")

        return devices
