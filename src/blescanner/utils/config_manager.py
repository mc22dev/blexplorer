"""
Manages application configuration settings using an INI file.

This module provides a ConfigManager class to handle loading, saving,
and restoring application settings from a configuration file.
"""
import configparser
import os

class ConfigManager:
    """Handles reading and writing of application settings to an INI file."""

    def __init__(self, config_path: str):
        """
        Initializes the ConfigManager.

        Args:
            config_path: The full path to the configuration file.
        """
        self.config_path = config_path
        self.config = configparser.ConfigParser(delimiters=('=',))
        self.defaults = {
            'scan': {
                'timeout': '5.0'
            },
            'theme': {
                'name': 'Dark'
            },
            'bluetooth': {
                'adapter': 'Default'
            },
            'ble': {
                'library': 'bleak'
            },
            'ota': {
                'service_uuid': '00010203-0405-0607-0809-0a0b0c0d1912',
                'characteristic_uuid': '00010203-0405-0607-0809-0a0b0c0d2b12'
            },
            'auto_connect': {
                'enabled': 'False',
                'filter': ''
            },
            'graph': {
                'rssi_min': '-110',
                'rssi_max': '-20'
            },
            'logging': {
                'level': 'DEBUG'
            },
            'general': {
                'last_tool_id': 'ble_scanner',
                'last_tool_name': 'BLE Scanner'
            },
            'serial_monitor': {
                'font_name': 'Roboto',
                'font_size': '12',
                'last_used_port': '',
                'eol': 'None',
                'char_delay': '0'
            },
            'noise_monitor': {
                'alarm_sound': 'alert.wav',
                'sensitivity': '1.0',
                'num_bars': '9',
                'average_time': '500',
                'alarm_cooldown': '2'
            },
            'ftp_server': {
                'port': '2121',
                'user': 'user',
                'password': 'password',
                'directory': '.',
                'read_only': 'False'
            },
            'device_names': {}
        }
        self._load_or_create_config()

    def get_device_name(self, address: str) -> str:
        """
        Gets the custom name for a given device address.

        Args:
            address: The MAC address of the device.

        Returns:
            The custom name as a string, or None if not found.
        """
        return self.get_setting('device_names', address)

    def set_device_name(self, address: str, name: str):
        """
        Sets a custom name for a device and saves the configuration.

        Args:
            address: The MAC address of the device.
            name: The custom name to set.
        """
        self.set_setting('device_names', address, name)

    def _load_or_create_config(self):
        """Loads the config file, or creates it with defaults if it doesn't exist."""
        if not os.path.exists(self.config_path):
            self._create_default_config()
        else:
            try:
                self.config.read(self.config_path)
            except configparser.DuplicateOptionError as e:
                print(f"Error: Corrupt config file detected at {self.config_path}. Details: {e}")
                print("Resetting configuration to defaults.")
                self.restore_defaults()
                return  # Exit after resetting to avoid further processing

            # Ensure that any new default settings are added to an existing config file
            needs_saving = False
            for section, options in self.defaults.items():
                if not self.config.has_section(section):
                    self.config.add_section(section)
                    needs_saving = True
                for option, value in options.items():
                    if not self.config.has_option(section, option):
                        self.config.set(section, option, value)
                        needs_saving = True
            if needs_saving:
                self._save_config()

    def _save_config(self):
        """Saves the current configuration to the file."""
        with open(self.config_path, 'w') as configfile:
            self.config.write(configfile)

    def _create_default_config(self):
        """Creates a new config file with default values."""
        # Ensure the directory for the config file exists
        config_dir = os.path.dirname(self.config_path)
        if config_dir:
            os.makedirs(config_dir, exist_ok=True)
        self.config.read_dict(self.defaults)
        self._save_config()

    def get_setting(self, section: str, option: str, default=None) -> str:
        """
        Gets a setting value for a given section and option.

        Args:
            section: The section in the INI file.
            option: The option within the section.
            default: An optional fallback value if the setting is not found.

        Returns:
            The value of the setting as a string, or the default value if not found.
        """
        fallback_value = default
        if fallback_value is None:
            fallback_value = self.defaults.get(section, {}).get(option)
        return self.config.get(section, option, fallback=fallback_value)


    def get_default_setting(self, section: str, option: str) -> str:
        """
        Gets a default setting value for a given section and option.

        Args:
            section: The section in the INI file.
            option: The option within the section.

        Returns:
            The default value of the setting as a string, or None if not found.
        """
        return self.defaults.get(section, {}).get(option)

    def set_setting(self, section: str, option: str, value):
        """
        Sets a setting value and saves the configuration.

        Args:
            section: The section in the INI file.
            option: The option within the section.
            value: The value to set. It will be converted to a string.
        """
        if not self.config.has_section(section):
            self.config.add_section(section)
        self.config.set(section, option, str(value))
        self._save_config()

    def restore_defaults(self):
        """Restores the configuration to the default settings."""
        # This removes the existing file and recreates it with defaults
        if os.path.exists(self.config_path):
            os.remove(self.config_path)
        # Re-initialize the config parser to clear any old state
        self.config = configparser.ConfigParser(delimiters=('=',))
        self._create_default_config()
