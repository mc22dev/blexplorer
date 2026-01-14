
from typing import Dict, List, Tuple
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
from kivy.uix.boxlayout import BoxLayout
from device_frame_kivy import DeviceFrameKivy
from models import DeviceScanStats

class DeviceManager:
    """Manages discovered BLE devices and their UI representation."""

    def __init__(self, app_callback, ui_container: BoxLayout, config_manager, theme_manager):
        self.app_callback = app_callback
        self.ui_container = ui_container
        self.config_manager = config_manager
        self.theme_manager = theme_manager
        self.device_frames: Dict[str, DeviceFrameKivy] = {}
        self.scan_stats: Dict[str, DeviceScanStats] = {}
        self.graph_selection: Dict[str, bool] = {}
        self.global_graph_data: Dict[str, Dict] = {}
        self.discovered_devices_batch: List[Tuple[BLEDevice, AdvertisementData]] = []

    def clear(self):
        """Clears all device data and UI elements."""
        self.ui_container.clear_widgets()
        if 'scanner_screen' in self.app_callback.root.ids and 'global_rssi_graph' in self.app_callback.root.ids.scanner_screen.ids:
            self.app_callback.root.ids.scanner_screen.ids.global_rssi_graph.clear_graph()
        self.device_frames.clear()
        self.scan_stats.clear()
        self.graph_selection.clear()
        self.global_graph_data.clear()
        self.discovered_devices_batch.clear()

    def add_discovered_device(self, device: BLEDevice, adv_data: AdvertisementData):
        """Adds a discovered device to the batch for processing."""
        self.discovered_devices_batch.append((device, adv_data))

    def process_device_batch(self):
        """Processes the batch of discovered devices and updates the UI."""
        if not self.discovered_devices_batch:
            return

        sorted_batch = sorted(self.discovered_devices_batch, key=lambda x: x[1].rssi, reverse=True)
        for device, adv_data in sorted_batch:
            self._update_device_ui(device, adv_data)

        self.app_callback.update_graph_data()
        self.discovered_devices_batch.clear()

    def _update_device_ui(self, device: BLEDevice, adv_data: AdvertisementData):
        """Updates or creates a UI frame for a discovered device."""
        if device.address not in self.scan_stats:
            self.scan_stats[device.address] = DeviceScanStats()
            self.graph_selection[device.address] = True  # Default to selected

        stats = self.scan_stats[device.address]
        stats.update(adv_data)

        # Update the global graph data
        self.global_graph_data[device.address] = {
            'rssi': stats.rssi_values,
            'timestamps': stats.timestamps
        }

        if device.address in self.device_frames:
            frame = self.device_frames[device.address]
            frame.stats = stats
            frame.property('stats').dispatch(frame)
            if frame.device.name != device.name:
                frame.device = device
        else:
            self.app_callback.log_with_timestamp(f"Found new device: {device.address} ({device.name or 'Unknown'})", "INFO")
            frame = DeviceFrameKivy(
                device=device,
                stats=stats,
                config_manager=self.config_manager,
                primary_color=self.theme_manager.primary,
                secondary_color=self.theme_manager.secondary
            )
            frame.bind(on_graph_selection_change=self.app_callback.on_graph_selection_change)
            frame.bind(on_connect_request=self.app_callback.connect_to_device)
            self.device_frames[device.address] = frame
            self.ui_container.add_widget(frame)
            self.app_callback.check_auto_connect(frame)

        # Assign the color from the graph to the device frame
        if 'scanner_screen' in self.app_callback.root.ids and 'global_rssi_graph' in self.app_callback.root.ids.scanner_screen.ids:
            graph = self.app_callback.root.ids.scanner_screen.ids.global_rssi_graph
            frame.indicator_color = graph.get_device_color(device.address)

    def filter_devices(self, search_term: str):
        """Filters the displayed devices based on a search term."""
        search_term = search_term.lower()
        for address, frame in self.device_frames.items():
            device_name = (frame.device.name or "Unknown").lower()
            device_address = frame.device.address.lower()
            if search_term in device_name or search_term in device_address:
                if frame.parent is None:
                    self.ui_container.add_widget(frame)
            else:
                if frame.parent is not None:
                    self.ui_container.remove_widget(frame)
