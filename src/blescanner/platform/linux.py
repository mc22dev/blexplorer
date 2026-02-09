
import logging
from typing import List, Callable

from dbus_fast import Variant
from dbus_fast.aio import MessageBus

from .base import BondedDevice, WifiAccessPoint
from .default import DefaultPlatformUtils

logger = logging.getLogger(__name__)


class LinuxPlatformUtils(DefaultPlatformUtils):
    """
    Utility class for handling Linux-specific operations.
    """

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

    def get_arp_table(self) -> dict:
        """
        Retrieves the ARP table by reading /proc/net/arp on Linux.
        """
        arp_table = {}
        try:
            with open("/proc/net/arp", "r") as f:
                # Skip header
                next(f)
                for line in f:
                    parts = line.split()
                    if len(parts) >= 4:
                        ip = parts[0]
                        mac = parts[3]
                        if mac != "00:00:00:00:00:00":
                            arp_table[ip] = mac.lower()
        except Exception as e:
            logger.error(f"Error reading ARP table on Linux: {e}")
            # Fallback to default
            return super().get_arp_table()
        return arp_table

    async def scan_wifi(self) -> List[WifiAccessPoint]:
        """
        Scans for available Wi-Fi access points on Linux using nmcli.
        """
        import asyncio
        import re

        aps = []
        try:
            # -t: terse output, -f: fields, device wifi list: list wifi APs
            cmd = ["nmcli", "-t", "-f", "SSID,BSSID,SIGNAL,CHAN,FREQ,SECURITY", "device wifi list"]
            process = await asyncio.create_subprocess_exec(*cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                logger.debug(f"nmcli failed or not available: {stderr.decode()}")
                return []

            output = stdout.decode("utf-8")
            for line in output.splitlines():
                if not line:
                    continue
                # nmcli terse output uses ':' as separator, but BSSID also contains ':'
                # and SSID might contain ':' too.
                # nmcli -t escapes ':' with '\'.

                parts = []
                current_part = ""
                i = 0
                while i < len(line):
                    if line[i] == '\\' and i + 1 < len(line) and line[i+1] == ':':
                        current_part += ':'
                        i += 2
                    elif line[i] == ':':
                        parts.append(current_part)
                        current_part = ""
                        i += 1
                    else:
                        current_part += line[i]
                        i += 1
                parts.append(current_part)

                if len(parts) >= 6:
                    ssid = parts[0]
                    bssid = parts[1]
                    try:
                        signal = int(parts[2])
                        # Convert signal percentage to dBm roughly
                        rssi = (signal / 2) - 100
                    except ValueError:
                        rssi = -100

                    try:
                        channel = int(parts[3])
                    except ValueError:
                        channel = 0

                    try:
                        # Frequency might be like "2437 MHz"
                        freq_str = parts[4].split()[0]
                        frequency = int(freq_str)
                    except (ValueError, IndexError):
                        frequency = 0

                    security = parts[5]

                    aps.append(WifiAccessPoint(
                        ssid=ssid,
                        bssid=bssid,
                        rssi=int(rssi),
                        channel=channel,
                        frequency=frequency,
                        security=security
                    ))
        except FileNotFoundError:
            logger.debug("nmcli not found.")
        except Exception as e:
            logger.error(f"Error scanning Wi-Fi on Linux: {e}")

        return aps
