from kivy.uix.boxlayout import BoxLayout
from kivy.uix.behaviors import ButtonBehavior
from kivy.properties import ObjectProperty, StringProperty, BooleanProperty, ListProperty
from kivy.app import App
from kivy.core.clipboard import Clipboard
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.core.window import Window
from kivy.uix.widget import Widget
from kivy.graphics import Color, Line, Rectangle
from kivy.uix.floatlayout import FloatLayout


class RSSIGraph(FloatLayout):
    """A widget to display a simple line graph of RSSI values with scales."""
    rssi_values = ListProperty([])
    timestamps = ListProperty([])

    # Define fixed min/max for the Y-axis scale
    min_rssi = -100
    max_rssi = -30

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Use a single binding for all updates
        self.bind(pos=self.update_graph, size=self.update_graph,
                  rssi_values=self.update_graph, timestamps=self.update_graph)

        # Create labels for the scales
        self.max_label = Label(text=f"{self.max_rssi}", font_size='10sp', size_hint=(None, None))
        self.min_label = Label(text=f"{self.min_rssi}", font_size='10sp', size_hint=(None, None))
        self.duration_label = Label(text="0s", font_size='10sp', size_hint=(None, None))
        self.add_widget(self.max_label)
        self.add_widget(self.min_label)
        self.add_widget(self.duration_label)

    def update_graph(self, *args):
        """Positions the labels and draws the RSSI graph."""
        # We draw on canvas.after so the line is rendered after the labels (children)
        self.canvas.after.clear()

        # --- Position Labels ---
        padding = 2
        label_width = 30  # Reserve space for Y-axis labels

        # Y-axis labels (top and bottom left)
        self.max_label.pos = (self.x + padding, self.top - self.max_label.texture_size[1] - padding)
        self.min_label.pos = (self.x + padding, self.y + padding)

        # X-axis label (bottom right)
        duration = 0
        if len(self.timestamps) > 1:
            duration = self.timestamps[-1] - self.timestamps[0]
        self.duration_label.text = f"{duration:.1f}s"
        self.duration_label.texture_update() # Ensure size is calculated for pos
        self.duration_label.pos = (self.right - self.duration_label.texture_size[0] - padding, self.y + padding)

        # --- Draw Graph ---
        if not self.rssi_values or len(self.rssi_values) < 2:
            return

        with self.canvas.after:
            Color(*App.get_running_app().theme.primary)

            # Define the drawing area for the line, inset to not overlap labels
            graph_x = self.x + label_width + padding
            graph_y = self.y + self.min_label.texture_size[1] + (padding * 2)
            graph_width = self.width - label_width - (padding * 2)
            graph_height = self.height - (self.max_label.texture_size[1] + self.min_label.texture_size[1]) - (padding * 4)

            points = []
            total_duration = self.timestamps[-1] - self.timestamps[0]
            if total_duration == 0:
                return # Avoid division by zero if all timestamps are the same

            for i, (rssi, timestamp) in enumerate(zip(self.rssi_values, self.timestamps)):
                # X-coordinate based on time
                time_offset = timestamp - self.timestamps[0]
                x_ratio = time_offset / total_duration
                x = graph_x + (x_ratio * graph_width)

                # Normalize RSSI to fit graph height (0-1 range)
                normalized_rssi = (rssi - self.min_rssi) / (self.max_rssi - self.min_rssi)
                normalized_rssi = max(0, min(1, normalized_rssi)) # Clamp

                y = graph_y + normalized_rssi * graph_height
                points.extend([x, y])

            Line(points=points, width=1.2)


class DeviceFrameKivy(ButtonBehavior, BoxLayout):
    device = ObjectProperty(None)
    stats = ObjectProperty(None)
    is_selected = BooleanProperty(False)

    device_name = StringProperty("Unknown")
    device_address = StringProperty("")
    rssi_info = StringProperty("")
    period_info = StringProperty("")
    adv_flags = StringProperty("")
    service_uuids = StringProperty("")
    manufacturer_data = StringProperty("")
    full_service_uuids = StringProperty("")
    full_manufacturer_data = StringProperty("")


    def on_device(self, instance, value):
        """Handles updates to the device object."""
        self.device_name = self.device.name or "Unknown"
        self.device_address = self.device.address

    def on_stats(self, instance, value):
        """Handles updates to the statistics object."""
        if not self.stats:
            return

        self.rssi_info = (f"RSSI: {self.stats.adv_data.rssi} dBm "
                          f"(Min: {self.stats.min_rssi}, "
                          f"Max: {self.stats.max_rssi}, "
                          f"Avg: {self.stats.avg_rssi:.2f})")

        # Update the graph with the new RSSI and timestamp values
        if 'rssi_graph' in self.ids:
            self.ids.rssi_graph.rssi_values = self.stats.rssi_values
            self.ids.rssi_graph.timestamps = self.stats.timestamps

        self.period_info = (f"Period: {self.stats.last_period:.2f} ms "
                            f"(Min: {self.stats.min_period:.2f}, "
                            f"Max: {self.stats.max_period:.2f}, "
                            f"Avg: {self.stats.avg_period:.2f}) | "
                            f"Count: {len(self.stats.rssi_values)}")

        flags = []
        if self.device.details and hasattr(self.device.details, 'props') and self.device.details.props.get('Connectable'):
            flags.append("Connectable")

        # Heuristic for connectable based on advertisement data for other platforms
        elif self.stats.adv_data:
            # Typically, connectable devices have manufacturer data or service UUIDs
            if self.stats.adv_data.manufacturer_data or self.stats.adv_data.service_uuids:
                 flags.append("Connectable")

        self.adv_flags = "Flags: " + ", ".join(flags) if flags else "Flags: Not Connectable"

        self.service_uuids = ""
        self.full_service_uuids = ""
        if self.stats.adv_data.service_uuids:
            self.full_service_uuids = "Services: " + ", ".join(self.stats.adv_data.service_uuids)
            if len(self.full_service_uuids) > 30:
                self.service_uuids = self.full_service_uuids[:27] + "..."
            else:
                self.service_uuids = self.full_service_uuids

        self.manufacturer_data = ""
        self.full_manufacturer_data = ""
        if self.stats.adv_data.manufacturer_data:
            manu_data_str = []
            for company_id, data in self.stats.adv_data.manufacturer_data.items():
                manu_data_str.append(f"0x{company_id:04X}: {data.hex()}")
            self.full_manufacturer_data = "Manu: " + ", ".join(manu_data_str)
            if len(self.full_manufacturer_data) > 30:
                self.manufacturer_data = self.full_manufacturer_data[:27] + "..."
            else:
                self.manufacturer_data = self.full_manufacturer_data


    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Trigger the on_... methods to populate the UI initially
        self.on_device(self, self.device)
        self.on_stats(self, self.stats)

    def copy_to_clipboard(self, text):
        Clipboard.copy(text)
        popup = Popup(title='Copied',
                      content=Label(text=f'"{text}" copied to clipboard.'),
                      size_hint=(None, None), size=(300, 100))
        popup.open()

    def show_full_data_popup(self, title, data):
        """Displays a popup with the full data."""
        if not data:
            return
        popup = Popup(title=title,
                      content=Label(text=data),
                      size_hint=(0.8, 0.5))
        popup.open()
