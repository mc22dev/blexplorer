import pytest
from blescanner.models import DeviceScanStats
from bleak.backends.scanner import AdvertisementData

def test_device_scan_stats_initialization():
    stats = DeviceScanStats()
    assert stats.rssi_values == []
    assert stats.timestamps == []
    assert stats.adv_data is None
    assert stats.min_rssi == 0
    assert stats.max_rssi == 0
    assert stats.avg_rssi == 0.0
    assert stats.avg_period == 0.0

def create_adv_data(rssi):
    return AdvertisementData(
        local_name='Test Device',
        manufacturer_data={},
        service_data={},
        service_uuids=[],
        rssi=rssi,
        tx_power=0,
        platform_data=()
    )

def test_device_scan_stats_single_update():
    stats = DeviceScanStats()
    adv1 = create_adv_data(-50)
    stats.update(adv1)

    assert stats.rssi_values == [-50]
    assert len(stats.timestamps) == 1
    assert stats.min_rssi == -50
    assert stats.max_rssi == -50
    assert stats.avg_rssi == -50.0

def test_device_scan_stats_multiple_updates():
    stats = DeviceScanStats()
    adv1 = create_adv_data(-50)
    adv2 = create_adv_data(-60)
    adv3 = create_adv_data(-55)

    stats.update(adv1)
    stats.update(adv2)
    stats.update(adv3)

    assert stats.rssi_values == [-50, -60, -55]
    assert len(stats.timestamps) == 3
    assert stats.min_rssi == -60
    assert stats.max_rssi == -50
    assert stats.avg_rssi == -55.0

def test_device_scan_stats_period_calculation():
    stats = DeviceScanStats()
    adv1 = create_adv_data(-50)
    stats.update(adv1)
    # Simulate a 100ms delay
    stats.timestamps[-1] -= 0.1
    adv2 = create_adv_data(-60)
    stats.update(adv2)

    assert len(stats.timestamps) == 2
    assert stats.avg_period > 0
