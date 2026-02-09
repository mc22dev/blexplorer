import asyncio
import math
from kivy.uix.screenmanager import Screen
from kivy.properties import ListProperty, StringProperty, NumericProperty, BooleanProperty, DictProperty
from kivy.clock import Clock
from kivy.uix.widget import Widget
from kivy.graphics import Color, Line
from kivy.app import App
import colorsys

class WifiGraph(Widget):
    aps = ListProperty([])
    min_freq = NumericProperty(2400)
    max_freq = NumericProperty(2500)
    rssi_min = NumericProperty(-100)
    rssi_max = NumericProperty(-20)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(aps=self.update_graph, size=self.update_graph, pos=self.update_graph,
                  min_freq=self.update_graph, max_freq=self.update_graph)
        self._device_colors = {}
        self._hue_iterator = 0.0

    def get_ap_color(self, bssid):
        if bssid not in self._device_colors:
            rgb = colorsys.hsv_to_rgb(self._hue_iterator, 0.8, 1.0)
            self._device_colors[bssid] = tuple(rgb)
            self._hue_iterator = (self._hue_iterator + 0.23) % 1.0
        return self._device_colors[bssid]

    def update_graph(self, *args):
        self.canvas.after.clear()

        padding_left = 50
        padding_bottom = 40
        padding_top = 20
        padding_right = 20

        graph_x = self.x + padding_left
        graph_y = self.y + padding_bottom
        graph_width = self.width - padding_left - padding_right
        graph_height = self.height - padding_bottom - padding_top

        if graph_width <= 0 or graph_height <= 0:
            return

        with self.canvas.after:
            # Draw grid
            Color(1, 1, 1, 0.1)
            # Y-axis (RSSI) grid and labels
            for i in range(self.rssi_min, self.rssi_max + 1, 10):
                y_ratio = (i - self.rssi_min) / (self.rssi_max - self.rssi_min)
                y = graph_y + y_ratio * graph_height
                Line(points=[graph_x, y, graph_x + graph_width, y], width=0.5)

            # X-axis (Freq) grid
            step = 20 if (self.max_freq - self.min_freq) < 200 else 100
            for f in range(int(self.min_freq), int(self.max_freq) + 1, step):
                x_ratio = (f - self.min_freq) / (self.max_freq - self.min_freq)
                x = graph_x + x_ratio * graph_width
                Line(points=[x, graph_y, x, graph_y + graph_height], width=0.5)

            # Draw axes
            Color(1, 1, 1, 0.6)
            Line(points=[graph_x, graph_y, graph_x + graph_width, graph_y], width=1)
            Line(points=[graph_x, graph_y, graph_x, graph_y + graph_height], width=1)

            if not self.aps:
                return

            # Draw curves for each AP
            for ap in self.aps:
                if not (self.min_freq <= ap.frequency <= self.max_freq):
                    continue

                color = self.get_ap_color(ap.bssid)
                Color(*color, 0.7)

                # Center point
                cx_ratio = (ap.frequency - self.min_freq) / (self.max_freq - self.min_freq)
                cx = graph_x + cx_ratio * graph_width

                cy_ratio = (ap.rssi - self.rssi_min) / (self.rssi_max - self.rssi_min)
                cy_ratio = max(0, min(1, cy_ratio))
                cy = graph_y + cy_ratio * graph_height

                # Width of the curve
                w_mhz = 22
                w_ratio = w_mhz / (self.max_freq - self.min_freq)
                w_px = w_ratio * graph_width

                points = []
                num_segments = 30
                for i in range(num_segments + 1):
                    rx = -1 + (2 * i / num_segments)
                    px = cx + rx * (w_px / 2)

                    # Ensure we don't draw outside the graph area horizontally
                    if px < graph_x: continue
                    if px > graph_x + graph_width: continue

                    # Simple parabola-like shape
                    ry = 1 - rx*rx
                    if ry < 0: ry = 0

                    py = graph_y + (cy - graph_y) * ry
                    points.extend([px, py])

                if len(points) >= 4:
                    Line(points=points, width=1.5)

class WifiScannerScreen(Screen):
    is_scanning = BooleanProperty(False)
    aps = ListProperty([])
    band = StringProperty("2.4GHz")
    status_text = StringProperty("Ready")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._scan_task = None

    def toggle_scan(self):
        if self.is_scanning:
            self.stop_scan()
        else:
            self.start_scan()

    def start_scan(self):
        if self.is_scanning: return
        self.is_scanning = True
        self.status_text = "Scanning..."
        self._scan_task = asyncio.create_task(self._async_scan_loop())

    def stop_scan(self):
        self.is_scanning = False
        self.status_text = "Stopped"
        if self._scan_task:
            self._scan_task.cancel()
            self._scan_task = None

    async def _async_scan_loop(self):
        app = App.get_running_app()
        try:
            while self.is_scanning:
                new_aps = await app.platform_utils.scan_wifi()
                self.aps = new_aps
                self.status_text = f"Last scan: {len(new_aps)} APs found"
                await asyncio.sleep(5)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Wifi scan loop error: {e}")
            self.status_text = f"Error: {e}"
            self.is_scanning = False

    def on_band(self, instance, value):
        if value == "2.4GHz":
            self.ids.wifi_graph.min_freq = 2400
            self.ids.wifi_graph.max_freq = 2500
        else:
            self.ids.wifi_graph.min_freq = 5100
            self.ids.wifi_graph.max_freq = 5900

    def on_leave(self):
        self.stop_scan()
