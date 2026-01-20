
from kivy.utils import platform as kivy_platform

from .base import BondedDevice
from .default import DefaultPlatformUtils

if kivy_platform == 'android':
    from .android import AndroidPlatformUtils
    platform_utils = AndroidPlatformUtils()
elif kivy_platform == 'linux':
    from .linux import LinuxPlatformUtils
    platform_utils = LinuxPlatformUtils()
else:
    platform_utils = DefaultPlatformUtils()

__all__ = ['platform_utils', 'BondedDevice']
