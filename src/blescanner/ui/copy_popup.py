from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.checkbox import CheckBox
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.core.window import Window
from kivy.core.clipboard import Clipboard

class CopyPopup(Popup):
    def __init__(self, title, data_dict, selection_state, save_callback, **kwargs):
        content = BoxLayout(orientation='vertical', padding="8dp", spacing="8dp")
        super().__init__(title=title, content=content, size_hint=(0.9, 0.9), **kwargs)

        self._data_dict = data_dict
        self._selection_state = selection_state
        self._save_callback = save_callback
        self._checkboxes = {}

        preview_input = TextInput(readonly=True, size_hint_y=None, height='100dp', multiline=True)

        def update_preview_text(*args):
            to_copy = []
            for key, chk in self._checkboxes.items():
                if chk.active:
                    # The value is now nested in the data_dict
                    to_copy.append(str(self._data_dict[key]['value']))
            preview_input.text = "\n".join(to_copy)

        scroll_content = BoxLayout(orientation='vertical', size_hint_y=None)
        scroll_content.bind(minimum_height=scroll_content.setter('height'))

        for key, data in self._data_dict.items():
            if data['value']:
                box = BoxLayout(orientation='horizontal', size_hint_y=None, height='60dp', spacing=5)

                chk = CheckBox(size_hint_x=None, width='48dp', active=key in self._selection_state)
                chk.bind(active=update_preview_text)
                box.add_widget(chk)

                text_layout = BoxLayout(orientation='vertical')
                text_layout.add_widget(Label(text=data['name'], halign='left', size_hint_y=None, height='20dp', text_size=(Window.width * 0.6, None)))
                text_layout.add_widget(TextInput(text=str(data['value']), readonly=True, size_hint_y=None, height='30dp'))
                box.add_widget(text_layout)

                scroll_content.add_widget(box)
                self._checkboxes[key] = chk

        select_buttons = BoxLayout(size_hint_y=None, height='30dp', spacing=5)
        select_all_button = Button(text="Select All")
        deselect_all_button = Button(text="Deselect All")
        select_buttons.add_widget(select_all_button)
        select_buttons.add_widget(deselect_all_button)
        content.add_widget(select_buttons)

        def select_all(instance):
            for chk in self._checkboxes.values():
                chk.active = True
            update_preview_text()

        def deselect_all(instance):
            for chk in self._checkboxes.values():
                chk.active = False
            update_preview_text()

        select_all_button.bind(on_release=select_all)
        deselect_all_button.bind(on_release=deselect_all)

        scroll_view = ScrollView(size_hint=(1, 1))
        scroll_view.add_widget(scroll_content)
        content.add_widget(scroll_view)

        content.add_widget(Label(text="Preview:", size_hint_y=None, height='20dp'))
        content.add_widget(preview_input)

        copy_button = Button(text="Copy", size_hint_y=None, height='44dp')

        def do_copy(instance):
            Clipboard.copy(preview_input.text)
            self.dismiss()
            confirm_popup = Popup(title='Copied',
                                  content=Label(text='Selected info copied to clipboard.'),
                                  size_hint=(None, None), size=(400, 100))
            confirm_popup.open()

        copy_button.bind(on_release=do_copy)
        content.add_widget(copy_button)

        self.bind(on_dismiss=self._on_dismiss)
        update_preview_text() # Initial update

    def _on_dismiss(self, *args):
        new_selection_state = {key for key, chk in self._checkboxes.items() if chk.active}
        if self._save_callback:
            self._save_callback(new_selection_state)
