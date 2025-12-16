from kivymd.uix.boxlayout import MDBoxLayout
from kivy.properties import DictProperty, ObjectProperty

class ListItem(MDBoxLayout):
    data = DictProperty()
    app = ObjectProperty()

    def on_data(self, instance, value):
        self.populate()

    def on_app(self, instance, value):
        self.populate()

    def populate(self):
        if not self.app or not self.data:
            return

        self.clear_widgets()
        if self.data['viewclass'] == 'ServiceHeader':
            header = ServiceHeader(text=self.data['text'])
            header.bind(on_release=lambda x: self.app.toggle_service_expansion(self.data))
            self.add_widget(header)
        elif self.data['viewclass'] == 'CharacteristicFrameKivy':
            char_frame = self.app._create_and_bind_characteristic_frame(self.data['characteristic'])
            self.add_widget(char_frame)

from kivymd.uix.button import MDRaisedButton
class ServiceHeader(MDRaisedButton):
    pass
