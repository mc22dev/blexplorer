
import logging
from typing import List, Callable

from dbus_fast import Variant
from dbus_fast.aio import MessageBus

from .base import PlatformUtilsBase, BondedDevice

logger = logging.getLogger(__name__)


class LinuxPlatformUtils(PlatformUtilsBase):
    """
    Utility class for handling Linux-specific operations.
    """

    def check_android_permissions(self) -> bool:
        """
        No-op on Linux.
        """
        return True

    def request_android_permissions(self, callback: Callable):
        """
        No-op on Linux.
        """
        pass

    def is_bluetooth_enabled(self) -> bool:
        """
        No-op on Linux, assuming enabled.
        """
        return True

    def is_location_enabled(self) -> bool:
        """
        No-op on Linux, assuming enabled.
        """
        return True

    async def get_bonded_devices(self) -> List[BondedDevice]:
        """
        Retrieves a list of bonded Bluetooth devices on Linux via D-Bus.
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
            if "org.freedesktop.DBus.Error.ServiceUnknown" in str(e):
                logger.warning("Could not find BlueZ service. Make sure Bluetooth is enabled and the service is running.")
            else:
                logger.error(f"Error getting bonded devices on Linux: {e}")

        return devices
