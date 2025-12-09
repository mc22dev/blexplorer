from kivy.uix.boxlayout import BoxLayout
from kivy.properties import ObjectProperty, StringProperty

from bleak.backends.characteristic import BleakGATTCharacteristic


class CharacteristicFrameKivy(BoxLayout):
    characteristic = ObjectProperty(None)
    char_uuid = StringProperty('')
    char_properties = StringProperty('')
    char_value = StringProperty('')

    def __init__(self, characteristic: BleakGATTCharacteristic, **kwargs):
        super().__init__(**kwargs)
        self.characteristic = characteristic
        self.char_uuid = characteristic.uuid
        self.char_properties = ", ".join(characteristic.properties)
