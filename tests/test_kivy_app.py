import pytest
from kivy.app import App
from device_frame_kivy import DeviceFrameKivy
from characteristic_frame_kivy import CharacteristicFrameKivy
from collapsible_frame_kivy import CollapsibleFrameKivy
from main_kivy import BLEScannerApp
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
        assert char_frame.char_properties == "read, write"

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
