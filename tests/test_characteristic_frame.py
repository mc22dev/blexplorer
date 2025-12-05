import pytest
from unittest.mock import Mock, MagicMock
from characteristic_frame import CharacteristicFrame

@pytest.fixture
def mock_characteristic():
    char = Mock()
    char.uuid = "1234"
    char.properties = ["read", "write", "notify", "indicate"]
    char.descriptors = []
    return char

@pytest.fixture
def characteristic_frame(mock_characteristic):
    app = MagicMock()
    return CharacteristicFrame(
        master=app,
        characteristic=mock_characteristic,
        description="Test Characteristic",
        read_callback=Mock(),
        write_callback=Mock(),
        subscribe_callback=Mock(),
        unsubscribe_callback=Mock(),
        read_desc_callback=Mock(),
        write_desc_callback=Mock()
    )

def test_interpret_data_hex(characteristic_frame):
    """Test that the interpret_data method correctly formats a hex string."""
    raw_bytes = b"\x01\x02\x03\x04"
    characteristic_frame.update_value(raw_bytes)
    characteristic_frame.interpret_data("Hex")
    assert characteristic_frame.read_value_entry.get() == "01020304"
