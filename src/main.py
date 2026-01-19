import asyncio
import csv
import platform
import subprocess
import re
from datetime import datetime
from functools import partial
import os
import sys

from kivy.utils import platform as kivy_platform
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.properties import ListProperty, StringProperty, BooleanProperty, ObjectProperty, DictProperty, NumericProperty
from kivy.uix.popup import Popup
from kivy.uix.button import Button
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.label import Label
from kivy.core.text import LabelBase
from kivy.core.window import Window

from tooltip import TooltipButton
from file_chooser_dialog import FileChooserDialog
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

from _version import __version__
from ble_decoder import decode_advertisement
from ble_manager import BLEManager
from device_cache import DeviceCache, service_to_dict
from models import CachedService, LogLevel, DeviceScanStats
from device_frame_kivy import DeviceFrameKivy
from characteristic_frame_kivy import CharacteristicFrameKivy
from descriptor_frame_kivy import DescriptorFrameKivy
from collapsible_frame_kivy import CollapsibleFrameKivy
from gatt import GATT_SERVICES
from parameter_window import ParameterWindow
from config_manager import ConfigManager
from ota_window import OTAWindow
from theme import theme_manager
from global_rssi_graph import GlobalRSSIGraph
from wireshark_log_entry import WiresharkLogEntry
from platform_utils import PlatformUtils
from ui_manager import UIManager


def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    else:
        # For development, the base path is the directory containing main.py
        base_path = os.path.abspath(os.path.dirname(__file__))

    return os.path.join(base_path, relative_path)

# Load the kv files for the custom widgets
LabelBase.register(name="MaterialIcons", fn_regular=resource_path("icons/materialdesignicons-webfont.ttf"))
if hasattr(sys, '_MEIPASS'):
    Builder.load_file(resource_path('scanner_screen.kv'))
    Builder.load_file(resource_path('device_screen.kv'))
    Builder.load_file(resource_path('log_screen.kv'))
    Builder.load_file(resource_path('wireshark_screen.kv'))
Builder.load_file(resource_path('deviceframekivy.kv'))
Builder.load_file(resource_path('characteristicframekivy.kv'))
Builder.load_file(resource_path('descriptorframekivy.kv'))
Builder.load_file(resource_path('collapsibleframekivy.kv'))
Builder.load_file(resource_path('parameterwindow.kv'))
Builder.load_file(resource_path('otawindow.kv'))
Builder.load_file(resource_path('globalrssigraph.kv'))
Builder.load_file(resource_path('tooltip.kv'))
Builder.load_file(resource_path('wiresharklogentry.kv'))


class MainLayout(BoxLayout):
    pass


class WiresharkScreen(BoxLayout):
    pass


class BLEScannerApp(App):
    # App properties
    adapters = ListProperty(["Default"])
    log_text = StringProperty("")
    wireshark_data = ListProperty([])
    scan_timeout = StringProperty("5.0")
    adapter = StringProperty("Default")
    VERSION = __version__
    is_scanning = BooleanProperty(False)
    is_connected = BooleanProperty(False)
    is_connecting = BooleanProperty(False)
    is_shutting_down = BooleanProperty(False)
    scan_button = ObjectProperty(None)
    disconnect_button = ObjectProperty(None)
    refresh_button = ObjectProperty(None)
    upload_button = ObjectProperty(None)
    global_graph_data = DictProperty({})
    rssi_min = NumericProperty(-110)
    rssi_max = NumericProperty(-20)

    # Lifecycle Methods
    # -----------------
    def build(self):
        config_path = os.path.join(self.user_data_dir, 'config.ini')
        self.config_manager = ConfigManager(config_path)
        self.ui_manager = UIManager(self)
        self.scan_timeout = self.config_manager.get_setting('scan', 'timeout')
        self.adapter = self.config_manager.get_setting('bluetooth', 'adapter')
        self.theme = theme_manager
        theme_manager.set_theme(self.config_manager.get_setting('theme', 'name'))

        # Set up the graph with configured RSSI limits
        self.rssi_min = int(self.config_manager.get_setting('graph', 'rssi_min'))
        self.rssi_max = int(self.config_manager.get_setting('graph', 'rssi_max'))

        self.ble_manager = BLEManager(
            device_discovered_callback=self._on_device_discovered,
            connection_status_callback=self._on_connection_status_changed,
            notification_callback=self.notification_handler,
            logger_callback=self.log_with_timestamp,
            config_manager=self.config_manager
        )
        self.characteristic_frames = {}
        self.device_frames = {}
        self.device_cache = DeviceCache()
        self.selected_device_frame = None
        self.discovered_devices_batch = []
        self.scan_stats = {}
        self.graph_selection = {}
        self.scan_task = None
        return MainLayout()

    def on_start(self):
        """
        Called when the application is starting.
        Requests permissions on Android.
        """
        def log_startup(dt):
            self.log_with_timestamp(f"BLEScanner v{self.VERSION} starting...", LogLevel.INFO)

        Clock.schedule_once(log_startup)
        Window.bind(on_keyboard=self._on_keyboard)

        self.discover_adapters()
        self.adapter = self.config_manager.get_setting('bluetooth', 'adapter')

    async def on_stop(self):
        """Called when the application is stopping."""
        self.is_shutting_down = True
        if self.is_scanning and self.scan_task and not self.scan_task.done():
            self.scan_task.cancel()
            try:
                # Wait for the scan task to finish its cleanup
                await self.scan_task
            except asyncio.CancelledError:
                # This is expected when we cancel it
                pass
        await self.ble_manager.shutdown()

    # Parameter and Settings Management
    # ---------------------------------
    def open_parameter_window(self):
        """Opens the parameter window."""
        self.parameter_popup = ParameterWindow()
        self.parameter_popup.ids.scan_timeout_input.text = self.scan_timeout
        self.parameter_popup.ids.theme_spinner.text = self.config_manager.get_setting('theme', 'name')
        self.parameter_popup.ids.adapter_spinner.values = self.adapters
        self.parameter_popup.ids.adapter_spinner.text = self.adapter
        self.parameter_popup.ids.auto_connect_checkbox.active = self.config_manager.get_setting('auto_connect', 'enabled') == 'True'
        self.parameter_popup.ids.auto_connect_filter_input.text = self.config_manager.get_setting('auto_connect', 'filter')
        self.parameter_popup.ids.rssi_min_input.text = self.config_manager.get_setting('graph', 'rssi_min')
        self.parameter_popup.ids.rssi_max_input.text = self.config_manager.get_setting('graph', 'rssi_max')
        self.parameter_popup.ids.ble_library_spinner.text = self.config_manager.get_setting('ble', 'library')
        self.parameter_popup.open()

    def restore_default_parameters(self, popup):
        """Restores the default parameters in the UI without saving."""
        popup.ids.scan_timeout_input.text = self.config_manager.get_default_setting('scan', 'timeout')
        popup.ids.theme_spinner.text = self.config_manager.get_default_setting('theme', 'name')
        popup.ids.adapter_spinner.text = self.config_manager.get_default_setting('bluetooth', 'adapter')
        popup.ids.auto_connect_checkbox.active = self.config_manager.get_default_setting('auto_connect', 'enabled') == 'True'
        popup.ids.auto_connect_filter_input.text = self.config_manager.get_default_setting('auto_connect', 'filter')
        popup.ids.rssi_min_input.text = self.config_manager.get_default_setting('graph', 'rssi_min')
        popup.ids.rssi_max_input.text = self.config_manager.get_default_setting('graph', 'rssi_max')
        popup.ids.ble_library_spinner.text = self.config_manager.get_default_setting('ble', 'library')
        self.log_with_timestamp("UI restored to default parameters. Click OK to save.", LogLevel.INFO)

    def update_parameters(self, popup):
        """Updates the parameters from the parameter window."""
        settings = {
            'scan_timeout': popup.ids.scan_timeout_input.text,
            'theme': popup.ids.theme_spinner.text,
            'adapter': popup.ids.adapter_spinner.text,
            'auto_connect_enabled': popup.ids.auto_connect_checkbox.active,
            'auto_connect_filter': popup.ids.auto_connect_filter_input.text,
            'rssi_min': popup.ids.rssi_min_input.text,
            'rssi_max': popup.ids.rssi_max_input.text,
            'ble_library': popup.ids.ble_library_spinner.text
        }
        if self._validate_and_apply_settings(settings):
            popup.dismiss()

    def _validate_and_apply_settings(self, settings):
        """Validates and applies all settings."""
        if not self._validate_and_set_scan_timeout(settings['scan_timeout']):
            return False
        if not self._validate_and_set_rssi_range(settings['rssi_min'], settings['rssi_max']):
            return False

        self._set_theme(settings['theme'])
        self._set_adapter(settings['adapter'])
        self._set_auto_connect(settings['auto_connect_enabled'], settings['auto_connect_filter'])
        self._set_ble_library(settings['ble_library'])
        return True

    def _validate_and_set_scan_timeout(self, timeout_str):
        """Validates and sets the scan timeout."""
        try:
            float(timeout_str)
            self.scan_timeout = timeout_str
            self.config_manager.set_setting('scan', 'timeout', self.scan_timeout)
            self.log_with_timestamp(f"Scan timeout set to {self.scan_timeout}s.", LogLevel.INFO)
            return True
        except ValueError:
            self.log_with_timestamp(f"Invalid scan timeout value: {timeout_str}. Please enter a number.", LogLevel.ERROR)
            return False

    def _validate_and_set_rssi_range(self, min_str, max_str):
        """Validates and sets the RSSI graph range."""
        try:
            min_val = int(min_str)
            max_val = int(max_str)
            self.rssi_min = min_val
            self.rssi_max = max_val
            self.config_manager.set_setting('graph', 'rssi_min', str(min_val))
            self.config_manager.set_setting('graph', 'rssi_max', str(max_val))
            self.log_with_timestamp(f"RSSI range set to [{min_val}, {max_val}].", LogLevel.INFO)
            return True
        except ValueError:
            self.log_with_timestamp(f"Invalid RSSI range. Please enter integers for min and max.", LogLevel.ERROR)
            return False

    def _set_theme(self, theme_name):
        """Sets the application theme."""
        self.config_manager.set_setting('theme', 'name', theme_name)
        theme_manager.set_theme(theme_name)
        self.log_with_timestamp(f"Theme set to {theme_name}.", LogLevel.INFO)

    def _set_adapter(self, adapter_name):
        """Sets the Bluetooth adapter."""
        self.adapter = adapter_name
        self.config_manager.set_setting('bluetooth', 'adapter', self.adapter)
        self.log_with_timestamp(f"Adapter set to {self.adapter}.", LogLevel.INFO)

    def _set_auto_connect(self, enabled, filter_text):
        """Sets the auto-connect settings."""
        self.config_manager.set_setting('auto_connect', 'enabled', str(enabled))
        self.config_manager.set_setting('auto_connect', 'filter', filter_text)
        self.log_with_timestamp(f"Auto-connect set to {enabled} with filter '{filter_text}'.", LogLevel.INFO)

    def _set_ble_library(self, library_name):
        """Sets the BLE library."""
        self.config_manager.set_setting('ble', 'library', library_name)
        self.log_with_timestamp(f"BLE library set to {library_name}. Please restart the app for the change to take effect.", LogLevel.INFO)


    # Keyboard Shortcuts
    # ------------------
    def _on_keyboard(self, window, key, scancode, codepoint, modifier):
        """
        Handles keyboard shortcuts.
        """
        if 'ctrl' in modifier:
            if codepoint == 'q':
                self.stop()
            elif codepoint == 's':
                if not self.is_scanning:
                    self.scan_for_devices()
            elif codepoint == 'd':
                if self.is_connected:
                    self.disconnect_from_device()
            elif codepoint == 'l':
                self.clear_log()

    # Android Permissions
    # -------------------
    def _on_android_permissions_callback(self, permissions, grants):
        """
        Callback for the permission request. Checks if all permissions were granted.
        """
        self.log_with_timestamp(f"Permission grants received: {grants}", LogLevel.DEBUG)
        success = all(grant == 0 for grant in grants)
        if success:
            self.log_with_timestamp("Permissions granted. You can now scan for devices.", LogLevel.SUCCESS)
        else:
            self.log_with_timestamp("Permissions denied. Scanning is disabled.", LogLevel.ERROR)

    def show_android_system_check_popup(self, bluetooth_enabled, location_enabled):
        """
        Shows a popup if Bluetooth or Location services are not enabled on Android.
        """
        missing_services = []
        if not bluetooth_enabled:
            missing_services.append("Bluetooth")
        if not location_enabled:
            missing_services.append("Location Services")

        message = "To scan for BLE devices, please enable the following services in your device settings:\n\n" + "\n".join(missing_services)

        popup_content = BoxLayout(orientation='vertical', padding=10, spacing=10)
        popup_content.add_widget(Label(text=message, size_hint_y=None, height=100))
        ok_button = Button(text="OK", size_hint_y=None, height=50)
        popup_content.add_widget(ok_button)

        popup = Popup(title="System Services Disabled",
                      content=popup_content,
                      size_hint=(0.8, 0.4))
        ok_button.bind(on_release=popup.dismiss)
        popup.open()

    # BLE Scanning and Device Handling
    # --------------------------------

    def discover_adapters(self):
        """Discovers available Bluetooth adapters and populates the dropdown."""
        adapters = ["Default"]
        if platform.system() == "Linux":
            try:
                result = subprocess.run(['hciconfig'], capture_output=True, text=True, check=True)
                adapters.extend(re.findall(r'^(hci\d+)', result.stdout, re.MULTILINE))
            except (FileNotFoundError, subprocess.CalledProcessError):
                self.log_with_timestamp("hciconfig not found. Could not list Bluetooth adapters.", LogLevel.WARNING)
        else:
            self.log_with_timestamp("Adapter discovery is currently only supported on Linux.", LogLevel.INFO)
        self.adapters = adapters

    def scan_for_devices(self, *args):
        """
        Schedules the asynchronous scan for devices.
        On Android, it checks for permissions first.
        """
        if kivy_platform == 'android':
            if not PlatformUtils.check_android_permissions():
                PlatformUtils.request_android_permissions(self._on_android_permissions_callback)
                return

            bluetooth_enabled = PlatformUtils.is_bluetooth_enabled()
            location_enabled = PlatformUtils.is_location_enabled()

            if not bluetooth_enabled or not location_enabled:
                self.show_android_system_check_popup(bluetooth_enabled, location_enabled)
                return

        self.scan_task = asyncio.create_task(self.async_scan_for_devices())

    async def async_scan_for_devices(self):
        """Initiates a scan for nearby BLE devices."""
        if self.selected_device_frame:
            self.selected_device_frame.is_selected = False
            self.selected_device_frame = None
        self.root.ids.scanner_screen.ids.device_list.clear_widgets()
        if 'scanner_screen' in self.root.ids and 'global_rssi_graph' in self.root.ids.scanner_screen.ids:
            self.root.ids.scanner_screen.ids.global_rssi_graph.clear_graph()
        self.global_graph_data = {}
        self.device_frames = {}
        self.discovered_devices_batch = []
        self.scan_stats = {}
        self.log_with_timestamp("Scan started...", LogLevel.INFO)
        self.is_scanning = True
        adapter = self.adapter if self.adapter != "Default" else None

        try:
            timeout = float(self.scan_timeout)
        except ValueError:
            self.log_with_timestamp("Invalid scan timeout. Please enter a number.", LogLevel.ERROR)
            self.is_scanning = False
            return

        self._batch_processing_task = asyncio.create_task(self._process_device_batch_periodically())
        await self.ble_manager.scan_for_devices(adapter)
        try:
            await asyncio.sleep(timeout)
        except asyncio.CancelledError:
            self.log_with_timestamp("Scan stopped by user.", LogLevel.INFO)
        finally:
            await self.async_stop_scan()

    def stop_scan(self, *args):
        """Stops the BLE scan task."""
        if self.scan_task and not self.scan_task.done():
            self.scan_task.cancel()

    async def async_stop_scan(self):
        """Async helper to perform the actual cleanup after a scan stops."""
        if self.is_scanning:
            await self.ble_manager.stop_scan()
            if self._batch_processing_task:
                self._batch_processing_task.cancel()
                try:
                    await self._batch_processing_task
                except asyncio.CancelledError:
                    pass
                self._batch_processing_task = None
            self._process_device_batch()  # Process any remaining devices
            self.log_with_timestamp("Scan finished.", LogLevel.INFO)
            self.is_scanning = False

    def filter_devices(self, search_term):
        """Filters the device list based on the search term."""
        search_term = search_term.lower()
        for address, frame in self.device_frames.items():
            device_name = (frame.device.name or "Unknown").lower()
            device_address = frame.device.address.lower()
            if search_term in device_name or search_term in device_address:
                if frame.parent is None:
                    self.root.ids.scanner_screen.ids.device_list.add_widget(frame)
            else:
                if frame.parent is not None:
                    self.root.ids.scanner_screen.ids.device_list.remove_widget(frame)

    def clear_device_filter(self):
        """Clears the device filter."""
        self.root.ids.scanner_screen.ids.search_input.text = ""

    def _on_device_discovered(self, device: BLEDevice, adv_data: AdvertisementData):
        """Callback for when a device is discovered."""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        manufacturer_data_str = ', '.join(f'{k}:{v.hex()}' for k, v in adv_data.manufacturer_data.items())
        service_data_str = ', '.join(f'"{k}":{v.hex()}' for k, v in adv_data.service_data.items())
        decoded_info = decode_advertisement(adv_data)

        entry = {
            'time': timestamp,
            'rssi': adv_data.rssi,
            'address': device.address,
            'service_uuids': ', '.join(adv_data.service_uuids),
            'service_data': service_data_str,
            'manufacturer_data': manufacturer_data_str,
            'decoded_data': decoded_info
        }
        self.log_to_wireshark(entry)

        self.discovered_devices_batch.append((device, adv_data))

    async def _process_device_batch_periodically(self):
        """Periodically processes the batch of discovered devices."""
        while True:
            self._process_device_batch()
            await asyncio.sleep(1.0)

    def _process_device_batch(self, *args):
        """Processes the batch of discovered devices and updates the UI."""
        if self.is_shutting_down:
            return
        # Sort by RSSI to show the strongest signals first
        sorted_batch = sorted(self.discovered_devices_batch, key=lambda x: x[1].rssi, reverse=True)
        if not sorted_batch:
            return

        for device, adv_data in sorted_batch:
            self._populate_device_ui(device, adv_data)

        # Reassign the dictionary to trigger the update on the Kivy property
        self._update_graph_data()
        # Reassign to a copy to trigger the Kivy property update, as in-place modification is not detected.
        self.global_graph_data = self.global_graph_data.copy()
        self.discovered_devices_batch = []

    def _update_graph_data(self):
        """Filters and updates the graph data based on selection."""
        filtered_data = {
            addr: data for addr, data in self.global_graph_data.items()
            if self.graph_selection.get(addr, True)
        }
        self.root.ids.scanner_screen.ids.global_rssi_graph.device_data = filtered_data

    def _on_graph_selection_change(self, instance, address, is_selected):
        """Callback for when a device's graph selection changes."""
        self.graph_selection[address] = is_selected
        self._update_graph_data()

    def _populate_device_ui(self, device: BLEDevice, adv_data: AdvertisementData):
        """
        Populates the UI with a discovered BLE device, updating if it already exists.
        """
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
            # Update existing frame only if data has changed to avoid unnecessary UI redraws
            frame = self.device_frames[device.address]
            frame.stats = stats
            frame.property('stats').dispatch(frame)
            if frame.device.name != device.name:
                frame.device = device
        else:
            # Create a new frame for a new device
            self.log_with_timestamp(f"Found new device: {device.address} ({device.name or 'Unknown'})", LogLevel.INFO)
            frame = DeviceFrameKivy(device=device, stats=stats)
            frame.bind(on_graph_selection_change=self._on_graph_selection_change)
            self.device_frames[device.address] = frame
            self.root.ids.scanner_screen.ids.device_list.add_widget(frame)
            self._check_auto_connect(frame)

        # Assign the color from the graph to the device frame
        if 'scanner_screen' in self.root.ids and 'global_rssi_graph' in self.root.ids.scanner_screen.ids:
            graph = self.root.ids.scanner_screen.ids.global_rssi_graph
            frame.indicator_color = graph.get_device_color(device.address)

    def _check_auto_connect(self, device_frame: DeviceFrameKivy):
        """Checks if the device matches the auto-connect filter and connects if it does."""
        auto_connect_enabled = self.config_manager.get_setting('auto_connect', 'enabled') == 'True'
        if not auto_connect_enabled or self.is_connected or self.is_connecting:
            return

        auto_connect_filter = self.config_manager.get_setting('auto_connect', 'filter').lower()
        device = device_frame.device
        device_name = (device.name or "Unknown").lower()
        device_address = device.address.lower()

        if auto_connect_filter in device_name or auto_connect_filter in device_address:
            self.log_with_timestamp(f"Auto-connecting to device: {device.address}", LogLevel.INFO)
            self.connect_to_device(device_frame)

    def connect_to_device(self, device_frame: DeviceFrameKivy):
        """Connects to the selected device."""
        asyncio.create_task(self.async_connect_to_device(device_frame))

    async def async_connect_to_device(self, device_frame: DeviceFrameKivy):
        """Connects to the selected device."""
        if self.is_scanning:
            await self.stop_scan()

        if self.selected_device_frame:
            self.selected_device_frame.is_selected = False

        self.selected_device_frame = device_frame
        self.selected_device_frame.is_selected = True

        device = device_frame.device
        self.is_connecting = True
        self.log_with_timestamp(f"Connecting to {device.address} ({device.name})...", LogLevel.INFO)
        adapter = self.adapter if self.adapter != "Default" else None
        await self.ble_manager.connect_to_device(device.address, adapter)

    def disconnect_from_device(self, *args):
        """Initiates a manual disconnection from the connected device."""
        if self.ble_manager and self.ble_manager.client and self.ble_manager.client.is_connected:
            self.log_with_timestamp("Disconnect button pressed.", LogLevel.INFO)
            asyncio.create_task(self.ble_manager.disconnect_from_device())

    # BLE Callbacks
    # -------------
    def _on_connection_status_changed(self, is_connected: bool):
        """Callback for connection status changes."""
        if self.is_shutting_down:
            return
        self.ui_manager.update_connection_ui(is_connected)

    # Attribute Discovery and UI Population
    # -------------------------------------
    def discover_attributes(self):
        """Discovers and displays the services and characteristics of the connected device."""
        self.root.ids.device_screen.ids.characteristic_list.clear_widgets()
        self.characteristic_frames = {}

        cached_services_data = None
        if self.selected_device_frame:
            cached_services_data = self.device_cache.load_device(self.selected_device_frame.device.address)
            if cached_services_data:
                self.log_with_timestamp("Loading services from cache...", LogLevel.INFO)
                cached_services = [CachedService(s) for s in cached_services_data]
                all_characteristics = [char for service in cached_services for char in service.characteristics]
                all_characteristics.sort(key=lambda c: (c.service_uuid, c.uuid))
                self.populate_characteristic_ui(all_characteristics)
                self.log_with_timestamp("Finished loading from cache.", LogLevel.INFO)

        if self.ble_manager.client:
            if not cached_services_data:
                all_characteristics = [char for service in self.ble_manager.client.services for char in service.characteristics]
                all_characteristics.sort(key=lambda c: (c.service_uuid, c.uuid))
                self.populate_characteristic_ui(all_characteristics)

            self._check_for_attribute_diffs(cached_services_data)

    def populate_characteristic_ui(self, characteristics):
        # Group characteristics by service UUID
        service_map = {}
        for char in characteristics:
            service_uuid = str(char.service_uuid)
            if service_uuid not in service_map:
                service_map[service_uuid] = []
            service_map[service_uuid].append(char)

        # Create collapsible frames for each service, passing the characteristics and a creation callback
        for service_uuid, service_chars in service_map.items():
            service_name = GATT_SERVICES.get(service_uuid.split("-")[0].lstrip("0").lower(), "Unknown Service")
            sf = CollapsibleFrameKivy(
                title=f"Service: {service_name} ({service_uuid})",
                characteristics=service_chars,
                populate_callback=self._create_and_bind_characteristic_frame,
                is_expanded=False  # Start collapsed
            )
            self.root.ids.device_screen.ids.characteristic_list.add_widget(sf)

    def _create_and_bind_characteristic_frame(self, char):
        """Creates a characteristic frame, binds its events, and returns the frame."""
        char_frame = CharacteristicFrameKivy(characteristic=char)
        self.characteristic_frames[char.uuid] = char_frame

        if "notify" not in char.properties and "indicate" not in char.properties:
            char_frame.ids.subscribe_button.disabled = True

        char_frame.ids.read_button.bind(on_release=partial(self.read_characteristic, char, char_frame))
        char_frame.ids.write_button.bind(on_release=partial(self.write_characteristic, char, char_frame))
        char_frame.ids.subscribe_button.bind(active=partial(self.toggle_subscription, char, char_frame))

        user_desc = None
        for desc in char.descriptors:
            if desc.uuid == "00002901-0000-1000-8000-00805f9b34fb":
                user_desc = desc
                continue
            desc_frame = DescriptorFrameKivy(descriptor=desc)
            char_frame.add_widget(desc_frame)
            desc_frame.ids.read_button.bind(on_release=partial(self.read_descriptor, desc, desc_frame))
            desc_frame.ids.write_button.bind(on_release=partial(self.write_descriptor, desc, desc_frame))

        if user_desc:
            # Defer the read operation to allow the UI to draw first
            asyncio.create_task(self.read_descriptor(user_desc, char_frame.ids.user_description_label))

        return char_frame

    def _check_for_attribute_diffs(self, cached_services):
        if self.ble_manager.client:
            self.log_with_timestamp("Checking for attribute differences...", LogLevel.INFO)
            live_services = [service_to_dict(s) for s in self.ble_manager.client.services]

            if cached_services:
                diffs = self.device_cache.compare_services(cached_services, live_services)
                if diffs:
                    self.log_with_timestamp("Differences found between cache and live data:", LogLevel.INFO)
                    for diff in diffs:
                        self.log_with_timestamp(f"- {diff}", LogLevel.INFO)
                    self.log_with_timestamp("Refreshing UI with live data...", LogLevel.INFO)
                    self.root.ids.device_screen.ids.characteristic_list.clear_widgets()
                    self.characteristic_frames = {}
                    all_characteristics = [char for service in self.ble_manager.client.services for char in
                                           service.characteristics]
                    all_characteristics.sort(key=lambda c: (c.service_uuid, c.uuid))
                    self.populate_characteristic_ui(all_characteristics)
                else:
                    self.log_with_timestamp("No differences found.", LogLevel.INFO)

            self.device_cache.save_device(self.ble_manager.client)

    def read_all_characteristics(self, *args):
        """Initiates a read operation for all readable characteristics."""
        self.log_with_timestamp("--- Reading all readable characteristics ---", LogLevel.INFO)
        for char_frame in self.characteristic_frames.values():
            if "read" in char_frame.characteristic.properties:
                asyncio.create_task(self.read_characteristic(char_frame.characteristic, char_frame))

    # Logging and File Operations
    # ---------------------------
    def clear_log(self, *args):
        """Clears the debug log text box."""
        self.log_with_timestamp("Clearing log...", LogLevel.INFO)
        self.root.ids.log_screen.ids.log_view.text = ""

    def clear_wireshark_log(self, *args):
        """Clears the Wireshark log."""
        self.log_with_timestamp("Clearing Wireshark log...", LogLevel.INFO)
        self.wireshark_data = []

    def show_save_dialog(self, *args):
        """Shows the save file dialog for the main log."""
        self.ui_manager.show_save_dialog("Save Log", self.save_log)

    def show_save_wireshark_dialog(self, *args):
        """Shows the save file dialog for the Wireshark log."""
        self.ui_manager.show_save_dialog("Save Wireshark Log", self.save_wireshark_log)

    def dismiss_popup(self):
        """Dismisses the currently open dialog."""
        self.ui_manager.dismiss_popup()

    def save_log(self, path, selection):
        """Saves the content of the debug log to a file."""
        if not selection:
            self.ui_manager.dismiss_popup()
            return
        filepath = os.path.join(path, selection[0])
        log_content = self.root.ids.log_screen.ids.log_view.text
        try:
            with open(filepath, "w") as f:
                f.write(log_content)
            self.log_with_timestamp(f"Log saved to {filepath}", LogLevel.SUCCESS)
        except IOError as e:
            self.log_with_timestamp(f"Error saving log: {e}", LogLevel.ERROR)
        self.ui_manager.dismiss_popup()

    def save_wireshark_log(self, path, selection):
        """Saves the content of the Wireshark log to a CSV file."""
        if not selection:
            self.ui_manager.dismiss_popup()
            return
        filepath = os.path.join(path, selection[0])
        if not filepath.lower().endswith('.csv'):
            filepath += '.csv'

        try:
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                if self.wireshark_data:
                    writer = csv.DictWriter(f, fieldnames=self.wireshark_data[0].keys())
                    writer.writeheader()
                    writer.writerows(self.wireshark_data)
            self.log_with_timestamp(f"Wireshark log saved to {filepath}", LogLevel.SUCCESS)
        except (IOError, csv.Error) as e:
            self.log_with_timestamp(f"Error saving Wireshark log: {e}", LogLevel.ERROR)
        self.ui_manager.dismiss_popup()

    # BLE Characteristic and Descriptor Operations
    # --------------------------------------------
    async def read_characteristic(self, characteristic, char_frame, *args):
        value = await self.ble_manager.read_characteristic(characteristic.uuid)
        self.ui_manager.on_characteristic_read(char_frame, value)

    def write_characteristic(self, characteristic, char_frame, *args):
        asyncio.create_task(self.async_write_characteristic(characteristic, char_frame))

    async def async_write_characteristic(self, characteristic, char_frame):
        value_str = char_frame.ids.value_input.text
        write_mode = char_frame.ids.write_mode_spinner.text
        try:
            char_frame.ids.value_input.background_color = (1, 1, 1, 1)
            if write_mode == 'ASCII':
                write_value = value_str.encode('utf-8')
            else:  # Hex mode
                write_value = bytes.fromhex(value_str)
        except ValueError:
            self.log_with_timestamp(f"Invalid input for write on {characteristic.uuid}", LogLevel.ERROR)
            char_frame.ids.value_input.background_color = (1, 0.6, 0.6, 1)
            return

        success = await self.ble_manager.write_characteristic(characteristic.uuid, write_value)
        self.ui_manager.on_characteristic_write(char_frame, success, characteristic, value_str, write_mode)

    def reset_char_color(self, char_frame):
        """Schedules the color reset for a characteristic's value input."""
        asyncio.create_task(self.async_reset_char_color(char_frame))

    async def async_reset_char_color(self, char_frame):
        """Resets the background color of a characteristic's value input after a delay."""
        await asyncio.sleep(0.5)
        char_frame.ids.value_input.background_color = (1, 1, 1, 1)

    async def read_descriptor(self, descriptor, desc_frame, *args):
        value = await self.ble_manager.read_descriptor(descriptor.uuid)
        self.ui_manager.on_descriptor_read(descriptor, desc_frame, value)

    def write_descriptor(self, descriptor, desc_frame, *args):
        asyncio.create_task(self.async_write_descriptor(descriptor, desc_frame))

    async def async_write_descriptor(self, descriptor, desc_frame):
        value_str = desc_frame.ids.value_input.text
        try:
            write_value = bytes.fromhex(value_str)
        except ValueError:
            self.log_with_timestamp(f"Invalid hex value for write on {descriptor.uuid}", LogLevel.ERROR)
            return

        success = await self.ble_manager.write_descriptor(descriptor.uuid, write_value)
        self.ui_manager.on_descriptor_write(desc_frame, success)

    def toggle_subscription(self, characteristic, char_frame, widget, active):
        if active:
            asyncio.create_task(self.ble_manager.subscribe_to_characteristic(characteristic.uuid))
            self.log_with_timestamp(f"Subscribed to {characteristic.uuid}", LogLevel.INFO)
        else:
            asyncio.create_task(self.ble_manager.unsubscribe_from_characteristic(characteristic.uuid))
            self.log_with_timestamp(f"Unsubscribed from {characteristic.uuid}", LogLevel.INFO)

    def notification_handler(self, characteristic, data):
        """Handles incoming notifications."""
        self.on_notification(characteristic, data)

    def on_notification(self, characteristic, data):
        if characteristic.uuid in self.characteristic_frames:
            char_frame = self.characteristic_frames[characteristic.uuid]
            char_frame.raw_value = data
            display_format = char_frame.ids.format_spinner.text
            self.log_with_timestamp(f"Notification from {characteristic.uuid} ({display_format}): {char_frame.char_value}", LogLevel.INFO)

        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        entry = {
            'time': timestamp,
            'rssi': 'N/A',
            'address': self.ble_manager.client.address if self.ble_manager.client else 'Unknown',
            'service_uuids': f"Notification: {characteristic.uuid}",
            'service_data': '',
            'manufacturer_data': data.hex(),
            'decoded_data': ''  # No specific decoding for notifications yet
        }
        self.log_to_wireshark(entry)

    def log_to_wireshark(self, entry: dict):
        """Logs a new entry to the Wireshark tab, scheduling it on the main thread."""
        def _log(dt):
            app = App.get_running_app()
            if not app:
                return
            app.wireshark_data.append(entry)
            if 'wireshark_screen' in app.root.ids and 'autoscroll_checkbox' in app.root.ids.wireshark_screen.ids:
                if app.root.ids.wireshark_screen.ids.autoscroll_checkbox.active:
                    if 'wireshark_log_view' in app.root.ids.wireshark_screen.ids:
                        app.root.ids.wireshark_screen.ids.wireshark_log_view.scroll_y = 0
        Clock.schedule_once(_log)

    def log_with_timestamp(self, message: str, level: LogLevel = LogLevel.INFO):
        """Logs a message with a timestamp and level, scheduling it on the main thread."""
        def _log(dt):
            app = App.get_running_app()
            if not app or not app.root:
                return
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            log_message = f"[{timestamp}] [{level.value}] {message}\n"
            if 'log_screen' in app.root.ids and 'log_view' in app.root.ids.log_screen.ids:
                app.root.ids.log_screen.ids.log_view.text += log_message
                if app.root.ids.log_screen.ids.autoscroll_checkbox.active and 'log_scroll_view' in app.root.ids.log_screen.ids:
                    app.root.ids.log_screen.ids.log_scroll_view.scroll_y = 0
        Clock.schedule_once(_log)

    # OTA (Over-the-Air) Update Methods
    # ---------------------------------
    def open_ota_window(self):
        """Opens the OTA window."""
        if not self.ble_manager.client or not self.ble_manager.client.is_connected:
            self.log_with_timestamp("OTA operations require a connected device.", LogLevel.WARNING)
            return
        self.ota_popup = OTAWindow()
        self.ota_popup.ids.upload_button.on_release = self.show_load_dialog
        self.ota_popup.open()

    def show_load_dialog(self):
        """Shows the load file dialog for OTA upload."""
        content = FileChooserDialog(title="Load", callback=self.upload_firmware, dismiss_callback=self.dismiss_popup, mode='open')
        self.dialog = Popup(title="Load Firmware", content=content,
                                 size_hint=(0.9, 0.9))
        self.dialog.open()

    def upload_firmware(self, path, selection):
        """Handles the firmware upload process."""
        if not selection:
            self.dismiss_popup()
            return
        filepath = os.path.join(path, selection[0])
        self.log_with_timestamp(f"Starting OTA upload from {filepath}", LogLevel.INFO)
        asyncio.create_task(self.ble_manager.start_ota_upload(filepath, self.ota_progress_callback))
        self.dismiss_popup()
        if self.ota_popup:
            self.ota_popup.ids.file_label.text = filepath

    def ota_progress_callback(self, progress):
        """Callback for OTA progress updates."""
        if self.ota_popup:
            self.ota_popup.ids.progress_bar.value = progress
        if progress == 100:
            self.log_with_timestamp("OTA operation completed.", LogLevel.SUCCESS)


    async def app_func(self):
        """The async main function of the app."""
        await self.async_run(async_lib='asyncio')


if __name__ == '__main__':
    try:
        loop = asyncio.get_event_loop()
        app = BLEScannerApp()
        loop.run_until_complete(app.app_func())
    except asyncio.CancelledError:
        pass  # Ignore TaskCancelledError when the app is closed
    except KeyboardInterrupt:
        pass
