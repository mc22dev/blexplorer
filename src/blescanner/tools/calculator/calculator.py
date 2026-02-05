from kivy.uix.screenmanager import Screen
from kivy.properties import StringProperty, NumericProperty, BooleanProperty
from simpleeval import SimpleEval
import logging

logger = logging.getLogger(__name__)

class CalculatorScreen(Screen):
    expression = StringProperty("")
    hex_display = StringProperty("0x0")
    dec_display = StringProperty("0")
    bin_display = StringProperty("0b0")

    bit_length = NumericProperty(64)
    is_signed = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.evaluator = SimpleEval()
        self.evaluator.functions = {
            "ROR": self.ror,
            "ROL": self.rol,
        }
        # Add single hex digits as names for convenience
        self.evaluator.names = {
            'A': 10, 'B': 11, 'C': 12, 'D': 13, 'E': 14, 'F': 15,
            'a': 10, 'b': 11, 'c': 12, 'd': 13, 'e': 14, 'f': 15,
        }

    def ror(self, val, count):
        count %= self.bit_length
        mask = (1 << self.bit_length) - 1
        val &= mask
        return ((val >> count) | (val << (self.bit_length - count))) & mask

    def rol(self, val, count):
        count %= self.bit_length
        mask = (1 << self.bit_length) - 1
        val &= mask
        return ((val << count) | (val >> (self.bit_length - count))) & mask

    def on_expression(self, instance, value):
        self.calculate()

    def on_bit_length(self, instance, value):
        self.calculate()

    def on_is_signed(self, instance, value):
        self.calculate()

    def calculate(self):
        if not self.expression:
            self.hex_display = "0x0"
            self.dec_display = "0"
            self.bin_display = "0b0"
            return

        try:
            expr = self.expression
            # Simple evaluation
            result = self.evaluator.eval(expr)

            if isinstance(result, (int, float)):
                self.update_displays(int(result))
        except Exception:
            # Silently fail for incomplete expressions
            pass

    def update_displays(self, value):
        mask = (1 << self.bit_length) - 1

        # Apply mask for unsigned representation
        unsigned_value = value & mask

        # Format hex with proper padding based on bit length
        hex_chars = self.bit_length // 4
        self.hex_display = "0x" + format(unsigned_value, f'0{hex_chars}X')

        # Format bin with proper padding
        self.bin_display = "0b" + format(unsigned_value, f'0{self.bit_length}b')

        if self.is_signed:
            if unsigned_value & (1 << (self.bit_length - 1)):
                signed_value = unsigned_value - (1 << self.bit_length)
            else:
                signed_value = unsigned_value
            self.dec_display = str(signed_value)
        else:
            self.dec_display = str(unsigned_value)

    def add_to_expression(self, text):
        self.expression += text

    def clear_expression(self):
        self.expression = ""

    def backspace(self):
        if self.expression:
            self.expression = self.expression[:-1]

    def set_bit_length(self, length):
        self.bit_length = length

    def toggle_signed(self):
        self.is_signed = not self.is_signed
