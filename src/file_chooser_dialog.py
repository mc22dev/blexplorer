from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.filechooser import FileChooserListView
import os

class FileChooserDialog(BoxLayout):
    def __init__(self, title, callback, dismiss_callback, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.callback = callback
        self.dismiss_callback = dismiss_callback

        self.file_chooser = FileChooserListView(path=os.getcwd())
        self.add_widget(self.file_chooser)

        button_box = BoxLayout(size_hint_y=None, height=40)
        self.action_button = Button(text=title)
        self.action_button.bind(on_release=self.on_action)
        button_box.add_widget(self.action_button)

        self.cancel_button = Button(text='Cancel')
        self.cancel_button.bind(on_release=self.on_cancel)
        button_box.add_widget(self.cancel_button)
        self.add_widget(button_box)

    def on_action(self, instance):
        self.callback(self.file_chooser.path, self.file_chooser.selection)

    def on_cancel(self, instance):
        self.dismiss_callback()
