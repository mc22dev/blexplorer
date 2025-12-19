from kivy.uix.boxlayout import BoxLayout
from kivy.uix.behaviors import ButtonBehavior
from kivy.properties import ObjectProperty, StringProperty, BooleanProperty, ColorProperty
from kivy.app import App
from kivy.core.clipboard import Clipboard
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.core.window import Window

class DeviceFrameKivy(ButtonBehavior, BoxLayout):
    device = ObjectProperty(None)
    stats = ObjectProperty(None)
    is_selected = BooleanProperty(False)
    is_graph_selected = BooleanProperty(True)
    indicator_color = ColorProperty([0, 0, 0, 0])  # Default to transparent

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
        app = App.get_running_app()
        custom_name = app.config_manager.get_device_name(self.device.address)
        self.device_name = custom_name or self.device.name or "Unknown"
        self.device_address = self.device.address

    def on_stats(self, instance, value):
        """Handles updates to the statistics object."""
        if not self.stats:
            return

        self.rssi_info = (f"RSSI: {self.stats.adv_data.rssi} dBm "
                          f"(Min: {self.stats.min_rssi}, "
                          f"Max: {self.stats.max_rssi}, "
                          f"Avg: {self.stats.avg_rssi:.2f})")

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
        self.register_event_type('on_graph_selection_change')
        # Trigger the on_... methods to populate the UI initially
        self.on_device(self, self.device)
        self.on_stats(self, self.stats)

    def on_graph_selection_change(self, *args):
        """Event dispatched when the graph selection changes."""
        pass

    def toggle_graph_selection(self):
        """Toggles the selection for the graph."""
        self.is_graph_selected = not self.is_graph_selected
        self.dispatch('on_graph_selection_change', self.device.address, self.is_graph_selected)

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

    def save_custom_name(self, name):
        """Saves the custom name for the device."""
        app = App.get_running_app()
        app.config_manager.set_device_name(self.device.address, name)
        self.device_name = name
        popup = Popup(title='Saved',
                      content=Label(text=f'Name saved for {self.device.address}.'),
                      size_hint=(None, None), size=(300, 100))
        popup.open()
