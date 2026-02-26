from kivy.uix.popup import Popup
from kivy.properties import ObjectProperty

class SettingsPopup(Popup):
    app = ObjectProperty(None)

    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app

    def add_tool_settings(self, widget):
        self.ids.settings_tabs.add_widget(widget)

    def select_tab_by_name(self, tab_text):
        """Switches to the tab with the given text if it exists."""
        for tab in self.ids.settings_tabs.tab_list:
            if tab.text == tab_text:
                self.ids.settings_tabs.switch_to(tab)
                break

    def save_settings(self):
        # This will be implemented by each tool's settings panel
        for panel in self.ids.settings_tabs.tab_list:
            if hasattr(panel.content, 'save_settings'):
                panel.content.save_settings()
        self.dismiss()
