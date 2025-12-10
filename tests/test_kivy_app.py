import pytest
import struct
from kivy.app import App
from device_frame_kivy import DeviceFrameKivy
from characteristic_frame_kivy import CharacteristicFrameKivy
from collapsible_frame_kivy import CollapsibleFrameKivy
from main import BLEScannerApp
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.service import BleakGATTService

class MockService(BleakGATTService):
    def __init__(self):
        super().__init__(obj=None, handle=1, uuid="00001800-0000-1000-8000-00805f9b34fb")

class MockCharacteristic(BleakGATTCharacteristic):
    def __init__(self, uuid="00002a00-0000-1000-8000-00805f9b34fb", properties=None):
        super().__init__(
            obj=None,
            handle=1,
            uuid=uuid,
            properties=properties or ["read", "write"],
            max_write_without_response_size=lambda: 20,
            service=MockService()
        )


class TestKivyApp:
    @pytest.fixture(scope="session", autouse=True)
    def app(self):
        # This is a hack to allow the test to run without a Kivy App instance
        if not App.get_running_app():
            app = BLEScannerApp()
            app.root = None # We don't need a root widget for this test
            return app
        return App.get_running_app()

    def test_app_instantiation(self, app):
        """
        Tests that the main application can be instantiated without errors.
        """
        assert app is not None

    def test_device_frame_instantiation(self):
        """
        Tests that the DeviceFrameKivy widget can be instantiated correctly.
        """
        device = BLEDevice('00:11:22:33:44:55', 'Test Device', {})
        adv_data = AdvertisementData(
            local_name='Test Device',
            manufacturer_data={},
            service_data={},
            service_uuids=[],
            rssi=-50,
            tx_power=0,
            platform_data=()
        )
        device_frame = DeviceFrameKivy(device=device, adv_data=adv_data)
        assert device_frame.device_name == 'Test Device'
        assert device_frame.device_address == '00:11:22:33:44:55'
        assert device_frame.device_rssi == 'RSSI: -50'

    def test_characteristic_frame_instantiation(self):
        """
        Tests that the CharacteristicFrameKivy widget can be instantiated correctly.
        """
        char = MockCharacteristic()
        char_frame = CharacteristicFrameKivy(characteristic=char)
        assert char_frame.char_uuid == "00002a00-0000-1000-8000-00805f9b34fb"
        assert char_frame.char_properties == "R/W"

    def test_collapsible_frame_instantiation_and_toggle(self):
        """
        Tests that the CollapsibleFrameKivy widget can be instantiated and toggled.
        """
        collapsible_frame = CollapsibleFrameKivy(title="Test Frame")
        assert collapsible_frame.title == "Test Frame"
        assert not collapsible_frame.collapsed
        collapsible_frame.toggle_collapse()
        assert collapsible_frame.collapsed
        collapsible_frame.toggle_collapse()
        assert not collapsible_frame.collapsed

    def test_data_format_conversion(self):
        """
        Tests the data format conversion logic.
        """
        char = MockCharacteristic()
        char_frame = CharacteristicFrameKivy(characteristic=char)

        # Test Hex
        char_frame.raw_value = b'\x01\x02\x03'
        char_frame.on_format_change('Hex')
        assert char_frame.char_value == '010203'

        # Test ASCII
        char_frame.raw_value = b'Hello'
        char_frame.on_format_change('ASCII')
        assert char_frame.char_value == 'Hello'

        # Test Int8
        char_frame.raw_value = b'\xfd'
        char_frame.on_format_change('Int8')
        assert char_frame.char_value == '-3'

        # Test UInt8
        char_frame.raw_value = b'\xfd'
        char_frame.on_format_change('UInt8')
        assert char_frame.char_value == '253'

        # Test Int16
        char_frame.raw_value = b'\xfd\xff'
        char_frame.on_format_change('Int16')
        assert char_frame.char_value == '-3'

        # Test UInt16
        char_frame.raw_value = b'\xfd\xff'
        char_frame.on_format_change('UInt16')
        assert char_frame.char_value == '65533'

        # Test Float32
        char_frame.raw_value = struct.pack('<f', 3.14)
        char_frame.on_format_change('Float32')
        assert abs(float(char_frame.char_value) - 3.14) < 0.001

        # Test Invalid Format
        char_frame.raw_value = b'\x01\x02\x03'
        char_frame.on_format_change('Int16') # Wrong number of bytes
        assert char_frame.char_value == "Invalid Format"
