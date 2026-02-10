import pytest
from blescanner.tools.calculator.calculator import CalculatorScreen

def test_calculator_basic_arithmetic():
    calc = CalculatorScreen()
    calc.expression = "1 + 1"
    calc.calculate()
    assert calc.dec_display == "2"

def test_calculator_hex_input():
    calc = CalculatorScreen()
    calc.expression = "0x10 + 0x05"
    calc.calculate()
    assert calc.dec_display == "21"
    assert "15" in calc.hex_display.upper()

def test_calculator_bitwise_ops():
    calc = CalculatorScreen()
    calc.expression = "0x0F & 0x03"
    calc.calculate()
    assert calc.dec_display == "3"

    calc.expression = "1 << 4"
    calc.calculate()
    assert calc.dec_display == "16"

def test_calculator_bit_length():
    calc = CalculatorScreen()
    calc.bit_length = 8
    calc.expression = "255 + 1"
    calc.calculate()
    assert calc.dec_display == "0"  # Overflow

    calc.bit_length = 16
    calc.expression = "255 + 1"
    calc.calculate()
    assert calc.dec_display == "256"

def test_calculator_signed_mode():
    calc = CalculatorScreen()
    calc.bit_length = 8
    calc.is_signed = True
    calc.expression = "0xFF"
    calc.calculate()
    assert calc.dec_display == "-1"

    calc.is_signed = False
    calc.calculate()
    assert calc.dec_display == "255"

def test_calculator_ror_rol():
    calc = CalculatorScreen()
    calc.bit_length = 8
    calc.expression = "ROR(1, 1)"
    calc.calculate()
    assert calc.dec_display == "128" # 0x80

    calc.expression = "ROL(128, 1)"
    calc.calculate()
    assert calc.dec_display == "1"

def test_calculator_hex_names():
    calc = CalculatorScreen()
    calc.expression = "A + B"
    calc.calculate()
    assert calc.dec_display == "21"

def test_calculator_keyboard_input():
    calc = CalculatorScreen()
    # Mock manager to bypass focus check if needed, but we check self.name
    calc.name = 'calculator'
    class MockManager:
        current = 'calculator'
    calc.manager = MockManager()

    # Simulate typing '1'
    calc._on_key_down(None, 49, None, '1', [])
    assert calc.expression == '1'

    # Simulate typing '+'
    calc._on_key_down(None, 43, None, '+', [])
    assert calc.expression == '1+'

    # Simulate typing 'A'
    calc._on_key_down(None, 97, None, 'a', [])
    assert calc.expression == '1+A'

    # Simulate Backspace
    calc._on_key_down(None, 8, None, None, [])
    assert calc.expression == '1+'

    # Simulate Clear (Escape)
    calc._on_key_down(None, 27, None, None, [])
    assert calc.expression == ''

    # Test 0x prefix typing
    calc._on_key_down(None, 48, None, '0', [])
    calc._on_key_down(None, 120, None, 'x', [])
    assert calc.expression == '0x'

def test_calculator_numpad_input():
    calc = CalculatorScreen()
    calc.name = 'calculator'
    class MockManager:
        current = 'calculator'
    calc.manager = MockManager()

    # Numpad 5
    calc._on_key_down(None, 261, None, None, [])
    assert calc.expression == '5'

    # Numpad +
    calc._on_key_down(None, 270, None, None, [])
    assert calc.expression == '5+'

    # Numpad 3
    calc._on_key_down(None, 259, None, None, [])
    assert calc.expression == '5+3'

    # Final check
    calc.calculate()
    assert calc.dec_display == "8"

def test_calculator_bitwise_not():
    calc = CalculatorScreen()
    calc.bit_length = 8
    calc.expression = "~0"
    calc.calculate()
    # ~0 in 8-bit is 0xFF which is 255 unsigned
    assert calc.dec_display == "255"
