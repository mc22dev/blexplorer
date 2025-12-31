from kivy.core.window import Window
from kivy.uix.label import Label
from kivy.properties import StringProperty
from kivy.uix.button import Button
from kivy.uix.behaviors import HoverBehavior


class Tooltip(Label):
    pass


class TooltipMixin:
    tooltip_text = StringProperty('')
    tooltip = None

    def on_enter(self):
        if self.tooltip_text:
            self.tooltip = Tooltip(text=self.tooltip_text)
            Window.add_widget(self.tooltip)
            Window.bind(mouse_pos=self.on_mouse_pos)

    def on_leave(self):
        if self.tooltip:
            Window.remove_widget(self.tooltip)
            self.tooltip = None
            Window.unbind(mouse_pos=self.on_mouse_pos)

    def on_mouse_pos(self, *args):
        if self.tooltip:
            pos = args[1]
            self.tooltip.pos = (pos[0] + 15, pos[1] + 15)


# Corrected implementation
class TooltipButton(TooltipMixin, HoverBehavior, Button):
    pass
