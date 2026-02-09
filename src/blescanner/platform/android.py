
import asyncio
import logging
import threading
from typing import List, Callable, Tuple

from jnius import autoclass, cast

from .base import PlatformUtilsBase, BondedDevice, SerialPort, WifiAccessPoint

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

    def get_local_ip_and_mask(self) -> Tuple[str, str]:
        """
        Retrieves the local IP address and netmask on Android using JNI.
        """
        try:
            Context = autoclass('android.content.Context')
            WifiManager = autoclass('android.net.wifi.WifiManager')
            activity = PythonActivity.mActivity
            wifi_manager = activity.getSystemService(Context.WIFI_SERVICE)
            dhcp_info = wifi_manager.getDhcpInfo()

            ip_int = dhcp_info.ipAddress
            mask_int = dhcp_info.netmask

            def int_to_ip(i):
                return f"{i & 0xFF}.{(i >> 8) & 0xFF}.{(i >> 16) & 0xFF}.{(i >> 24) & 0xFF}"

            ip = int_to_ip(ip_int)
            mask = int_to_ip(mask_int)

            if ip == "0.0.0.0":
                # Try another way if WiFi dhcp info is not available
                import socket
                import psutil
                for interface, addrs in psutil.net_if_addrs().items():
                    for addr in addrs:
                        if addr.family == socket.AF_INET and not addr.address.startswith("127."):
                            return addr.address, addr.netmask

            return ip, mask
        except Exception as e:
            logger.error(f"Error getting IP on Android: {e}")
            import socket
            import psutil
            for interface, addrs in psutil.net_if_addrs().items():
                for addr in addrs:
                    if addr.family == socket.AF_INET and not addr.address.startswith("127."):
                        return addr.address, addr.netmask
            return None, None

    def get_arp_table(self) -> dict:
        """
        Retrieves the ARP table by reading /proc/net/arp on Android.
        """
        arp_table = {}
        try:
            with open("/proc/net/arp", "r") as f:
                next(f)
                for line in f:
                    parts = line.split()
                    if len(parts) >= 4:
                        ip = parts[0]
                        mac = parts[3]
                        if mac != "00:00:00:00:00:00":
                            arp_table[ip] = mac.lower()
        except Exception as e:
            logger.error(f"Error reading ARP table on Android: {e}")
        return arp_table

    async def scan_wifi(self) -> List[WifiAccessPoint]:
        """
        Scans for available Wi-Fi access points on Android using WifiManager.
        """
        aps = []
        try:
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            Context = autoclass('android.content.Context')
            activity = PythonActivity.mActivity
            wifi_manager = activity.getSystemService(Context.WIFI_SERVICE)

            # Trigger a scan (might be throttled)
            try:
                wifi_manager.startScan()
            except Exception:
                pass

            # Wait a bit for scan to complete or just get current results
            scan_results = wifi_manager.getScanResults()
            for i in range(scan_results.size()):
                res = scan_results.get(i)

                # Derive channel from frequency
                freq = res.frequency
                channel = 0
                if 2412 <= freq <= 2484:
                    channel = (freq - 2407) // 5
                elif 5170 <= freq <= 5825:
                    channel = (freq - 5000) // 5

                aps.append(WifiAccessPoint(
                    ssid=str(res.SSID).strip('"'),
                    bssid=str(res.BSSID).lower(),
                    rssi=int(res.level),
                    channel=channel,
                    frequency=freq,
                    security=str(res.capabilities)
                ))
        except Exception as e:
            logger.error(f"Error scanning Wi-Fi on Android: {e}")
        return aps

    def list_serial_ports(self) -> List[SerialPort]:
        """
        Lists available serial ports using the usb-serial-for-android library.
        """
        try:
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            Context = autoclass('android.content.Context')
            UsbManager = autoclass('android.hardware.usb.UsbManager')
            UsbSerialProber = autoclass('com.hoho.android.usbserial.driver.UsbSerialProber')

            # Get the UsbManager from the current activity
            activity = PythonActivity.mActivity
            usb_manager = activity.getSystemService(Context.USB_SERVICE)

            # Find all available drivers from the prober
            prober = UsbSerialProber.getDefaultProber()
            drivers = prober.findAllDrivers(usb_manager)

            ports = []
            for driver in drivers:
                device = driver.getDevice()
                ports.append(
                    SerialPort(
                        device=f"usb{device.getDeviceId()}",
                        description=f"{device.getProductName()} (VID:{device.getVendorId()} PID:{device.getProductId()})"
                    )
                )
            logger.debug(f"Found serial ports: {ports}")
            return ports
        except Exception as e:
            logger.error(f"Error listing serial ports on Android: {e}")
            # The Java class might not be found if the library is not included
            logger.error("Make sure the usb-serial-for-android library is included in the build.")
            return []

    async def create_serial_connection(
        self,
        loop: asyncio.AbstractEventLoop,
        protocol_factory: Callable[[], asyncio.Protocol],
        url: str,
        **kwargs
    ) -> Tuple[asyncio.Transport, asyncio.Protocol]:
        """
        Creates a serial connection for Android using the usb-serial-for-android library.
        """
        logger.info(f"Attempting to connect to {url} with args {kwargs}")
        try:
            # JNI class imports
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            Context = autoclass('android.content.Context')
            UsbManager = autoclass('android.hardware.usb.UsbManager')
            UsbSerialProber = autoclass('com.hoho.android.usbserial.driver.UsbSerialProber')
            # Note: A custom permission request flow might be needed for production
            # PendingIntent = autoclass('android.app.PendingIntent')
            # Intent = autoclass('android.content.Intent')

            activity = PythonActivity.mActivity
            usb_manager = activity.getSystemService(Context.USB_SERVICE)

            # Find the target device by parsing the URL (e.g., "usb1002")
            try:
                device_id = int(url.replace("usb", ""))
            except (ValueError, TypeError):
                raise ValueError(f"Invalid serial port URL for Android: {url}")

            target_driver = None
            prober = UsbSerialProber.getDefaultProber()
            for driver in prober.findAllDrivers(usb_manager):
                if driver.getDevice().getDeviceId() == device_id:
                    target_driver = driver
                    break

            if not target_driver:
                raise ConnectionError(f"USB device for {url} not found.")

            # --- Permission Handling (Simplified) ---
            # In a real app, a BroadcastReceiver would be needed to handle the result
            # of requestPermission asynchronously. For now, we hope it's pre-approved.
            if not usb_manager.hasPermission(target_driver.getDevice()):
                 logger.warning(f"App does not have permission for {url}. Connection may fail.")
                 # usb_manager.requestPermission(target_driver.getDevice(), ...) # Requires PendingIntent

            connection = usb_manager.openDevice(target_driver.getDevice())
            if not connection:
                raise ConnectionError(f"Failed to open USB device connection for {url}.")

            # Use the first port of the driver
            port = target_driver.getPorts().get(0)
            port.open(connection)

            # Set serial parameters
            stopbits_map = {1: 1, 1.5: 3, 2: 2}  # pyserial -> usb-serial-for-android
            parity_map = {'N': 0, 'E': 2, 'O': 1, 'M': 3, 'S': 4}  # pyserial -> usb-serial-for-android

            port.setParameters(
                kwargs.get('baudrate', 115200),
                kwargs.get('bytesize', 8),
                stopbits_map.get(kwargs.get('stopbits', 1), 1),
                parity_map.get(kwargs.get('parity', 'N'), 0)
            )

            protocol = protocol_factory()
            transport = AndroidSerialTransport(loop, protocol, port)
            loop.call_soon(protocol.connection_made, transport)

            logger.info(f"Successfully connected to {url}")
            return transport, protocol

        except Exception as e:
            logger.error(f"Failed to create Android serial connection: {e}")
            raise


class AndroidSerialTransport(asyncio.Transport):
    """
    An asyncio.Transport implementation for the Android USB serial library.
    """

    def __init__(self, loop: asyncio.AbstractEventLoop, protocol: asyncio.Protocol, java_port):
        super().__init__()
        self._loop = loop
        self._protocol = protocol
        self._java_port = java_port
        self._closing = False
        self._read_thread = threading.Thread(target=self._read_loop, daemon=True)
        self._read_thread.start()

    def _read_loop(self):
        """Continuously reads from the serial port in a separate thread."""
        read_buffer = bytearray(4096)
        j_buffer = autoclass('java.nio.ByteBuffer').wrap(read_buffer)

        while not self._closing:
            try:
                num_bytes_read = self._java_port.read(j_buffer.array(), 200) # 200ms timeout
                if num_bytes_read > 0:
                    data = bytes(read_buffer[:num_bytes_read])
                    self._loop.call_soon_threadsafe(self._protocol.data_received, data)
            except Exception as e:
                logger.error(f"Error in Android serial read loop: {e}")
                self._loop.call_soon_threadsafe(self._protocol.connection_lost, e)
                break
        logger.info("Android serial read loop terminated.")

    def write(self, data: bytes):
        """Writes data to the serial port."""
        if self._closing:
            return
        try:
            self._java_port.write(data, 200) # 200ms timeout
        except Exception as e:
            logger.error(f"Error writing to Android serial port: {e}")
            self._loop.call_soon_threadsafe(self._protocol.connection_lost, e)

    def is_closing(self):
        """Returns True if the transport is closing."""
        return self._closing

    def close(self):
        """Closes the serial port and stops the read thread."""
        if self._closing:
            return
        self._closing = True
        try:
            self._java_port.close()
            logger.info("Android serial port closed.")
        except Exception as e:
            logger.error(f"Error closing Android serial port: {e}")
        finally:
            self._loop.call_soon_threadsafe(self._protocol.connection_lost, None)

    def abort(self):
        """Aborts the connection."""
        self.close()
