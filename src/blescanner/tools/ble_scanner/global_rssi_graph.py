from kivy.uix.floatlayout import FloatLayout
from kivy.properties import DictProperty, NumericProperty
from kivy.uix.label import Label
from kivy.graphics import Color, Line
from kivy.clock import Clock
import colorsys
import math

class GlobalRSSIGraph(FloatLayout):
    """A widget to display a line graph of RSSI values for multiple devices."""
    device_data = DictProperty({})
    rssi_min = NumericProperty(-110)
    rssi_max = NumericProperty(-20)
    _device_colors = {}
    _hue_iterator = 0.0
    _y_labels = []

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(pos=self.update_graph, size=self.update_graph, device_data=self.update_graph,
                  rssi_min=self.update_graph, rssi_max=self.update_graph)
        self.duration_label = Label(text="0s", font_size='10sp', size_hint=(None, None), color=(1, 1, 1, 0.5))
        self.add_widget(self.duration_label)
        Clock.schedule_once(self.create_y_labels)

    def create_y_labels(self, *args):
        """Creates the Y-axis labels based on the RSSI range."""
        for label in self._y_labels:
            self.remove_widget(label)
        self._y_labels.clear()

        for i in range(self.rssi_min, self.rssi_max + 1, 10):
            label = Label(text=str(i), font_size='10sp', size_hint=(None, None), color=(1, 1, 1, 0.5))
            self.add_widget(label)
            self._y_labels.append(label)
        self.update_graph()

    def on_rssi_min(self, instance, value):
        self.create_y_labels()

    def on_rssi_max(self, instance, value):
        self.create_y_labels()

    def get_device_color(self, address):
        """Assigns a unique, bright color to each device address."""
        if address not in self._device_colors:
            rgb = colorsys.hsv_to_rgb(self._hue_iterator, 0.9, 1.0)
            self._device_colors[address] = tuple(rgb)
            self._hue_iterator = (self._hue_iterator + 0.17) % 1.0
        return self._device_colors[address]

    def clear_graph(self):
        """Clears all data and resets the graph."""
        self.device_data = {}
        self._device_colors = {}
        self._hue_iterator = 0.0
        self.update_graph()

    def update_graph(self, *args):
        """Positions labels and draws the graph for all devices."""
        self.canvas.after.clear()

        padding = 2
        label_width = 30
        graph_x = self.x + label_width + padding
        graph_y = self.y + padding
        graph_width = self.width - label_width - (padding * 2)
        graph_height = self.height - (padding * 2)

        if graph_width <= 0 or graph_height <= 0:
            return

        # Update Y-labels positions
        for label in self._y_labels:
            rssi_val = int(label.text)
            y_ratio = (rssi_val - self.rssi_min) / (self.rssi_max - self.rssi_min)
            y = graph_y + y_ratio * graph_height
            label.pos = (self.x + padding, y - label.height / 2)

        all_timestamps = [ts for data in self.device_data.values() for ts in data['timestamps']]
        if not all_timestamps:
            self.duration_label.text = "0s"
            self.duration_label.texture_update()
            self.duration_label.pos = (self.right - self.duration_label.texture_size[0] - padding, self.y + padding)
            return

        min_time = min(all_timestamps)
        max_time = max(all_timestamps)
        total_duration = max_time - min_time

        self.duration_label.text = f"{total_duration:.1f}s"
        self.duration_label.texture_update()
        self.duration_label.pos = (self.right - self.duration_label.texture_size[0] - padding, self.y + padding)

        with self.canvas.after:
            # Draw axis lines and grid
            Color(1, 1, 1, 0.3)
            Line(points=[graph_x, graph_y, graph_x + graph_width, graph_y], width=1)  # X-axis
            Line(points=[graph_x, graph_y, graph_x, graph_y + graph_height], width=1)  # Y-axis

            # Grid lines
            grid_color = (1, 1, 1, 0.1)
            for label in self._y_labels:
                Color(*grid_color)
                Line(points=[graph_x, label.center_y, graph_x + graph_width, label.center_y], width=1)

            if total_duration > 0:
                num_vertical_lines = 10
                for i in range(1, num_vertical_lines):
                    x = graph_x + (i / num_vertical_lines) * graph_width
                    Color(*grid_color)
                    Line(points=[x, graph_y, x, graph_y + graph_height], width=1)

            for address, data in self.device_data.items():
                rssi_values = data['rssi']
                timestamps = data['timestamps']

                if len(rssi_values) < 2:
                    continue

                Color(*self.get_device_color(address))
                points = []

                if total_duration == 0:
                    continue

                for rssi, timestamp in zip(rssi_values, timestamps):
                    time_offset = timestamp - min_time
                    x_ratio = time_offset / total_duration
                    x = graph_x + (x_ratio * graph_width)

                    normalized_rssi = (rssi - self.rssi_min) / (self.rssi_max - self.rssi_min)
                    normalized_rssi = max(0, min(1, normalized_rssi))
                    y = graph_y + normalized_rssi * graph_height

                    points.extend([x, y])

                Line(points=points, width=1.5)
