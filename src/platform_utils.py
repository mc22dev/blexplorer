
import logging

from kivy.utils import platform as kivy_platform

logger = logging.getLogger(__name__)

if kivy_platform == 'android':
    from jnius import autoclass
    from android.permissions import request_permissions as android_request_permissions
    PythonActivity = autoclass('org.kivy.android.PythonActivity')
    Build = autoclass('android.os.Build$VERSION')
    PackageManager = autoclass('android.content.pm.PackageManager')
else:
    # Create mock classes for non-Android platforms to avoid import errors
    PythonActivity = None
    Build = None
    PackageManager = None
    android_request_permissions = None


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
