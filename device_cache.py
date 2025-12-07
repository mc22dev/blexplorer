import json
import os
from typing import Dict, Any, Optional, List

from bleak.backends.client import BleakClient
from bleak.backends.service import BleakGATTService
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.descriptor import BleakGATTDescriptor

CACHE_DIR = ".device_cache"


def descriptor_to_dict(desc: BleakGATTDescriptor) -> Dict[str, Any]:
    """Serializes a BleakGATTDescriptor to a dictionary."""
    return {
        "uuid": desc.uuid,
        "handle": desc.handle,
    }


def characteristic_to_dict(char: BleakGATTCharacteristic) -> Dict[str, Any]:
    """Serializes a BleakGATTCharacteristic to a dictionary."""
    return {
        "uuid": char.uuid,
        "handle": char.handle,
        "description": char.description,
        "properties": char.properties,
        "descriptors": [descriptor_to_dict(desc) for desc in char.descriptors],
    }


def service_to_dict(service: BleakGATTService) -> Dict[str, Any]:
    """Serializes a BleakGATTService to a dictionary."""
    return {
        "uuid": service.uuid,
        "handle": service.handle,
        "description": service.description,
        "characteristics": [characteristic_to_dict(char) for char in service.characteristics],
    }


class DeviceCache:
    """Handles caching of device attributes."""

    def __init__(self, cache_dir: str = CACHE_DIR):
        """Initializes the DeviceCache."""
        self.cache_dir = cache_dir
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)

    def get_cache_filepath(self, device_address: str) -> str:
        """Gets the cache filepath for a given device address."""
        filename = f"{device_address.replace(':', '_')}.json"
        return os.path.join(self.cache_dir, filename)

    def save_device(self, client: BleakClient) -> None:
        """Saves device attributes from a BleakClient to the cache."""
        if not client.address:
            return
        filepath = self.get_cache_filepath(client.address)
        services_data = [service_to_dict(service) for service in client.services]
        data = {"services": services_data}
        try:
            with open(filepath, "w") as f:
                json.dump(data, f, indent=4)
        except IOError as e:
            print(f"Error saving device cache: {e}")

    def load_device(self, device_address: str) -> Optional[List[Dict[str, Any]]]:
        """Loads device services from the cache."""
        filepath = self.get_cache_filepath(device_address)
        if not os.path.exists(filepath):
            return None

        try:
            with open(filepath, "r") as f:
                data = json.load(f)
                return data.get("services")
        except (IOError, json.JSONDecodeError) as e:
            print(f"Error loading device cache: {e}")
            return None

    def compare_services(self, cached_services: List[Dict[str, Any]], live_services: List[Dict[str, Any]]) -> List[str]:
        """
        Compares cached services with live services and returns a list of differences.
        """
        diffs = []
        cached_services_map = {s['uuid']: s for s in cached_services}
        live_services_map = {s['uuid']: s for s in live_services}

        # Check for added/removed services
        cached_uuids = set(cached_services_map.keys())
        live_uuids = set(live_services_map.keys())

        added_services = live_uuids - cached_uuids
        removed_services = cached_uuids - live_uuids

        for uuid in added_services:
            diffs.append(f"Service added: {uuid}")
        for uuid in removed_services:
            diffs.append(f"Service removed: {uuid}")

        # Check for modified services
        for uuid in cached_uuids.intersection(live_uuids):
            cached_service = cached_services_map[uuid]
            live_service = live_services_map[uuid]

            cached_chars_map = {c['uuid']: c for c in cached_service['characteristics']}
            live_chars_map = {c['uuid']: c for c in live_service['characteristics']}

            cached_char_uuids = set(cached_chars_map.keys())
            live_char_uuids = set(live_chars_map.keys())

            added_chars = live_char_uuids - cached_char_uuids
            removed_chars = cached_char_uuids - live_char_uuids

            for char_uuid in added_chars:
                diffs.append(f"Characteristic added to service {uuid}: {char_uuid}")
            for char_uuid in removed_chars:
                diffs.append(f"Characteristic removed from service {uuid}: {char_uuid}")

        return diffs
