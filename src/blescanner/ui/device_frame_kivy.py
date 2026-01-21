from kivy.uix.boxlayout import BoxLayout
from kivy.uix.behaviors import ButtonBehavior
from kivy.properties import ObjectProperty, StringProperty, BooleanProperty, ColorProperty
from kivy.core.clipboard import Clipboard
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.checkbox import CheckBox
from kivy.uix.button import Button
from kivy.core.window import Window

class DeviceFrameKivy(ButtonBehavior, BoxLayout):
    device = ObjectProperty(None)
    stats = ObjectProperty(None)
    is_selected = BooleanProperty(False)
    is_graph_selected = BooleanProperty(True)
    indicator_color = ColorProperty([0, 0, 0, 0])
    primary_color = ColorProperty([0, 0, 0, 0])
    secondary_color = ColorProperty([0, 0, 0, 0])

    device_name = StringProperty("Unknown")
    custom_device_name = StringProperty("")
    device_address = StringProperty("")
    rssi_info = StringProperty("")
    period_info = StringProperty("")
    adv_flags = StringProperty("")
    service_uuids = StringProperty("")
    manufacturer_data = StringProperty("")
    full_service_uuids = StringProperty("")
    full_manufacturer_data = StringProperty("")
    bond_state = StringProperty("")


    def on_device(self, instance, value):
        """Handles updates to the device object."""
        if self.config_manager:
            self.custom_device_name = self.config_manager.get_device_name(self.device.address) or ""
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


    def __init__(self, config_manager=None, bond_state="", **kwargs):
        self.config_manager = config_manager
        super().__init__(**kwargs)
        self.bond_state = bond_state
        self.register_event_type('on_graph_selection_change')
        self.register_event_type('on_connect_request')
        # Trigger the on_... methods to populate the UI initially
        self.on_device(self, self.device)
        self.on_stats(self, self.stats)

    def on_graph_selection_change(self, *args):
        """Event dispatched when the graph selection changes."""
        pass

    def on_connect_request(self, *args):
        """Event dispatched when the user wants to connect to the device."""
        pass

    def toggle_graph_selection(self):
        """Toggles the selection for the graph."""
        self.is_graph_selected = not self.is_graph_selected
        self.dispatch('on_graph_selection_change', self.device.address, self.is_graph_selected)

    def show_copy_popup(self):
        """Displays a popup to select what to copy."""
        content = BoxLayout(orientation='vertical', padding="8dp")

        options = {
            "device_name": "Device Name",
            "custom_device_name": "Custom Name",
            "device_address": "Device Address",
            "rssi_info": "RSSI Info",
            "period_info": "Period Info",
            "adv_flags": "Advertisement Flags",
            "full_service_uuids": "Service UUIDs",
            "full_manufacturer_data": "Manufacturer Data"
        }

        checkboxes = {}
        for key, text in options.items():
            if getattr(self, key):
                box = BoxLayout(orientation='horizontal', size_hint_y=None, height='30dp')
                box.add_widget(Label(text=text))
                chk = CheckBox()
                box.add_widget(chk)
                content.add_widget(box)
                checkboxes[key] = chk

        copy_button = Button(text="Copy", size_hint_y=None, height='44dp')

        def do_copy(instance):
            self._copy_selected_to_clipboard(checkboxes)
            popup.dismiss()

        copy_button.bind(on_release=do_copy)
        content.add_widget(copy_button)

        popup = Popup(title='Copy Device Info',
                      content=content,
                      size_hint=(0.8, 0.8))
        popup.open()

    def _copy_selected_to_clipboard(self, checkboxes):
        """Copies the selected device information to the clipboard."""
        to_copy = []
        for key, chk in checkboxes.items():
            if chk.active:
                to_copy.append(str(getattr(self, key)))

        text_to_copy = "\n".join(to_copy)
        Clipboard.copy(text_to_copy)

        popup = Popup(title='Copied',
                      content=Label(text=f'Selected info copied to clipboard.'),
                      size_hint=(None, None), size=(400, 100))
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
        if self.config_manager:
            self.config_manager.set_device_name(self.device.address, name)
        self.custom_device_name = name
        popup = Popup(title='Saved',
                      content=Label(text=f'Name saved for {self.device.address}.'),
                      size_hint=(None, None), size=(300, 100))
        popup.open()
