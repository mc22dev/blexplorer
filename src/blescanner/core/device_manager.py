
from typing import Dict, List, Tuple
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
from kivy.uix.boxlayout import BoxLayout
from functools import partial
from blescanner.ui.device_frame_kivy import DeviceFrameKivy
from blescanner.models import DeviceScanStats, LogLevel
from blescanner.platform import platform_utils, BondedDevice


class DeviceManager:
    """Manages discovered BLE devices and their UI representation."""

    def __init__(self, ui_container: BoxLayout, config_manager, theme_manager, log_callback,
                 on_graph_selection_change_callback,
                 connect_callback,
                 auto_connect_callback,
                 update_graph_data_callback,
                 get_graph_device_color_callback,
                 clear_graph_callback):
        self.ui_container = ui_container
        self.config_manager = config_manager
        self.theme_manager = theme_manager
        self.device_frames: Dict[str, DeviceFrameKivy] = {}
        self.scan_stats: Dict[str, DeviceScanStats] = {}
        self.graph_selection: Dict[str, bool] = {}
        self.global_graph_data: Dict[str, Dict] = {}
        self.discovered_devices_batch: List[Tuple[BLEDevice, AdvertisementData]] = []
        self.log_callback = log_callback
        self.on_graph_selection_change_callback = on_graph_selection_change_callback
        self.connect_callback = connect_callback
        self.auto_connect_callback = auto_connect_callback
        self.update_graph_data_callback = update_graph_data_callback
        self.get_graph_device_color_callback = get_graph_device_color_callback
        self.clear_graph_callback = clear_graph_callback

    async def clear(self):
        """Clears all device data and UI elements."""
        self.ui_container.clear_widgets()
        self.clear_graph_callback()
        self.device_frames.clear()
        self.scan_stats.clear()
        self.graph_selection.clear()
        self.global_graph_data.clear()
        self.discovered_devices_batch.clear()

        # Add bonded devices first
        bonded_devices = await platform_utils.get_bonded_devices()
        for bonded_device in bonded_devices:
            # Create a mock BLEDevice for UI representation
            mock_ble_device = BLEDevice(
                address=bonded_device.address,
                name=bonded_device.name,
                details={},
                rssi=0
            )
            self._update_bonded_device_ui(mock_ble_device, bonded_device.bond_state)

    def _update_bonded_device_ui(self, device: BLEDevice, bond_state: str):
        """Creates a UI frame for a bonded device."""
        if device.address in self.device_frames:
            return  # Already displayed

        self.log_callback(f"Found bonded device: {device.address} ({device.name or 'Unknown'})", LogLevel.INFO)
        stats = DeviceScanStats()
        frame = DeviceFrameKivy(
            device=device,
            stats=stats,
            config_manager=self.config_manager,
            primary_color=self.theme_manager.primary,
            secondary_color=self.theme_manager.secondary,
            bond_state=bond_state
        )
        frame.bind(on_graph_selection_change=self.on_graph_selection_change_callback)
        frame.bind(on_connect_request=self.connect_callback)
        self.device_frames[device.address] = frame
        self.scan_stats[device.address] = stats
        self.ui_container.add_widget(frame)

    def add_discovered_device(self, device: BLEDevice, adv_data: AdvertisementData):
        """Adds a discovered device to the batch for processing."""
        self.discovered_devices_batch.append((device, adv_data))

    def process_device_batch(self):
        """Processes the batch of discovered devices and updates the UI."""
        if not self.discovered_devices_batch:
            return

        # Atomically swap the batch to prevent race conditions.
        batch_to_process = self.discovered_devices_batch
        self.discovered_devices_batch = []
        self.log_callback(f"[DeviceManager] Processing batch of {len(batch_to_process)} devices.", LogLevel.DEBUG)

        sorted_batch = sorted(batch_to_process, key=lambda x: x[1].rssi, reverse=True)
        for device, adv_data in sorted_batch:
            self._update_device_ui(device, adv_data)

        self.update_graph_data_callback()

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
            self.log_callback(f"Found new device: {device.address} ({device.name or 'Unknown'})", LogLevel.INFO)
            frame = DeviceFrameKivy(
                device=device,
                stats=stats,
                config_manager=self.config_manager,
                primary_color=self.theme_manager.primary,
                secondary_color=self.theme_manager.secondary
            )
            frame.bind(on_graph_selection_change=self.on_graph_selection_change_callback)
            frame.bind(on_connect_request=self.connect_callback)
            self.device_frames[device.address] = frame
            self.log_callback(f"[DeviceManager] Adding widget for {device.address}", LogLevel.DEBUG)
            self.ui_container.add_widget(frame)
            self.auto_connect_callback(frame)

        # Assign the color from the graph to the device frame
        frame.indicator_color = self.get_graph_device_color_callback(device.address)

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
