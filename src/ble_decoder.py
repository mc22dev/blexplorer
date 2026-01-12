import struct
import logging
from typing import Optional, Tuple

from bleak.backends.scanner import AdvertisementData
from beacontools import (
    parse_packet,
    EddystoneUIDFrame,
    EddystoneURLFrame,
    EddystoneTLMFrame,
    IBeaconAdvertisement,
    EstimoteTelemetryFrameA,
    EstimoteTelemetryFrameB
)


def _reconstruct_packet(adv_data: AdvertisementData) -> bytes:
    """
    Tries to reconstruct a raw BLE advertisement packet from bleak's AdvertisementData.
    This is a best-effort reconstruction as bleak does not provide the raw packet.
    """
    packet = bytearray()

    # Add Manufacturer Data (for iBeacon, Estimote, etc.)
    for mfg_id, data in adv_data.manufacturer_data.items():
        payload = mfg_id.to_bytes(2, 'little') + data
        # AD Structure: Length byte, AD Type byte, Payload
        packet += (len(payload) + 1).to_bytes(1, 'little')
        packet += b'\xff'  # AD Type: Manufacturer Specific Data
        packet += payload

    # Add Service Data (for Eddystone)
    for uuid, data in adv_data.service_data.items():
        try:
            # Get the 16-bit part if it's a standard UUID, e.g., "0000feaa-..." -> 0xfeaa
            uuid_short = int(uuid.split('-')[0], 16)
            payload = uuid_short.to_bytes(2, 'little') + data
            # AD Structure: Length byte, AD Type byte, Payload
            packet += (len(payload) + 1).to_bytes(1, 'little')
            packet += b'\x16'  # AD Type: Service Data - 16-bit UUID
            packet += payload
        except (ValueError, IndexError):
            logging.warning(f"Could not parse service UUID for packet reconstruction: {uuid}")
            continue

    return bytes(packet)


def _format_beacon(beacon) -> str:
    """Formats a beacon object from beacontools into a human-readable string."""
    if isinstance(beacon, IBeaconAdvertisement):
        return (f"[iBeacon] UUID: {beacon.uuid}, "
                f"Major: {beacon.major}, Minor: {beacon.minor}, "
                f"TX Power: {beacon.tx_power} dBm")
    elif isinstance(beacon, EddystoneUIDFrame):
        return (f"[Eddystone-UID] Namespace: {beacon.namespace}, "
                f"Instance: {beacon.instance}, "
                f"TX Power: {beacon.tx_power} dBm")
    elif isinstance(beacon, EddystoneURLFrame):
        return f"[Eddystone-URL] URL: {beacon.url}, TX Power: {beacon.tx_power} dBm"
    elif isinstance(beacon, EddystoneTLMFrame):
        # sec_cnt is in 0.1s increments
        uptime_s = beacon.sec_cnt / 10.0 if beacon.sec_cnt is not None else 0.0
        return (f"[Eddystone-TLM] v{beacon.version}, Batt: {beacon.voltage}mV, "
                f"Temp: {beacon.temperature:.2f}°C, ADV Cnt: {beacon.adv_cnt}, "
                f"Uptime: {uptime_s:.1f}s")
    elif isinstance(beacon, (EstimoteTelemetryFrameA, EstimoteTelemetryFrameB)):
        return f"[Estimote] {beacon}"  # The default __str__ is informative enough
    return ""


def _decode_xiaomi_temp_humidity(data: bytes) -> Optional[Tuple[float, float]]:
    """
    Decodes temperature and humidity from Xiaomi Mijia LYWSD03MMC sensor data.
    """
    if len(data) < 4:
        return None
    try:
        temp = int.from_bytes(data[0:2], byteorder='little', signed=True) / 100.0
        humidity = int.from_bytes(data[2:4], byteorder='little', signed=False) / 100.0
        return temp, humidity
    except (IndexError, struct.error):
        return None


def decode_advertisement(adv_data: AdvertisementData) -> str:
    """
    Decodes BLE advertisement data into a human-readable string using custom decoders
    and the beacontools library.
    """
    decoded_output = []

    # --- Custom Decoders ---
    # Xiaomi Temperature/Humidity Sensor
    if "0000fe95-0000-1000-8000-00805f9b34fb" in adv_data.service_data:
        xiaomi_data = adv_data.service_data["0000fe95-0000-1000-8000-00805f9b34fb"]
        result = _decode_xiaomi_temp_humidity(xiaomi_data)
        if result:
            temp, humidity = result
            decoded_output.append(f"[Xiaomi Sensor] Temp: {temp:.2f}°C, Humidity: {humidity:.2f}%")

    # --- BeaconTools Decoder ---
    raw_packet = _reconstruct_packet(adv_data)
    if raw_packet:
        try:
            # Use strict=False to be more lenient with packet structures
            beacons = parse_packet(raw_packet, strict=False)
            if beacons:
                # parse_packet can return a single item or a list
                if not isinstance(beacons, list):
                    beacons = [beacons]

                for beacon in beacons:
                    formatted_beacon = _format_beacon(beacon)
                    if formatted_beacon:
                        decoded_output.append(formatted_beacon)
        except Exception as e:
            # beacontools can raise various exceptions if the packet is malformed or not a beacon.
            logging.debug(f"beacontools could not parse advertisement packet: {e}")

    return "\n".join(decoded_output)
