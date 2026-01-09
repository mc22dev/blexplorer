from kivy.uix.boxlayout import BoxLayout
from kivy.properties import StringProperty, BooleanProperty


class CollapsibleFrameKivy(BoxLayout):
    title = StringProperty('')
    collapsed = BooleanProperty(False)
    content_widgets = []

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'

    def toggle_collapse(self):
        self.collapsed = not self.collapsed

    def add_content(self, widget):
        self.ids.content.add_widget(widget)
