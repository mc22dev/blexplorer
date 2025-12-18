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
        self.config = configparser.ConfigParser()
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
            'ota': {
                'service_uuid': '00010203-0405-0607-0809-0a0b0c0d1912',
                'characteristic_uuid': '00010203-0405-0607-0809-0a0b0c0d2b12'
            }
        }
        self._load_or_create_config()

    def _load_or_create_config(self):
        """Loads the config file, or creates it with defaults if it doesn't exist."""
        if not os.path.exists(self.config_path):
            self._create_default_config()
        else:
            self.config.read(self.config_path)
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

    def get_setting(self, section: str, option: str) -> str:
        """
        Gets a setting value for a given section and option.

        Args:
            section: The section in the INI file.
            option: The option within the section.

        Returns:
            The value of the setting as a string, or the default value if not found.
        """
        return self.config.get(section, option, fallback=self.defaults.get(section, {}).get(option))

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
        self._create_default_config()
