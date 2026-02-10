import asyncio
import math
from kivy.uix.screenmanager import Screen
from kivy.properties import ListProperty, StringProperty, NumericProperty, BooleanProperty, DictProperty
from kivy.clock import Clock
from kivy.uix.widget import Widget
from kivy.uix.label import Label
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
        self._update_event = None
        self.bind(aps=self.schedule_update, size=self.schedule_update, pos=self.schedule_update,
                  min_freq=self.schedule_update, max_freq=self.schedule_update)
        self._device_colors = {}
        self._hue_iterator = 0.0
        self._channel_labels = []
        self._axis_label = None

    def schedule_update(self, *args):
        if self._update_event:
            self._update_event.cancel()
        self._update_event = Clock.schedule_once(self.update_graph, 0)

    def get_ap_color(self, bssid):
        if bssid not in self._device_colors:
            rgb = colorsys.hsv_to_rgb(self._hue_iterator, 0.8, 1.0)
            self._device_colors[bssid] = tuple(rgb)
            self._hue_iterator = (self._hue_iterator + 0.23) % 1.0
        return self._device_colors[bssid]

    def update_graph(self, *args):
        self.canvas.after.clear()
        self.clear_widgets()
        self._channel_labels.clear()
        self._axis_label = None

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

            # X-axis (Freq) grid and channel labels
            if self.aps:
                self._axis_label = Label(text="Channel", font_size='10sp', size_hint=(None, None), color=(1, 1, 1, 0.8), bold=True)
                self._axis_label.texture_update()
                self._axis_label.size = self._axis_label.texture_size
                self._axis_label.pos = (graph_x + graph_width/2 - self._axis_label.width/2, graph_y - dp(30))
                self.add_widget(self._axis_label)

            if self.min_freq < 3000: # 2.4GHz
                # Standard channels 1-13 (14 is rare)
                channels = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]
                for ch in channels:
                    f = 2412 + (ch - 1) * 5
                    x_ratio = (f - self.min_freq) / (self.max_freq - self.min_freq)
                    x = graph_x + x_ratio * graph_width
                    if graph_x <= x <= graph_x + graph_width:
                        Color(1, 1, 1, 0.1)
                        Line(points=[x, graph_y, x, graph_y + graph_height], width=0.5)

                        label = Label(text=str(ch), font_size='10sp', size_hint=(None, None), color=(1, 1, 1, 0.5))
                        label.texture_update()
                        label.size = label.texture_size
                        label.pos = (x - label.width/2, graph_y - dp(20))
                        self.add_widget(label)
                        self._channel_labels.append(label)
            else: # 5GHz
                # More channels, draw every 4 channels or so
                for ch in range(36, 166, 4):
                    f = 5000 + (ch * 5)
                    x_ratio = (f - self.min_freq) / (self.max_freq - self.min_freq)
                    x = graph_x + x_ratio * graph_width
                    if graph_x <= x <= graph_x + graph_width:
                        Color(1, 1, 1, 0.1)
                        Line(points=[x, graph_y, x, graph_y + graph_height], width=0.5)

                        label = Label(text=str(ch), font_size='10sp', size_hint=(None, None), color=(1, 1, 1, 0.5))
                        label.pos = (x - label.width/2, graph_y - 25)
                        self.add_widget(label)
                        self._channel_labels.append(label)

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
    ap_data = ListProperty([])
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
                self._update_ap_data()
                self.status_text = f"Last scan: {len(new_aps)} APs found"
                await asyncio.sleep(5)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Wifi scan loop error: {e}")
            self.status_text = f"Error: {e}"
            self.is_scanning = False

    def _update_ap_data(self):
        # Sort by is_connected (desc) then by rssi (desc)
        sorted_aps = sorted(self.aps, key=lambda x: (x.is_connected, x.rssi), reverse=True)

        self.ap_data = [
            {
                'text': (
                    f"{'[b][color=#55ff55]CONNECTED: [/color][/b]' if ap.is_connected else ''}"
                    f"[b]{ap.ssid or 'Hidden'}[/b] ({ap.bssid})\n"
                    f"Ch: {ap.channel} | {ap.frequency} MHz | [color=#ff5555]{ap.rssi} dBm[/color]\n"
                    f"Security: {ap.security} | Mode: {ap.mode} | Rate: {ap.rate}"
                )
            }
            for ap in sorted_aps
        ]

    def on_band(self, instance, value):
        if value == "2.4GHz":
            self.ids.wifi_graph.min_freq = 2400
            self.ids.wifi_graph.max_freq = 2500
        else:
            self.ids.wifi_graph.min_freq = 5100
            self.ids.wifi_graph.max_freq = 5900

    def on_leave(self):
        self.stop_scan()
