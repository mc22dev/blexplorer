import kivy
import bleak
import platform
from importlib.metadata import version as get_version

from kivy.properties import StringProperty
from kivy.uix.popup import Popup

from blescanner._version import __version__

try:
    import pyjnius
except ImportError:
    pyjnius = None


class ParameterWindow(Popup):
    versions_info = StringProperty('')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.versions_info = self._get_version_info()

    def _get_version_info(self):
        """
        Get versions of used libraries

        :return: string with versions
        """
        # App version
        app_version = __version__

        # Libraries versions
        versions = [
            f"Product version: {app_version}",
            f"Python version: {platform.python_version()}",
            f"Kivy version: {kivy.__version__}",
            f"Bleak version: {get_version('bleak')}",
        ]
        if pyjnius:
            versions.append(f"Pyjnius version: {get_version('pyjnius')}")
        return "\n".join(versions)
