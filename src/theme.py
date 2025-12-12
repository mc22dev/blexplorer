"""
Manages the visual theme for the application.

This module defines the color palettes for different themes and provides a
ThemeManager class that holds the current theme's colors as Kivy properties.
This allows UI elements to automatically update when the theme changes.
"""

from kivy.properties import ColorProperty, StringProperty
from kivy.event import EventDispatcher

# Define the color palettes for the themes
THEMES = {
    'Light': {
        'background': [1, 1, 1, 1],
        'text': [0, 0, 0, 1],
        'primary': [0.2, 0.5, 0.9, 1],
        'secondary': [0.8, 0.8, 0.8, 1],
        'success': [0.2, 0.8, 0.2, 1],
        'warning': [0.9, 0.9, 0.2, 1],
        'error': [0.9, 0.3, 0.3, 1],
        'input_bg': [0.95, 0.95, 0.95, 1],
        'input_fg': [0, 0, 0, 1],
        'disabled_fg': [0.5, 0.5, 0.5, 1],
        'header_bg': [0.9, 0.9, 0.9, 1],
        'button_bg': [0.85, 0.85, 0.85, 1],
        'button_fg': [0, 0, 0, 1],
    },
    'Dark': {
        'background': [0.1, 0.1, 0.1, 1],
        'text': [1, 1, 1, 1],
        'primary': [0.3, 0.6, 1, 1],
        'secondary': [0.3, 0.3, 0.3, 1],
        'success': [0.3, 0.9, 0.3, 1],
        'warning': [1, 1, 0.3, 1],
        'error': [1, 0.4, 0.4, 1],
        'input_bg': [0.2, 0.2, 0.2, 1],
        'input_fg': [1, 1, 1, 1],
        'disabled_fg': [0.6, 0.6, 0.6, 1],
        'header_bg': [0.2, 0.2, 0.2, 1],
        'button_bg': [0.25, 0.25, 0.25, 1],
        'button_fg': [1, 1, 1, 1],
    }
}


class ThemeManager(EventDispatcher):
    """Manages the application's theme."""
    name = StringProperty('Light')
    background = ColorProperty(THEMES['Light']['background'])
    text = ColorProperty(THEMES['Light']['text'])
    primary = ColorProperty(THEMES['Light']['primary'])
    secondary = ColorProperty(THEMES['Light']['secondary'])
    success = ColorProperty(THEMES['Light']['success'])
    warning = ColorProperty(THEMES['Light']['warning'])
    error = ColorProperty(THEMES['Light']['error'])
    input_bg = ColorProperty(THEMES['Light']['input_bg'])
    input_fg = ColorProperty(THEMES['Light']['input_fg'])
    disabled_fg = ColorProperty(THEMES['Light']['disabled_fg'])
    header_bg = ColorProperty(THEMES['Light']['header_bg'])
    button_bg = ColorProperty(THEMES['Light']['button_bg'])
    button_fg = ColorProperty(THEMES['Light']['button_fg'])

    def set_theme(self, theme_name: str):
        """
        Sets the application theme.

        Args:
            theme_name: The name of the theme to set ('Light' or 'Dark').
        """
        if theme_name in THEMES:
            self.name = theme_name
            theme = THEMES[theme_name]
            for key, value in theme.items():
                setattr(self, key, value)


# Global instance of the ThemeManager
theme_manager = ThemeManager()
