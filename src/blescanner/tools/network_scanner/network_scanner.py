import asyncio
import socket
import ipaddress
import math
import logging
try:
    import psutil
except ImportError:
    psutil = None

from kivy.uix.screenmanager import Screen
from kivy.properties import ListProperty, StringProperty, NumericProperty, BooleanProperty, ObjectProperty
from kivy.clock import Clock
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup
from kivy.uix.button import Button
from kivy.uix.widget import Widget
from kivy.graphics import Color, Line, Ellipse
from kivy.app import App
from kivy.lang import Builder

from blescanner.platform import platform_utils
try:
    from scapy.data import MANUFDB
except ImportError:
    MANUFDB = None

logger = logging.getLogger(__name__)

class DeviceNode(BoxLayout):
    ip = StringProperty("")
    mac = StringProperty("")
    manufacturer = StringProperty("")
    is_local = BooleanProperty(False)

class NetworkGraph(Widget):
    devices = ListProperty([])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(devices=self.update_graph, size=self.update_graph, pos=self.update_graph)

    def update_graph(self, *args):
        self.canvas.before.clear()
        self.clear_widgets()
        if not self.devices:
            return

        center_x, center_y = self.center

        local_device = next((d for d in self.devices if d.get('is_local')), None)
        other_devices = [d for d in self.devices if not d.get('is_local')]

        num_others = len(other_devices)
        # Adjust radius based on number of devices to avoid clutter
        base_radius = min(self.width, self.height) * 0.35
        radius = base_radius if num_others < 10 else base_radius * 1.2

        with self.canvas.before:
            Color(0.5, 0.5, 0.5, 0.3)
            for i, dev in enumerate(other_devices):
                angle = (2 * math.pi * i / num_others) if num_others > 0 else 0
                dx = center_x + radius * math.cos(angle)
                dy = center_y + radius * math.sin(angle)
                Line(points=[center_x, center_y, dx, dy], width=1)

        if local_device:
            node = DeviceNode(
                ip=local_device['ip'],
                mac=local_device['mac'],
                manufacturer="Local Host",
                is_local=True
            )
            node.size_hint = (None, None)
            node.size = ("140dp", "90dp")
            node.center = (center_x, center_y)
            self.add_widget(node)

        for i, dev in enumerate(other_devices):
            angle = (2 * math.pi * i / num_others) if num_others > 0 else 0
            dx = center_x + radius * math.cos(angle)
            dy = center_y + radius * math.sin(angle)

            node = DeviceNode(
                ip=dev['ip'],
                mac=dev['mac'],
                manufacturer=dev['manuf']
            )
            node.size_hint = (None, None)
            node.size = ("140dp", "90dp")
            node.center = (dx, dy)
            self.add_widget(node)

    def on_touch_down(self, touch):
        # We handle double tap on children manually if needed,
        # but Kivy widgets in a FloatLayout/Widget will get the touch.
        return super().on_touch_down(touch)

class NetworkScannerScreen(Screen):
    scan_progress = NumericProperty(0)
    is_scanning = BooleanProperty(False)
    discovered_devices = ListProperty([])
    status_text = StringProperty("Ready to scan")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.scan_task = None

    def start_scan(self):
        if self.is_scanning:
            return
        self.is_scanning = True
        self.discovered_devices = []
        self.scan_progress = 0
        self.status_text = "Finding local network..."
        self.scan_task = asyncio.create_task(self.async_scan())

    async def async_scan(self):
        try:
            ip, mask = platform_utils.get_local_ip_and_mask()
            if not ip:
                self.status_text = "Error: Local IP not found"
                self.is_scanning = False
                return

            if not mask:
                mask = "255.255.255.0" # Default to /24

            self.status_text = f"Scanning network {ip}/{mask}..."
            network = ipaddress.IPv4Network(f"{ip}/{mask}", strict=False)
            hosts = list(network.hosts())

            # Use only a subset if network is too large for a quick demo
            # But the requirement says "all computers and devices"
            # For /24 it's 254 hosts, which is fine.
            if len(hosts) > 512:
                 logger.warning("Large network detected. Scanning might be slow.")

            local_mac = "N/A"
            if psutil:
                for interface, addrs in psutil.net_if_addrs().items():
                    found_ip = False
                    for addr in addrs:
                        if addr.address == ip:
                            found_ip = True
                            break
                    if found_ip:
                        for addr in addrs:
                            if hasattr(socket, 'AF_PACKET') and addr.family == socket.AF_PACKET:
                                local_mac = addr.address
                                break
                            elif hasattr(psutil, 'AF_LINK') and addr.family == psutil.AF_LINK:
                                local_mac = addr.address
                                break
                        break

            self.discovered_devices = [{'ip': ip, 'mac': local_mac, 'manuf': 'This Device', 'is_local': True}]

            # Discovery: We'll ping all hosts concurrently
            sem = asyncio.Semaphore(100)

            async def check_host(host_ip):
                async with sem:
                    host_str = str(host_ip)
                    if host_str == ip:
                        return None

                    # Try a very quick TCP connection to common ports
                    ports = [80, 443, 22, 135, 445]
                    for port in ports:
                        try:
                            reader, writer = await asyncio.wait_for(
                                asyncio.open_connection(host_str, port), timeout=0.3
                            )
                            writer.close()
                            await writer.wait_closed()
                            return host_str
                        except:
                            continue

                    # Also check ARP table - even if ports are closed,
                    # if it's in ARP table and not "incomplete", it's likely there.
                    # Touching an IP (even if it fails) usually populates the ARP table if it's alive.
                    try:
                        # Dummy connection to trigger ARP
                        # Use run_in_executor to avoid blocking the main thread
                        loop = asyncio.get_running_loop()
                        def touch():
                            try:
                                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                                sock.settimeout(0.1)
                                sock.connect_ex((host_str, 1))
                                sock.close()
                            except:
                                pass
                        await loop.run_in_executor(None, touch)
                    except:
                        pass

                    arp_table = platform_utils.get_arp_table()
                    if host_str in arp_table:
                        return host_str
                return None

            total_hosts = len(hosts)
            tasks = [check_host(h) for h in hosts]

            completed = 0
            for future in asyncio.as_completed(tasks):
                res = await future
                completed += 1
                self.scan_progress = completed / total_hosts * 100

                if res:
                    arp_table = platform_utils.get_arp_table()
                    mac = arp_table.get(res, "Unknown")
                    if not any(d['ip'] == res for d in self.discovered_devices):
                        manuf = "Unknown"
                        if MANUFDB and mac != "Unknown":
                            try:
                                manuf = MANUFDB.get_manuf(mac) or "Unknown"
                            except:
                                pass
                        self.discovered_devices.append({
                            'ip': res,
                            'mac': mac,
                            'manuf': manuf,
                            'is_local': False
                        })

            self.status_text = f"Scan complete. Found {len(self.discovered_devices)} devices."
        except Exception as e:
            logger.error(f"Network scan error: {e}")
            self.status_text = f"Scan error: {str(e)}"
        finally:
            self.is_scanning = False

    def show_port_scan(self, ip):
        content = PortScanPopup(ip=ip)
        self._port_popup = Popup(title=f"Port Scan: {ip}", content=content, size_hint=(0.9, 0.9))
        self._port_popup.open()
        content.start_scan()

class PortScanPopup(BoxLayout):
    ip = StringProperty("")
    results = ListProperty([])
    progress = NumericProperty(0)
    is_scanning = BooleanProperty(False)
    status = StringProperty("Initializing...")

    def start_scan(self):
        self.is_scanning = True
        self.results = []
        asyncio.create_task(self.async_port_scan())

    async def async_port_scan(self):
        tcp_ports = [
            21, 22, 23, 25, 53, 80, 110, 135, 139, 143, 443, 445, 993, 995,
            1723, 3306, 3389, 5432, 5900, 8000, 8080, 8443
        ]
        udp_ports = [
            53, 67, 68, 69, 123, 161, 162, 443, 500, 514, 520, 1900, 4500, 5353
        ]

        total = len(tcp_ports) + len(udp_ports)
        count = 0

        self.status = "Scanning TCP ports..."
        sem = asyncio.Semaphore(10)

        async def scan_tcp(port):
            nonlocal count
            async with sem:
                try:
                    reader, writer = await asyncio.wait_for(
                        asyncio.open_connection(self.ip, port), timeout=1.5
                    )
                    service = "Unknown"
                    try:
                        service = socket.getservbyport(port, "tcp")
                    except:
                        pass
                    self.results.append({
                        'port': str(port),
                        'proto': 'TCP',
                        'service': service,
                        'status': 'Open'
                    })
                    writer.close()
                    await writer.wait_closed()
                except:
                    pass
                count += 1
                self.progress = count / total * 100

        await asyncio.gather(*(scan_tcp(p) for p in tcp_ports))

        self.status = "Scanning UDP ports (Probing)..."
        async def scan_udp(port):
            nonlocal count
            async with sem:
                try:
                    loop = asyncio.get_running_loop()
                    def probe():
                        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                        sock.settimeout(1.0)
                        try:
                            # DNS probe for port 53
                            p = b"\x12\x34\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00\x03www\x06google\x03com\x00\x00\x01\x00\x01" if port == 53 else b"\x00"
                            sock.sendto(p, (self.ip, port))
                            data, addr = sock.recvfrom(1024)
                            return True
                        except:
                            return False
                        finally:
                            sock.close()

                    is_open = await loop.run_in_executor(None, probe)
                    if is_open:
                        service = "Unknown"
                        try:
                            service = socket.getservbyport(port, "udp")
                        except:
                            pass
                        self.results.append({
                            'port': str(port),
                            'proto': 'UDP',
                            'service': service,
                            'status': 'Open'
                        })
                except:
                    pass
                count += 1
                self.progress = count / total * 100

        await asyncio.gather(*(scan_udp(p) for p in udp_ports))

        self.status = f"Finished. Found {len(self.results)} open ports."
        self.is_scanning = False
