import statistics
import time
from typing import List, Dict, Any, Optional
from enum import Enum
from bleak.backends.scanner import AdvertisementData


class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    SUCCESS = "SUCCESS"


class CachedDescriptor:
    """A class to represent a cached BLE descriptor."""
    def __init__(self, data: Dict[str, Any]):
        self.uuid: str = data['uuid']
        self.handle: int = data['handle']


class CachedCharacteristic:
    """A class to represent a cached BLE characteristic."""
    def __init__(self, data: Dict[str, Any], service_uuid: str):
        self.uuid: str = data['uuid']
        self.handle: int = data['handle']
        self.description: str = data.get('description', '')
        self.properties: List[str] = data['properties']
        self.service_uuid: str = service_uuid
        self.descriptors: List[CachedDescriptor] = [
            CachedDescriptor(desc_data) for desc_data in data['descriptors']
        ]


class CachedService:
    """A class to represent a cached BLE service."""
    def __init__(self, data: Dict[str, Any]):
        self.uuid: str = data['uuid']
        self.handle: int = data['handle']
        self.description: str = data.get('description', '')
        self.characteristics: List[CachedCharacteristic] = [
            CachedCharacteristic(char_data, self.uuid) for char_data in data['characteristics']
        ]


class DeviceScanStats:
    """A class to hold and calculate statistics for a scanned device."""
    def __init__(self):
        self.rssi_values: List[int] = []
        self.timestamps: List[float] = []
        self.adv_data: Optional[AdvertisementData] = None

        self.min_rssi: int = 0
        self.max_rssi: int = 0
        self.avg_rssi: float = 0.0
        self.avg_period: float = 0.0

    def update(self, adv_data: AdvertisementData):
        """Updates the statistics with new advertisement data."""
        self.adv_data = adv_data
        self.rssi_values.append(adv_data.rssi)
        self.timestamps.append(time.monotonic())

        if len(self.rssi_values) >= 1:
            self.min_rssi = min(self.rssi_values)
            self.max_rssi = max(self.rssi_values)
            self.avg_rssi = statistics.mean(self.rssi_values)

        if len(self.rssi_values) >= 2:
            time_diffs = [self.timestamps[i] - self.timestamps[i-1] for i in range(1, len(self.timestamps))]
            if time_diffs:
                self.avg_period = statistics.mean(time_diffs) * 1000  # in ms
