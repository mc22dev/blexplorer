from kivymd.uix.boxlayout import MDBoxLayout
from kivy.properties import ObjectProperty, StringProperty
from kivy.app import App
from kivy.core.clipboard import Clipboard
from kivymd.uix.dialog import MDDialog
from kivy.core.window import Window

class DeviceFrameKivy(MDBoxLayout):
    device = ObjectProperty(None)
    stats = ObjectProperty(None)

    device_name = StringProperty("Unknown")
    device_address = StringProperty("")
    rssi_info = StringProperty("")
    period_info = StringProperty("")
    adv_flags = StringProperty("")


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

        self.period_info = f"Period: {self.stats.avg_period:.2f} ms | Count: {len(self.stats.rssi_values)}"

        flags = []
        if self.device.details and hasattr(self.device.details, 'props') and self.device.details.props.get('Connectable'):
            flags.append("Connectable")

        # Heuristic for connectable based on advertisement data for other platforms
        elif self.stats.adv_data:
            # Typically, connectable devices have manufacturer data or service UUIDs
            if self.stats.adv_data.manufacturer_data or self.stats.adv_data.service_uuids:
                 flags.append("Connectable")

        self.adv_flags = "Flags: " + ", ".join(flags) if flags else "Flags: Not Connectable"


    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Trigger the on_... methods to populate the UI initially
        self.on_device(self, self.device)
        self.on_stats(self, self.stats)

    def copy_to_clipboard(self, text):
        Clipboard.copy(text)
        dialog = MDDialog(title='Copied',
                          text=f'"{text}" copied to clipboard.',
                          size_hint=(None, None), size=(300, 100))
        dialog.open()
