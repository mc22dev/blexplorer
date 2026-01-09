from typing import List, Dict, Any


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
