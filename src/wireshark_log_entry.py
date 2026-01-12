from kivy.uix.boxlayout import BoxLayout
from kivy.properties import StringProperty, NumericProperty


class WiresharkLogEntry(BoxLayout):
    """
    A widget representing a single log entry in the Wireshark view.
    """
    time = StringProperty('')
    rssi = NumericProperty(0)
    address = StringProperty('')
    service_uuids = StringProperty('')
    manufacturer_data = StringProperty('')
    decoded_data = StringProperty('')
