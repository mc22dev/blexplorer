import struct
from typing import Dict, Optional, Tuple
from bleak.backends.scanner import AdvertisementData

def _decode_xiaomi_temp_humidity(data: bytes) -> Optional[Tuple[float, float]]:
    """
    Decodes temperature and humidity from Xiaomi Mijia LYWSD03MMC sensor data.
    """
    if len(data) < 5:
        return None

    # This is a simplified check. A more robust implementation would parse the full frame.
    # The event type for temp+humidity is often 0x0D.
    # Let's assume the data passed here is just the payload for temp/humidity.
    # Temp: 2 bytes, signed int, little-endian, scaled by 0.01
    # Humidity: 2 bytes, unsigned int, little-endian, scaled by 0.01
    try:
        temp = int.from_bytes(data[0:2], byteorder='little', signed=True) / 100.0
        humidity = int.from_bytes(data[2:4], byteorder='little', signed=False) / 100.0
        return temp, humidity
    except (IndexError, struct.error):
        return None

def decode_advertisement(adv_data: AdvertisementData) -> str:
    """
    Decodes BLE advertisement data into a human-readable string.
    Specifically decodes Xiaomi temperature and humidity sensors.
    """
    decoded_output = []

    # Xiaomi Temperature/Humidity Sensor
    if "0000fe95-0000-1000-8000-00805f9b34fb" in adv_data.service_data:
        xiaomi_data = adv_data.service_data["0000fe95-0000-1000-8000-00805f9b34fb"]

        # A simple check for one common format (LYWSD03MMC with custom firmware)
        # where the service data contains temp and humidity directly.
        # A more robust solution would be needed for all Xiaomi variants.
        if len(xiaomi_data) >= 4:
            result = _decode_xiaomi_temp_humidity(xiaomi_data)
            if result:
                temp, humidity = result
                decoded_output.append(f"  [Xiaomi Sensor] Temperature: {temp:.2f}°C, Humidity: {humidity:.2f}%")

    if not decoded_output:
        return ""

    return "\n".join(decoded_output)
