from kivy.core.window import Window
from kivy.uix.label import Label
from kivy.properties import StringProperty, BooleanProperty, ObjectProperty
from kivy.uix.button import Button


class HoverBehavior(object):
    """Custom hover behavior implementation."""
    hovered = BooleanProperty(False)
    border_point = ObjectProperty(None)

    def __init__(self, **kwargs):
        self.register_event_type('on_enter')
        self.register_event_type('on_leave')
        Window.bind(mouse_pos=self.on_mouse_pos)
        super(HoverBehavior, self).__init__(**kwargs)

    def on_mouse_pos(self, *args):
        if not self.get_root_window():
            return
        pos = args[1]
        if self.parent:
            inside = self.collide_point(*self.to_widget(*pos))
            if self.hovered == inside:
                return
            self.border_point = pos
            self.hovered = inside
            if inside:
                self.dispatch('on_enter')
            else:
                self.dispatch('on_leave')

    def on_enter(self):
        pass

    def on_leave(self):
        pass


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


class TooltipButton(TooltipMixin, HoverBehavior, Button):
    pass
