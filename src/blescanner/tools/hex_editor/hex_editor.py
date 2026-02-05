import os
import logging
from kivy.app import App
from kivy.uix.screenmanager import Screen
from kivy.properties import ObjectProperty, StringProperty, ListProperty, NumericProperty, BooleanProperty
from kivy.core.window import Window
from kivy.uix.recycleview.views import RecycleDataViewBehavior
from kivy.uix.boxlayout import BoxLayout
from blescanner.models import LogLevel

logger = logging.getLogger(__name__)

class HexEditorRow(RecycleDataViewBehavior, BoxLayout):
    index = NumericProperty(0)
    offset_text = StringProperty("")
    hex_text = StringProperty("")
    ascii_text = StringProperty("")
    selected_byte = NumericProperty(-1) # 0-15
    edit_in_hex = BooleanProperty(True)

    def refresh_view_attrs(self, rv, index, data):
        self.index = index
        return super().refresh_view_attrs(rv, index, data)

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            app = App.get_running_app()
            screen = app.root.ids.screen_manager.get_screen('hex_editor')
            screen.handle_row_touch(self.index, touch.pos, self)
            return True
        return super().on_touch_down(touch)

class HexEditorScreen(Screen):
    data = ObjectProperty(bytearray(), rebind=True)
    filepath = StringProperty("")
    cursor_offset = NumericProperty(0)
    cursor_sub_offset = NumericProperty(0) # 0 or 1 for hex digits
    edit_in_hex = BooleanProperty(True)
    status_text = StringProperty("No file loaded")

    view_data = ListProperty([])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.app = App.get_running_app()

    def on_enter(self, *args):
        Window.bind(on_key_down=self._on_key_down)

    def on_leave(self, *args):
        Window.unbind(on_key_down=self._on_key_down)

    def load_file_dialog(self):
        self.app.ui_manager.show_load_dialog("Open File", self._load_file)

    def _load_file(self, path, selection):
        if not selection:
            self.app.ui_manager.dismiss_popup()
            return
        filepath = os.path.join(path, selection[0])
        try:
            with open(filepath, "rb") as f:
                self.data = bytearray(f.read())
            self.filepath = filepath
            self.cursor_offset = 0
            self.update_view_data()
            self.status_text = f"Loaded {filepath} ({len(self.data)} bytes)"
        except Exception as e:
            self.app.log_with_timestamp(f"Error loading file: {e}", LogLevel.ERROR)
        self.app.ui_manager.dismiss_popup()

    def save_file_dialog(self):
        if not self.data:
            return
        self.app.ui_manager.show_save_dialog("Save File", self._save_file)

    def _save_file(self, path, selection):
        if not selection:
            self.app.ui_manager.dismiss_popup()
            return
        filepath = os.path.join(path, selection[0])
        try:
            with open(filepath, "wb") as f:
                f.write(self.data)
            self.filepath = filepath
            self.status_text = f"Saved to {filepath}"
            self.app.log_with_timestamp(f"File saved: {filepath}", LogLevel.SUCCESS)
        except Exception as e:
            self.app.log_with_timestamp(f"Error saving file: {e}", LogLevel.ERROR)
        self.app.ui_manager.dismiss_popup()

    def update_view_data(self):
        new_view_data = []
        for i in range(0, len(self.data), 16):
            chunk = self.data[i:i+16]
            hex_part = " ".join(f"{b:02X}" for b in chunk)
            ascii_part = "".join(chr(b) if 32 <= b <= 126 else "." for b in chunk)

            # Highlight selected byte if it's in this row
            row_selected_byte = -1
            if i <= self.cursor_offset < i + 16:
                row_selected_byte = self.cursor_offset - i

            new_view_data.append({
                'offset_text': f"{i:08X}",
                'hex_text': hex_part,
                'ascii_text': ascii_part,
                'selected_byte': row_selected_byte,
                'edit_in_hex': self.edit_in_hex
            })
        self.view_data = new_view_data

    def handle_row_touch(self, row_index, pos, row_widget):
        local_pos = row_widget.to_local(*pos)
        local_x = local_pos[0]

        hex_label = row_widget.ids.hex_label
        ascii_label = row_widget.ids.ascii_label

        if hex_label.collide_point(local_x, local_pos[1]):
            # Inside hex label. It has 16*3-1 characters = 47 chars
            char_width = hex_label.width / 48
            byte_index = int((local_x - hex_label.x) / (char_width * 3))
            byte_index = max(0, min(15, byte_index))
            self.edit_in_hex = True
            self.cursor_offset = row_index * 16 + byte_index
            self.cursor_sub_offset = 0
        elif ascii_label.collide_point(local_x, local_pos[1]):
            # Inside ascii label. 16 chars.
            char_width = ascii_label.width / 16
            byte_index = int((local_x - ascii_label.x) / char_width)
            byte_index = max(0, min(15, byte_index))
            self.edit_in_hex = False
            self.cursor_offset = row_index * 16 + byte_index

        if self.cursor_offset >= len(self.data):
            self.cursor_offset = len(self.data) - 1 if self.data else 0

        self.update_view_data()

    def insert_byte(self):
        if self.data is not None:
            self.data.insert(self.cursor_offset, 0)
            self.update_view_data()
            self.status_text = f"Inserted byte at {self.cursor_offset:08X}. Total: {len(self.data)} bytes"

    def delete_byte(self):
        if self.data and self.cursor_offset < len(self.data):
            del self.data[self.cursor_offset]
            if self.cursor_offset >= len(self.data) and self.data:
                self.cursor_offset = len(self.data) - 1
            self.update_view_data()
            self.status_text = f"Deleted byte at {self.cursor_offset:08X}. Total: {len(self.data)} bytes"

    def scroll_to_offset(self, offset):
        if not self.data:
            return
        row_index = offset // 16
        total_rows = (len(self.data) + 15) // 16
        if total_rows > 1:
            self.ids.rv.scroll_y = 1.0 - (row_index / (total_rows - 1))
        else:
            self.ids.rv.scroll_y = 1.0

    def search(self, pattern, is_hex):
        if not pattern:
            return
        try:
            if is_hex:
                search_bytes = bytes.fromhex(pattern.replace(" ", ""))
            else:
                search_bytes = pattern.encode('utf-8')

            idx = self.data.find(search_bytes, self.cursor_offset + 1)
            if idx == -1:
                idx = self.data.find(search_bytes) # Wrap around

            if idx != -1:
                self.cursor_offset = idx
                self.update_view_data()
                self.status_text = f"Found at {idx:08X}"
                self.scroll_to_offset(idx)
            else:
                self.status_text = "Pattern not found"
        except Exception as e:
            self.status_text = f"Search error: {e}"

    def replace(self, search_pattern, replace_pattern, is_hex):
        if not search_pattern:
            return
        try:
            if is_hex:
                s_bytes = bytes.fromhex(search_pattern.replace(" ", ""))
                r_bytes = bytes.fromhex(replace_pattern.replace(" ", ""))
            else:
                s_bytes = search_pattern.encode('utf-8')
                r_bytes = replace_pattern.encode('utf-8')

            idx = self.data.find(s_bytes, self.cursor_offset)
            if idx != -1:
                self.data[idx:idx+len(s_bytes)] = r_bytes
                self.update_view_data()
                self.status_text = f"Replaced at {idx:08X}"
            else:
                self.status_text = "Pattern not found for replacement"
        except Exception as e:
            self.status_text = f"Replace error: {e}"

    def _on_key_down(self, window, key, scancode, codepoint, modifier):
        if not self.manager or self.manager.current != self.name:
            return

        # Don't process keys if any TextInput has focus
        if any(ti.focus for ti in [self.ids.search_input, self.ids.replace_input]):
            return

        if not self.data:
            return

        # Handle numeric keypad and digits/letters for editing
        if self.edit_in_hex:
            if codepoint and codepoint.upper() in "0123456789ABCDEF":
                val = int(codepoint, 16)
                current_byte = self.data[self.cursor_offset]
                if self.cursor_sub_offset == 0:
                    new_byte = (val << 4) | (current_byte & 0x0F)
                    self.data[self.cursor_offset] = new_byte
                    self.cursor_sub_offset = 1
                else:
                    new_byte = (current_byte & 0xF0) | val
                    self.data[self.cursor_offset] = new_byte
                    self.cursor_sub_offset = 0
                    if self.cursor_offset < len(self.data) - 1:
                        self.cursor_offset += 1
                self.update_view_data()
                return True
        else:
            if codepoint:
                val = ord(codepoint)
                if val > 255:
                    return False
                self.data[self.cursor_offset] = val
                if self.cursor_offset < len(self.data) - 1:
                    self.cursor_offset += 1
                self.update_view_data()
                return True

        # Navigation
        if key == 273: # Up
            self.cursor_offset = max(0, self.cursor_offset - 16)
            self.update_view_data()
            self.scroll_to_offset(self.cursor_offset)
            return True
        elif key == 274: # Down
            self.cursor_offset = min(len(self.data) - 1, self.cursor_offset + 16)
            self.update_view_data()
            self.scroll_to_offset(self.cursor_offset)
            return True
        elif key == 275: # Right
            self.cursor_offset = min(len(self.data) - 1, self.cursor_offset + 1)
            self.cursor_sub_offset = 0
            self.update_view_data()
            self.scroll_to_offset(self.cursor_offset)
            return True
        elif key == 276: # Left
            self.cursor_offset = max(0, self.cursor_offset - 1)
            self.cursor_sub_offset = 0
            self.update_view_data()
            self.scroll_to_offset(self.cursor_offset)
            return True

        return False
