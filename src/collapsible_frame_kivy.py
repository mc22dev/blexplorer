from kivy.uix.boxlayout import BoxLayout
from kivy.properties import StringProperty, BooleanProperty, ListProperty, ObjectProperty


class CollapsibleFrameKivy(BoxLayout):
    title = StringProperty("")
    is_expanded = BooleanProperty(True)
    characteristics = ListProperty()
    populate_callback = ObjectProperty()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._content_populated = False

    def on_expansion(self):
        """Lazy load the content of the frame."""
        if self.is_expanded and not self._content_populated and self.populate_callback:
            for char in self.characteristics:
                char_frame = self.populate_callback(char)
                self.add_content(char_frame)
            self._content_populated = True

    def add_content(self, widget):
        self.ids.content_box.add_widget(widget)

    def clear_content(self):
        """Clears the content of the frame."""
        self.ids.content_box.clear_widgets()
        self._content_populated = False
