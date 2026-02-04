import psutil
import platform
import os
from kivy.uix.screenmanager import Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import StringProperty, ListProperty
from kivy.clock import Clock
from kivy.utils import platform as kivy_platform

class DiskItem(BoxLayout):
    device = StringProperty("")
    mountpoint = StringProperty("")
    fstype = StringProperty("")
    total = StringProperty("")
    used = StringProperty("")
    free = StringProperty("")
    percent = StringProperty("")

class SysInfoScreen(Screen):
    os_info = StringProperty("")
    cpu_info = StringProperty("")
    memory_info = StringProperty("")
    disk_data = ListProperty([])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.update_info()

    def on_enter(self, *args):
        self.update_info()
        self._timer = Clock.schedule_interval(self.update_info, 5)

    def on_leave(self, *args):
        if hasattr(self, '_timer'):
            self._timer.cancel()

    def update_info(self, dt=None):
        # OS Info
        try:
            os_name = platform.system()
            if kivy_platform == 'android':
                os_name = "Android"

            self.os_info = (
                f"System: {os_name}\n"
                f"Release: {platform.release()}\n"
                f"Version: {platform.version()}\n"
                f"Architecture: {platform.machine()}"
            )
        except Exception as e:
            self.os_info = f"Error getting OS info: {e}"

        # CPU Info
        try:
            cpu_count_logical = psutil.cpu_count(logical=True)
            cpu_count_physical = psutil.cpu_count(logical=False)

            freq = None
            try:
                freq = psutil.cpu_freq()
            except Exception:
                pass # cpu_freq might not be available

            freq_str = f"{freq.current:.2f}MHz" if freq and freq.current else "N/A"

            self.cpu_info = (
                f"Physical Cores: {cpu_count_physical}\n"
                f"Total Cores: {cpu_count_logical}\n"
                f"Frequency: {freq_str}"
            )
        except Exception as e:
            self.cpu_info = f"Error getting CPU info: {e}"

        # Memory Info
        try:
            mem = psutil.virtual_memory()
            self.memory_info = (
                f"Total: {self._format_bytes(mem.total)}\n"
                f"Available: {self._format_bytes(mem.available)}\n"
                f"Used: {self._format_bytes(mem.used)} ({mem.percent}%)"
            )
        except Exception as e:
            self.memory_info = f"Error getting memory info: {e}"

        # Disk Info
        try:
            disks = []
            partitions = psutil.disk_partitions(all=False)
            for part in partitions:
                # Filter out some common non-physical disks on Linux/Android
                if kivy_platform in ['linux', 'android']:
                    if any(part.mountpoint.startswith(p) for p in ['/proc', '/sys', '/dev', '/run', '/var/lib']):
                        continue

                if platform.system() == 'Windows' and 'cdrom' in part.opts:
                    continue

                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    disks.append({
                        'device': part.device,
                        'mountpoint': part.mountpoint,
                        'fstype': part.fstype,
                        'total': self._format_bytes(usage.total),
                        'used': self._format_bytes(usage.used),
                        'free': self._format_bytes(usage.free),
                        'percent': f"{usage.percent}%"
                    })
                except (PermissionError, OSError):
                    continue
            self.disk_data = disks
        except Exception as e:
            # If we fail to get partitions, at least try to get root
            try:
                usage = psutil.disk_usage('/')
                self.disk_data = [{
                    'device': 'root',
                    'mountpoint': '/',
                    'fstype': 'N/A',
                    'total': self._format_bytes(usage.total),
                    'used': self._format_bytes(usage.used),
                    'free': self._format_bytes(usage.free),
                    'percent': f"{usage.percent}%"
                }]
            except Exception:
                pass

    def _format_bytes(self, n):
        for unit in ['', 'K', 'M', 'G', 'T', 'P']:
            if n < 1024:
                return f"{n:.2f} {unit}B"
            n /= 1024
        return f"{n:.2f} PB"
