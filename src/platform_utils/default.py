
from typing import List, Callable

from .base import PlatformUtilsBase, BondedDevice


class DefaultPlatformUtils(PlatformUtilsBase):
    """
    Default platform utility implementation for unsupported platforms.
    """

    def check_android_permissions(self) -> bool:
        """
        No-op on this platform.
        """
        return True

    def request_android_permissions(self, callback: Callable):
        """
        No-op on this platform.
        """
        pass

    def is_bluetooth_enabled(self) -> bool:
        """
        No-op on this platform, assuming enabled.
        """
        return True

    def is_location_enabled(self) -> bool:
        """
        No-op on this platform, assuming enabled.
        """
        return True

    async def get_bonded_devices(self) -> List[BondedDevice]:
        """
        No-op on this platform.
        """
        return []
