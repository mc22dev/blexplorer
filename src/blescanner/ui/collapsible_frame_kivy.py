from kivy.uix.boxlayout import BoxLayout
from kivy.properties import StringProperty, BooleanProperty, ListProperty, ObjectProperty


class CollapsibleFrameKivy(BoxLayout):
    title = StringProperty("")
    is_expanded = BooleanProperty(True)
    characteristics = ListProperty([])
    populate_callback = ObjectProperty(None)
    _is_populated = False

    def on_is_expanded(self, instance, value):
        if value and not self._is_populated:
            self._populate_content()

    def _populate_content(self):
        if self.populate_callback:
            for char in self.characteristics:
                widget = self.populate_callback(char)
                self.add_widget(widget)
            self._is_populated = True

    def add_widget(self, widget, index=0, canvas=None):
        if len(self.children) < 2:  # First child is the layout, second is the content_box
            super().add_widget(widget, index, canvas)
        else:
            self.ids.content_box.add_widget(widget, index, canvas)

    def remove_widget(self, widget):
        if widget in self.children:
            super().remove_widget(widget)
        else:
            self.ids.content_box.remove_widget(widget)

    def clear_widgets(self, children=None):
        if children is None:
            self.ids.content_box.clear_widgets()
        else:
            for child in children:
                self.remove_widget(child)
