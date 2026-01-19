
import logging
from typing import List

from jnius import autoclass

from .base import PlatformUtilsBase, BondedDevice

logger = logging.getLogger(__name__)

# Android-specific imports
from android.permissions import request_permissions as android_request_permissions
PythonActivity = autoclass('org.kivy.android.PythonActivity')
Build = autoclass('android.os.Build$VERSION')
PackageManager = autoclass('android.content.pm.PackageManager')
Context = autoclass('android.content.Context')
BluetoothAdapter = autoclass('android.bluetooth.BluetoothAdapter')
BluetoothDevice = autoclass('android.bluetooth.BluetoothDevice')
LocationManager = autoclass('android.location.LocationManager')


class AndroidPlatformUtils(PlatformUtilsBase):
    """
    Utility class for handling Android-specific operations.
    """

    def _get_android_permissions(self) -> list[str]:
        """
        Returns the appropriate list of Android permissions based on the API level.
        """
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

    def check_android_permissions(self) -> bool:
        """
        Checks if the necessary Android permissions for BLE scanning are granted.
        """
        context = PythonActivity.mActivity
        permissions_to_check = self._get_android_permissions()

        granted = all(
            context.checkSelfPermission(p) == PackageManager.PERMISSION_GRANTED
            for p in permissions_to_check
        )
        logger.debug(f"Permission check for {permissions_to_check}: {granted}")
        return granted

    def request_android_permissions(self, callback):
        """
        Requests BLE scanning permissions on Android.
        """
        permissions = self._get_android_permissions()
        logger.info(f"Requesting Android permissions: {permissions}")
        android_request_permissions(permissions, callback)

    def is_bluetooth_enabled(self) -> bool:
        """
        Checks if the Bluetooth adapter is enabled on Android.
        """
        adapter = BluetoothAdapter.getDefaultAdapter()
        if adapter is None:
            logger.warning("Device does not support Bluetooth.")
            return False
        return adapter.isEnabled()

    def is_location_enabled(self) -> bool:
        """
        Checks if Location Services are enabled on Android.
        """
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

    async def get_bonded_devices(self) -> List[BondedDevice]:
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
