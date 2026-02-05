import pytest
from blescanner.tools.hex_editor.hex_editor import HexEditorScreen
from unittest.mock import MagicMock
from kivy.app import App

@pytest.fixture
def mock_app(monkeypatch):
    app = MagicMock(spec=App)
    app.root = MagicMock()
    app.ui_manager = MagicMock()
    monkeypatch.setattr(App, "get_running_app", lambda: app)
    return app

@pytest.fixture
def hex_editor(mock_app):
    screen = HexEditorScreen(name='hex_editor')
    screen.manager = MagicMock()
    screen.manager.current = 'hex_editor'
    screen.ids.search_input = MagicMock()
    screen.ids.search_input.focus = False
    screen.ids.replace_input = MagicMock()
    screen.ids.replace_input.focus = False
    screen.ids.rv = MagicMock()
    screen.data = bytearray(b"Hello World! This is a test.")
    return screen

def test_hex_editor_initial_data(hex_editor):
    assert len(hex_editor.data) == 28
    hex_editor.update_view_data()
    assert len(hex_editor.view_data) == 2 # 28 bytes / 16 = 1.75 -> 2 rows

def test_hex_editor_insert_byte(hex_editor):
    initial_len = len(hex_editor.data)
    hex_editor.cursor_offset = 5
    hex_editor.insert_byte()
    assert len(hex_editor.data) == initial_len + 1
    assert hex_editor.data[5] == 0

def test_hex_editor_delete_byte(hex_editor):
    initial_len = len(hex_editor.data)
    hex_editor.cursor_offset = 5
    hex_editor.delete_byte()
    assert len(hex_editor.data) == initial_len - 1
    # "Hello World" -> bytes: [72, 101, 108, 108, 111, 32, 87, 111, 114, 108, 100]
    # Index 5 is space (32). Deleting it makes index 5 'W' (87).
    assert hex_editor.data[5] == ord('W')

def test_hex_editor_search_ascii(hex_editor):
    hex_editor.cursor_offset = 0
    hex_editor.search("World", is_hex=False)
    assert hex_editor.cursor_offset == 6

def test_hex_editor_search_hex(hex_editor):
    hex_editor.cursor_offset = 0
    # "Hello" in hex: 48 65 6C 6C 6F
    hex_editor.search("48656C6C6F", is_hex=True)
    assert hex_editor.cursor_offset == 0

def test_hex_editor_replace_ascii(hex_editor):
    hex_editor.cursor_offset = 6 # At 'World'
    hex_editor.replace("World", "Kivy", is_hex=False)
    assert b"Kivy" in hex_editor.data
    assert b"World" not in hex_editor.data

def test_hex_editor_replace_hex(hex_editor):
    hex_editor.cursor_offset = 0 # At 'Hello'
    # 'Hello' -> 'Hi!!!' (5 chars)
    # 48 65 6C 6C 6F -> 48 69 21 21 21
    hex_editor.replace("48656C6C6F", "4869212121", is_hex=True)
    assert b"Hi!!!" in hex_editor.data

def test_hex_editor_invalid_codepoint(hex_editor):
    hex_editor.edit_in_hex = False
    hex_editor.cursor_offset = 0
    # Test a multi-byte unicode character
    result = hex_editor._on_key_down(None, None, None, "€", [])
    assert result is False
    assert hex_editor.data[0] == ord('H') # Should not change
