from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.label import Label
import os

class FileChooserDialog(BoxLayout):
    def __init__(self, title, callback, dismiss_callback, mode='open', **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.callback = callback
        self.dismiss_callback = dismiss_callback
        self.mode = mode

        self.file_chooser = FileChooserListView(path=os.getcwd())
        self.file_chooser.bind(on_submit=self.on_file_submit)
        self.add_widget(self.file_chooser)

        if self.mode == 'save':
            self.filename_input = TextInput(text='', hint_text='Enter filename', multiline=False, size_hint_y=None, height=40)
            self.add_widget(self.filename_input)

        button_box = BoxLayout(size_hint_y=None, height=40)
        self.action_button = Button(text=title)
        self.action_button.bind(on_release=self.on_action)
        button_box.add_widget(self.action_button)

        self.cancel_button = Button(text='Cancel')
        self.cancel_button.bind(on_release=self.on_cancel)
        button_box.add_widget(self.cancel_button)
        self.add_widget(button_box)

    def on_file_submit(self, instance, selection, touch):
        if not selection:
            return

        if self.mode == 'save':
            self.filename_input.text = os.path.basename(selection[0])

        self.on_action(None)

    def on_action(self, instance):
        if self.mode == 'save':
            filename = self.filename_input.text
            if not filename:
                return

            full_path = os.path.join(self.file_chooser.path, filename)
            if os.path.exists(full_path):
                self.show_overwrite_confirmation(full_path)
            else:
                self.callback(self.file_chooser.path, [full_path])
        else:
            self.callback(self.file_chooser.path, self.file_chooser.selection)

    def show_overwrite_confirmation(self, filepath):
        content = BoxLayout(orientation='vertical', padding=10, spacing=10)
        content.add_widget(Label(text=f"File '{os.path.basename(filepath)}' already exists.\nDo you want to overwrite it?"))

        btns = BoxLayout(size_hint_y=None, height=40, spacing=10)
        yes_btn = Button(text="Yes")
        no_btn = Button(text="No")
        btns.add_widget(yes_btn)
        btns.add_widget(no_btn)
        content.add_widget(btns)

        popup = Popup(title="Confirm Overwrite", content=content, size_hint=(0.6, 0.4))

        def on_yes(instance):
            popup.dismiss()
            self.callback(self.file_chooser.path, [filepath])

        yes_btn.bind(on_release=on_yes)
        no_btn.bind(on_release=popup.dismiss)
        popup.open()

    def on_cancel(self, instance):
        self.dismiss_callback()
