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
