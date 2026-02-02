from kivy.uix.floatlayout import FloatLayout
from kivy.properties import DictProperty
from kivy.uix.label import Label
from kivy.graphics import Color, Line, Rectangle
from kivy.app import App
import colorsys

class GlobalRSSIGraph(FloatLayout):
    """A widget to display a line graph of RSSI values for multiple devices."""
    device_data = DictProperty({})  # Format: { 'address': {'rssi': [], 'timestamps': []} }
    _device_colors = {}
    _hue_iterator = 0.0

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bind(pos=self.update_graph, size=self.update_graph, device_data=self.update_graph)

        self.max_label = Label(text="-30", font_size='10sp', size_hint=(None, None), color=(1,1,1,0.5))
        self.min_label = Label(text="-100", font_size='10sp', size_hint=(None, None), color=(1,1,1,0.5))
        self.duration_label = Label(text="0s", font_size='10sp', size_hint=(None, None), color=(1,1,1,0.5))
        self.add_widget(self.max_label)
        self.add_widget(self.min_label)
        self.add_widget(self.duration_label)

    def get_device_color(self, address):
        """Assigns a unique, bright color to each device address."""
        if address not in self._device_colors:
            rgb = colorsys.hsv_to_rgb(self._hue_iterator, 0.9, 1.0)
            self._device_colors[address] = tuple(rgb)
            self._hue_iterator = (self._hue_iterator + 0.17) % 1.0  # Use a prime fraction to cycle hues
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

        self.max_label.pos = (self.x + padding, self.top - self.max_label.texture_size[1] - padding)
        self.min_label.pos = (self.x + padding, self.y + padding)

        graph_x = self.x + label_width + padding
        graph_y = self.y + self.min_label.texture_size[1] + (padding * 2)
        graph_width = self.width - label_width - (padding * 2)
        graph_height = self.height - (self.max_label.texture_size[1] + self.min_label.texture_size[1]) - (padding * 4)

        if not self.device_data or graph_width <= 0 or graph_height <= 0:
            self.duration_label.text = "0s"
            self.duration_label.texture_update()
            self.duration_label.pos = (self.right - self.duration_label.texture_size[0] - padding, self.y + padding)
            self.min_label.text = "-100"
            self.max_label.text = "-30"
            return

        all_timestamps = [ts for data in self.device_data.values() for ts in data['timestamps']]
        all_rssi = [rssi for data in self.device_data.values() for rssi in data['rssi']]

        if not all_timestamps or not all_rssi:
            return

        # Dynamic Y-axis calculation
        min_rssi = min(all_rssi) - 5
        max_rssi = max(all_rssi) + 5
        self.min_label.text = f"{min_rssi}"
        self.max_label.text = f"{max_rssi}"

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
            num_horizontal_lines = 5
            num_vertical_lines = 10

            for i in range(1, num_horizontal_lines):
                y = graph_y + (i / num_horizontal_lines) * graph_height
                Color(*grid_color)
                Line(points=[graph_x, y, graph_x + graph_width, y], width=1)

            if total_duration > 0:
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

                    normalized_rssi = (rssi - min_rssi) / (max_rssi - min_rssi)
                    normalized_rssi = max(0, min(1, normalized_rssi))
                    y = graph_y + normalized_rssi * graph_height

                    points.extend([x, y])

                Line(points=points, width=1.5)
