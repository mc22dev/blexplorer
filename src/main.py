import platform
import subprocess
import re
from datetime import datetime
from functools import partial
import os
import sys
from enum import Enum

from kivy.utils import platform as kivy_platform
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.properties import ListProperty, StringProperty, BooleanProperty
from kivy.uix.popup import Popup
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.core.window import Window

from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

from ble_manager import BLEManager
from device_cache import DeviceCache, service_to_dict
from models import CachedService, LogLevel
from device_frame_kivy import DeviceFrameKivy
from characteristic_frame_kivy import CharacteristicFrameKivy
from descriptor_frame_kivy import DescriptorFrameKivy
from collapsible_frame_kivy import CollapsibleFrameKivy
from gatt import GATT_SERVICES
from parameter_window import ParameterWindow
from config_manager import ConfigManager
from ota_window import OTAWindow
from theme import theme_manager


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
Builder.load_file(resource_path('deviceframekivy.kv'))
Builder.load_file(resource_path('characteristicframekivy.kv'))
Builder.load_file(resource_path('descriptorframekivy.kv'))
Builder.load_file(resource_path('collapsibleframekivy.kv'))
Builder.load_file(resource_path('parameterwindow.kv'))
Builder.load_file(resource_path('otawindow.kv'))


class MainLayout(BoxLayout):
    pass

class SaveDialog(BoxLayout):
    def __init__(self, save_callback, dismiss_callback, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.save_callback = save_callback
        self.dismiss_callback = dismiss_callback
        self.file_chooser = FileChooserListView(path=os.getcwd())
        self.add_widget(self.file_chooser)

        button_box = BoxLayout(size_hint_y=None, height=40)
        self.save_button = Button(text='Save')
        self.save_button.bind(on_release=self.on_save)
        button_box.add_widget(self.save_button)
        self.cancel_button = Button(text='Cancel')
        self.cancel_button.bind(on_release=self.on_cancel)
        button_box.add_widget(self.cancel_button)
        self.add_widget(button_box)

    def on_save(self, instance):
        self.save_callback(self.file_chooser.path, self.file_chooser.selection)

    def on_cancel(self, instance):
        self.dismiss_callback()


class LoadDialog(BoxLayout):
    def __init__(self, load_callback, dismiss_callback, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.load_callback = load_callback
        self.dismiss_callback = dismiss_callback
        self.file_chooser = FileChooserListView(path=os.getcwd())
        self.add_widget(self.file_chooser)

        button_box = BoxLayout(size_hint_y=None, height=40)
        self.load_button = Button(text='Load')
        self.load_button.bind(on_release=self.on_load)
        button_box.add_widget(self.load_button)
        self.cancel_button = Button(text='Cancel')
        self.cancel_button.bind(on_release=self.on_cancel)
        button_box.add_widget(self.cancel_button)
        self.add_widget(button_box)

    def on_load(self, instance):
        self.load_callback(self.file_chooser.path, self.file_chooser.selection)

    def on_cancel(self, instance):
        self.dismiss_callback()


class BLEScannerApp(App):
    adapters = ListProperty(["Default"])
    log_text = StringProperty("")
    is_scan_button_disabled = BooleanProperty(True)
    scan_timeout = StringProperty("5.0")
    VERSION = "1.0.0"

    def open_parameter_window(self):
        """Opens the parameter window."""
        self.parameter_popup = ParameterWindow()
        self.parameter_popup.ids.scan_timeout_input.text = self.scan_timeout
        self.parameter_popup.ids.theme_spinner.text = self.config_manager.get_setting('theme', 'name')
        self.parameter_popup.open()

    def restore_default_parameters(self, popup):
        """Restores the default parameters."""
        self.config_manager.restore_defaults()
        self.scan_timeout = self.config_manager.get_setting('scan', 'timeout')
        popup.ids.scan_timeout_input.text = self.scan_timeout

        theme_name = self.config_manager.get_setting('theme', 'name')
        theme_manager.set_theme(theme_name)
        popup.ids.theme_spinner.text = theme_name

        self.log_with_timestamp("Default parameters restored.", LogLevel.INFO)

    def update_parameters(self, popup):
        """Updates the parameters from the parameter window."""
        new_timeout = popup.ids.scan_timeout_input.text
        new_theme = popup.ids.theme_spinner.text
        try:
            # Validate that the input is a valid float before saving
            float(new_timeout)
            self.scan_timeout = new_timeout
            self.config_manager.set_setting('scan', 'timeout', self.scan_timeout)
            self.log_with_timestamp(f"Scan timeout set to {self.scan_timeout}s.", LogLevel.INFO)

            self.config_manager.set_setting('theme', 'name', new_theme)
            theme_manager.set_theme(new_theme)
            self.log_with_timestamp(f"Theme set to {new_theme}.", LogLevel.INFO)

            popup.dismiss()
        except ValueError:
            self.log_with_timestamp(f"Invalid scan timeout value: {new_timeout}. Please enter a number.", LogLevel.ERROR)
            # Optionally, provide visual feedback to the user in the popup
            popup.ids.scan_timeout_input.background_color = (1, 0.6, 0.6, 1)


    def on_start(self):
        """
        Called when the application is starting.
        Binds UI events and requests permissions on Android.
        """
        self.log_with_timestamp(f"BLEScanner v{self.VERSION} starting...", LogLevel.INFO)
        self.root.ids.scan_button.bind(on_release=self.scan_for_devices)
        self.root.ids.disconnect_button.bind(on_release=self.disconnect_from_device)
        self.root.ids.read_all_button.bind(on_release=self.read_all_characteristics)
        self.root.ids.clear_log_button.bind(on_release=self.clear_log)
        self.root.ids.save_log_button.bind(on_release=self.show_save_dialog)
        self.root.ids.adapter_spinner.bind(on_text=self.on_adapter_selected)

        Window.bind(on_keyboard=self._on_keyboard)

        if kivy_platform == 'android':
            self.request_android_permissions()
        else:
            self.is_scan_button_disabled = False

        self.discover_adapters()

    def _on_permissions_result(self, success: bool, dt=None):
        """
        Callback function for permission request results.
        Enables the scan button if permissions were granted.
        """
        if success:
            self.log_with_timestamp("Permissions granted.", LogLevel.SUCCESS)
            self.is_scan_button_disabled = False
        else:
            self.log_with_timestamp("Permissions denied. Scanning is disabled.", LogLevel.ERROR)
            self.is_scan_button_disabled = True

    def _on_permissions_callback(self, permissions, grants):
        """
        Callback for the permission request. Checks if all permissions were granted.
        """
        success = all(grant == 0 for grant in grants)
        self._on_permissions_result(success)

    def request_android_permissions(self):
        """
        Requests BLE scanning permissions on Android using Kivy's built-in APIs.
        """
        from android.permissions import request_permissions, Permission

        permissions = [
            Permission.BLUETOOTH_SCAN,
            Permission.BLUETOOTH_CONNECT,
            Permission.ACCESS_FINE_LOCATION,
        ]

        self.log_with_timestamp("Requesting Android permissions...", LogLevel.INFO)
        request_permissions(permissions, self._on_permissions_callback)

    def _on_keyboard(self, window, key, scancode, codepoint, modifier):
        """
        Handles keyboard shortcuts.
        """
        if 'ctrl' in modifier:
            if codepoint == 'q':
                self.stop()
            elif codepoint == 's':
                if not self.is_scan_button_disabled:
                    self.scan_for_devices()
            elif codepoint == 'd':
                if not self.root.ids.disconnect_button.disabled:
                    self.disconnect_from_device()
            elif codepoint == 'l':
                self.clear_log()

    def build(self):
        config_path = os.path.join(self.user_data_dir, 'config.ini')
        self.config_manager = ConfigManager(config_path)
        self.scan_timeout = self.config_manager.get_setting('scan', 'timeout')

        # Set the initial theme
        theme_name = self.config_manager.get_setting('theme', 'name')
        theme_manager.set_theme(theme_name)

        self.ble_manager = BLEManager(
            device_discovered_callback=self._on_device_discovered,
            connection_status_callback=self._on_connection_status_changed,
            notification_callback=self.notification_handler,
            logger_callback=self.log_with_timestamp
        )
        self.characteristic_frames = {}
        self.device_frames = {}
        self.device_cache = DeviceCache()
        self.selected_device = None
        return MainLayout()

    def on_stop(self):
        self.ble_manager.shutdown()

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
            self.log_with_timestamp("Adapter discovery is currently only supported on Linux.", LogLevel.DEBUG)
        self.root.ids.adapter_spinner.values = adapters

    def on_adapter_selected(self, spinner, text):
        """
        Handles the selection of a Bluetooth adapter.
        """
        self.log_with_timestamp(f"Adapter selected: {text}", LogLevel.INFO)
        if platform.system() == "Linux" and text != "Default":
            try:
                result = subprocess.run(['hciconfig', '-a', text], capture_output=True, text=True, check=True)
                self.log_with_timestamp(f"--- Adapter Info for {text} ---\n{result.stdout.strip()}\n--------------------", LogLevel.DEBUG)
            except (FileNotFoundError, subprocess.CalledProcessError) as e:
                self.log_with_timestamp(f"Could not get info for adapter {text}: {e}", LogLevel.ERROR)

    def scan_for_devices(self, *args):
        """Initiates a scan for nearby BLE devices."""
        self.is_scan_button_disabled = True
        self.root.ids.scan_button.text = "Scanning..."
        self.root.ids.device_list.clear_widgets()
        self.device_frames = {}
        self.log_with_timestamp("Scan started...", LogLevel.INFO)
        adapter = self.root.ids.adapter_spinner.text
        adapter = adapter if adapter != "Default" else None

        try:
            timeout = float(self.scan_timeout)
        except ValueError:
            self.log_with_timestamp("Invalid scan timeout. Please enter a number.", LogLevel.ERROR)
            self.is_scan_button_disabled = False
            self.root.ids.scan_button.text = "Scan"
            return

        self.ble_manager.scan_for_devices(adapter, timeout)
        Clock.schedule_once(self.on_scan_finished, timeout + 0.5)

    def on_scan_finished(self, *args):
        self.log_with_timestamp("Scan stopped.", LogLevel.INFO)
        self.is_scan_button_disabled = False
        self.root.ids.scan_button.text = "Scan"

    def filter_devices(self, search_term):
        """Filters the device list based on the search term."""
        search_term = search_term.lower()
        for address, frame in self.device_frames.items():
            device_name = (frame.device.name or "Unknown").lower()
            device_address = frame.device.address.lower()
            if search_term in device_name or search_term in device_address:
                if frame.parent is None:
                    self.root.ids.device_list.add_widget(frame)
            else:
                if frame.parent is not None:
                    self.root.ids.device_list.remove_widget(frame)

    def _on_device_discovered(self, device: BLEDevice, adv_data: AdvertisementData):
        """Callback for when a device is discovered."""
        Clock.schedule_once(lambda dt: self._populate_device_ui(device, adv_data))

    def _populate_device_ui(self, device: BLEDevice, adv_data: AdvertisementData):
        """
        Populates the UI with a discovered BLE device.
        """
        self.log_with_timestamp(f"Found device: {device.address} ({device.name or 'Unknown'}) RSSI: {adv_data.rssi}", LogLevel.DEBUG)
        frame = DeviceFrameKivy(device=device, adv_data=adv_data)
        self.device_frames[device.address] = frame
        self.root.ids.device_list.add_widget(frame)

    def connect_to_device(self, device: BLEDevice):
        """Connects to the selected device."""
        self.selected_device = device
        self.log_with_timestamp(f"Connecting to {device.address} ({device.name})...", LogLevel.INFO)
        adapter = self.root.ids.adapter_spinner.text
        adapter = adapter if adapter != "Default" else None
        self.ble_manager.connect_to_device(device.address, adapter)

    def disconnect_from_device(self, *args):
        """Initiates a manual disconnection from the connected device."""
        if self.ble_manager and self.ble_manager.client and self.ble_manager.client.is_connected:
            self.log_with_timestamp("Disconnect button pressed.", LogLevel.INFO)
            self.ble_manager.disconnect_from_device()

    def _on_connection_status_changed(self, is_connected: bool):
        """Callback for connection status changes."""
        Clock.schedule_once(lambda dt: self._update_connection_ui(is_connected))

    def _update_connection_ui(self, is_connected: bool):
        """Updates the UI based on the connection status."""
        if is_connected:
            self.log_with_timestamp("Device connected.", LogLevel.SUCCESS)
            self.root.ids.disconnect_button.disabled = False
            self.root.ids.read_all_button.disabled = False
            self.discover_attributes()
        else:
            # The BLEManager now logs the disconnection event.
            # We just need to update the UI state.
            self.root.ids.disconnect_button.disabled = True
            self.root.ids.read_all_button.disabled = True
            self.root.ids.characteristic_list.clear_widgets()
            self.characteristic_frames = {}

    def discover_attributes(self):
        """Discovers and displays the services and characteristics of the connected device."""
        self.root.ids.characteristic_list.clear_widgets()
        self.characteristic_frames = {}

        cached_services_data = None
        if self.selected_device:
            cached_services_data = self.device_cache.load_device(self.selected_device.address)
            if cached_services_data:
                self.log_with_timestamp("Loading services from cache...", LogLevel.DEBUG)
                cached_services = [CachedService(s) for s in cached_services_data]
                all_characteristics = [char for service in cached_services for char in service.characteristics]
                all_characteristics.sort(key=lambda c: (c.service_uuid, c.uuid))
                self.populate_characteristic_ui(all_characteristics)
                self.log_with_timestamp("Finished loading from cache.", LogLevel.DEBUG)

        if self.ble_manager.client:
            if not cached_services_data:
                all_characteristics = [char for service in self.ble_manager.client.services for char in service.characteristics]
                all_characteristics.sort(key=lambda c: (c.service_uuid, c.uuid))
                self.populate_characteristic_ui(all_characteristics)

            Clock.schedule_once(lambda dt: self._check_for_attribute_diffs(cached_services_data), 0.1)

    def populate_characteristic_ui(self, characteristics):
        service_frames = {}
        for char in characteristics:
            service_uuid = str(char.service_uuid)
            if service_uuid not in service_frames:
                service_name = GATT_SERVICES.get(service_uuid.split("-")[0].lstrip("0").lower(), "Unknown Service")
                sf = CollapsibleFrameKivy(title=f"Service: {service_name} ({service_uuid})")
                self.root.ids.characteristic_list.add_widget(sf)
                service_frames[service_uuid] = sf

            char_frame = CharacteristicFrameKivy(characteristic=char)
            self.characteristic_frames[char.uuid] = char_frame
            service_frames[service_uuid].add_content(char_frame)

            if "notify" not in char.properties and "indicate" not in char.properties:
                char_frame.ids.subscribe_button.disabled = True

            char_frame.ids.read_button.bind(on_release=partial(self.read_characteristic, char, char_frame))
            char_frame.ids.write_button.bind(on_release=partial(self.write_characteristic, char, char_frame))
            char_frame.ids.subscribe_button.bind(on_state=partial(self.toggle_subscription, char, char_frame))

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
                self.read_descriptor(user_desc, char_frame.ids.user_description_label)


    def _check_for_attribute_diffs(self, cached_services):
        if self.ble_manager.client:
            self.log_with_timestamp("Checking for attribute differences...", LogLevel.DEBUG)
            live_services = [service_to_dict(s) for s in self.ble_manager.client.services]

            if cached_services:
                diffs = self.device_cache.compare_services(cached_services, live_services)
                if diffs:
                    self.log_with_timestamp("Differences found between cache and live data:", LogLevel.INFO)
                    for diff in diffs:
                        self.log_with_timestamp(f"- {diff}", LogLevel.INFO)
                    self.log_with_timestamp("Refreshing UI with live data...", LogLevel.INFO)
                    self.discover_attributes()
                else:
                    self.log_with_timestamp("No differences found.", LogLevel.DEBUG)

            self.device_cache.save_device(self.ble_manager.client)

    def read_all_characteristics(self, *args):
        """Initiates a read operation for all readable characteristics."""
        self.log_with_timestamp("--- Reading all readable characteristics ---", LogLevel.INFO)
        for char_frame in self.characteristic_frames.values():
            if "read" in char_frame.characteristic.properties:
                self.read_characteristic(char_frame.characteristic, char_frame)

    def clear_log(self, *args):
        """Clears the debug log text box."""
        self.log_with_timestamp("Clearing log...", LogLevel.INFO)
        self.root.ids.log_view.text = ""

    def show_save_dialog(self, *args):
        """Shows the save file dialog."""
        self.log_with_timestamp("Showing save log dialog...", LogLevel.INFO)
        content = SaveDialog(save_callback=self.save_log, dismiss_callback=self.dismiss_popup)
        self.popup = Popup(title="Save Log", content=content, size_hint=(0.9, 0.9))
        self.popup.open()

    def dismiss_popup(self):
        self.popup.dismiss()

    def save_log(self, path, selection):
        """Saves the content of the debug log to a file."""
        if not selection:
            return
        filepath = os.path.join(path, selection[0])
        log_content = self.root.ids.log_view.text
        try:
            with open(filepath, "w") as f:
                f.write(log_content)
            self.log_with_timestamp(f"Log saved to {filepath}", LogLevel.SUCCESS)
        except IOError as e:
            self.log_with_timestamp(f"Error saving log: {e}", LogLevel.ERROR)
        self.dismiss_popup()

    def read_characteristic(self, characteristic, char_frame, *args):
        self.ble_manager.read_characteristic(characteristic.uuid, lambda value: Clock.schedule_once(lambda dt: self.on_characteristic_read(char_frame, value)))

    def on_characteristic_read(self, char_frame, value):
        if value is not None:
            char_frame.raw_value = value
            display_format = char_frame.ids.format_spinner.text
            self.log_with_timestamp(f"Value read from {char_frame.char_uuid} ({display_format}): {char_frame.char_value}", LogLevel.SUCCESS)
            char_frame.ids.value_input.background_color = (0, 1, 0, 1) # Green for success
            Clock.schedule_once(lambda dt: self.reset_char_color(char_frame), 0.5)
        else:
            self.log_with_timestamp(f"Failed to read from {char_frame.char_uuid}", LogLevel.ERROR)

    def write_characteristic(self, characteristic, char_frame, *args):
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

        self.ble_manager.write_characteristic(
            characteristic.uuid,
            write_value,
            lambda success: Clock.schedule_once(
                lambda dt: self.on_characteristic_write(char_frame, success, characteristic, value_str, write_mode)
            )
        )

    def on_characteristic_write(self, char_frame, success, characteristic, value_written, write_mode):
        if success:
            self.log_with_timestamp(f"Value written to {char_frame.char_uuid} ({write_mode}): {value_written}", LogLevel.SUCCESS)
            if "read" in characteristic.properties:
                self.read_characteristic(characteristic, char_frame)
        else:
            self.log_with_timestamp(f"Write Error on {char_frame.char_uuid}", LogLevel.ERROR)
            char_frame.ids.value_input.background_color = (1, 0.6, 0.6, 1)

    def reset_char_color(self, char_frame):
        char_frame.ids.value_input.background_color = (1, 1, 1, 1)

    def read_descriptor(self, descriptor, desc_frame, *args):
        callback = partial(self.on_descriptor_read, descriptor, desc_frame)
        self.ble_manager.read_descriptor(descriptor.handle, lambda value: Clock.schedule_once(lambda dt: callback(value)))

    def on_descriptor_read(self, descriptor, desc_frame, value):
        if value is not None:
            if isinstance(desc_frame, Label):
                desc_frame.text = f"{value.decode('utf-8')}"
            else:
                desc_frame.desc_value = value.hex()
            self.log_with_timestamp(f"Value read from {descriptor.uuid}: {value.hex()}", LogLevel.SUCCESS)
        else:
            self.log_with_timestamp(f"Failed to read from {descriptor.uuid}", LogLevel.ERROR)

    def write_descriptor(self, descriptor, desc_frame, *args):
        value_str = desc_frame.ids.value_input.text
        try:
            write_value = bytes.fromhex(value_str)
        except ValueError:
            self.log_with_timestamp(f"Invalid hex value for write on {descriptor.uuid}", LogLevel.ERROR)
            return

        self.ble_manager.write_descriptor(descriptor.handle, write_value, lambda success: Clock.schedule_once(lambda dt: self.on_descriptor_write(desc_frame, success)))

    def on_descriptor_write(self, desc_frame, success):
        if success:
            self.log_with_timestamp(f"Value written to {desc_frame.desc_uuid}", LogLevel.SUCCESS)
        else:
            self.log_with_timestamp(f"Write Error on {desc_frame.desc_uuid}", LogLevel.ERROR)

    def toggle_subscription(self, characteristic, char_frame, widget, state):
        if state == 'down':
            self.ble_manager.subscribe_to_characteristic(characteristic.uuid)
            self.log_with_timestamp(f"Subscribed to {characteristic.uuid}", LogLevel.INFO)
        else:
            self.ble_manager.unsubscribe_from_characteristic(characteristic.uuid)
            self.log_with_timestamp(f"Unsubscribed from {characteristic.uuid}", LogLevel.INFO)

    def notification_handler(self, characteristic, data):
        """Handles incoming notifications."""
        Clock.schedule_once(lambda dt: self.on_notification(characteristic, data))

    def on_notification(self, characteristic, data):
        if characteristic.uuid in self.characteristic_frames:
            char_frame = self.characteristic_frames[characteristic.uuid]
            char_frame.raw_value = data
            display_format = char_frame.ids.format_spinner.text
            self.log_with_timestamp(f"Notification from {characteristic.uuid} ({display_format}): {char_frame.char_value}", LogLevel.INFO)

    def log_with_timestamp(self, message: str, level: LogLevel = LogLevel.INFO):
        """
        Logs a message with a timestamp and level in a thread-safe manner.
        Schedules the actual UI update on the main Kivy thread.
        """
        Clock.schedule_once(lambda dt: self._log_on_main_thread(message, level))

    def _log_on_main_thread(self, message: str, level: LogLevel):
        """Performs the actual log update on the main thread."""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        log_message = f"[{timestamp}] [{level.value}] {message}\n"
        self.root.ids.log_view.text += log_message

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
        content = LoadDialog(load_callback=self.upload_firmware, dismiss_callback=self.dismiss_popup)
        self.popup = Popup(title="Load Firmware", content=content, size_hint=(0.9, 0.9))
        self.popup.open()

    def upload_firmware(self, path, selection):
        """Handles the firmware upload process."""
        if not selection:
            self.dismiss_popup()
            return
        filepath = os.path.join(path, selection[0])
        self.log_with_timestamp(f"Starting OTA upload from {filepath}", LogLevel.INFO)
        self.ble_manager.start_ota_upload(filepath, self.ota_progress_callback)
        self.dismiss_popup()
        if self.ota_popup:
            self.ota_popup.ids.file_label.text = filepath

    def ota_progress_callback(self, progress):
        """Callback for OTA progress updates."""
        if self.ota_popup:
            self.ota_popup.ids.progress_bar.value = progress
        if progress == 100:
            self.log_with_timestamp("OTA operation completed.", LogLevel.SUCCESS)


if __name__ == '__main__':
    BLEScannerApp().run()
