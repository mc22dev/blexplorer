from kivy.uix.boxlayout import BoxLayout
from kivy.properties import ObjectProperty, StringProperty

from bleak.backends.descriptor import BleakGATTDescriptor


class DescriptorFrameKivy(BoxLayout):
    descriptor = ObjectProperty(None)
    desc_uuid = StringProperty('')
    desc_value = StringProperty('')

    def __init__(self, descriptor: BleakGATTDescriptor, **kwargs):
        super().__init__(**kwargs)
        self.descriptor = descriptor
        self.desc_uuid = descriptor.uuid
