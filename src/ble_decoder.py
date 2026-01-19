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

def _decode_ibeacon(data: bytes) -> Optional[str]:
    """
    Decodes iBeacon advertisement data.
    """
    if len(data) < 25 or data[0:2] != b'\x02\x15':
        return None

    uuid = data[2:18].hex()
    major = int.from_bytes(data[18:20], 'big')
    minor = int.from_bytes(data[20:22], 'big')
    tx_power = int.from_bytes(data[22:23], 'big', signed=True)

    return f"[iBeacon] UUID: {uuid}, Major: {major}, Minor: {minor}, TX Power: {tx_power} dBm"


def _decode_eddystone_uid(data: bytes) -> Optional[str]:
    """
    Decodes Eddystone-UID frame.
    """
    if len(data) < 18:
        return None

    tx_power = int.from_bytes(data[1:2], 'big', signed=True)
    namespace = data[2:12].hex()
    instance = data[12:18].hex()

    return f"[Eddystone-UID] Namespace: {namespace}, Instance: {instance}, TX Power: {tx_power} dBm"


def _decode_eddystone_url(data: bytes) -> Optional[str]:
    """
    Decodes Eddystone-URL frame.
    """
    if len(data) < 4:
        return None

    tx_power = int.from_bytes(data[1:2], 'big', signed=True)
    url_scheme_prefixes = ["http://www.", "https://www.", "http://", "https://"]
    url_scheme = url_scheme_prefixes[data[2]]

    encoded_url = data[3:]
    decoded_url = ""
    for char_code in encoded_url:
        if 0 < char_code < 14:
            decoded_url += [".com/", ".org/", ".edu/", ".net/", ".info/", ".biz/", ".gov/",
                            ".com", ".org", ".edu", ".net", ".info", ".biz", ".gov"][char_code - 1]
        else:
            decoded_url += chr(char_code)

    return f"[Eddystone-URL] URL: {url_scheme}{decoded_url}, TX Power: {tx_power} dBm"


def _decode_eddystone(data: bytes) -> Optional[str]:
    """
    Decodes Eddystone frames (UID, URL, TLM).
    """
    frame_type = data[0]
    if frame_type == 0x00:
        return _decode_eddystone_uid(data)
    elif frame_type == 0x10:
        return _decode_eddystone_url(data)
    elif frame_type == 0x20:
        return _decode_eddystone_tlm(data)
    return None


def _decode_eddystone_tlm(data: bytes) -> Optional[str]:
    """
    Decodes Eddystone-TLM frame.
    """
    if len(data) < 14:
        return None

    version = data[1]
    voltage = int.from_bytes(data[2:4], 'big')
    temp_fixed = int.from_bytes(data[4:6], 'big', signed=True)
    temp = temp_fixed / 256.0
    adv_count = int.from_bytes(data[6:10], 'big')
    uptime = int.from_bytes(data[10:14], 'big') * 0.1

    return f"[Eddystone-TLM] v{version}, Batt: {voltage}mV, Temp: {temp:.2f}°C, ADV Cnt: {adv_count}, Uptime: {uptime:.1f}s"


def decode_advertisement(adv_data: AdvertisementData) -> str:
    """
    Decodes BLE advertisement data into a human-readable string.
    """
    decoded_output = []

    # Xiaomi Temperature/Humidity Sensor
    if "0000fe95-0000-1000-8000-00805f9b34fb" in adv_data.service_data:
        xiaomi_data = adv_data.service_data["0000fe95-0000-1000-8000-00805f9b34fb"]
        if len(xiaomi_data) >= 4:
            result = _decode_xiaomi_temp_humidity(xiaomi_data)
            if result:
                temp, humidity = result
                decoded_output.append(f"[Xiaomi Sensor] Temp: {temp:.2f}°C, Humidity: {humidity:.2f}%")

    # iBeacon
    if 76 in adv_data.manufacturer_data:
        ibeacon_data = adv_data.manufacturer_data[76]
        result = _decode_ibeacon(ibeacon_data)
        if result:
            decoded_output.append(result)

    # Eddystone
    if "0000feaa-0000-1000-8000-00805f9b34fb" in adv_data.service_data:
        eddystone_data = adv_data.service_data["0000feaa-0000-1000-8000-00805f9b34fb"]
        result = _decode_eddystone(eddystone_data)
        if result:
            decoded_output.append(result)

    return "\n".join(decoded_output)
