"""Read the Accu-Chek Instant using a local Home Assistant Bluetooth adapter."""
import asyncio
import logging

from bleak.exc import BleakError
from bleak_retry_connector import BleakClientWithServiceCache, establish_connection
from dbus_fast.errors import DBusError
from homeassistant.components import bluetooth
from homeassistant.util import dt as dt_util

from .pairing import ensure_paired
from .protocol import GlucoseRecords, MeterError, Reading, REPORT_ALL


_LOGGER = logging.getLogger(__name__)


def sig_uuid(number: str) -> str:
    return f"0000{number}-0000-1000-8000-00805f9b34fb"


def local_bluez_path(device) -> str | None:
    details = device.details
    path = details.get("path") if isinstance(details, dict) else None
    return path if isinstance(path, str) and path.startswith("/org/bluez/") else None


async def read_latest(hass, address: str, pin: str, *, automatic=False) -> Reading:
    candidates = bluetooth.async_scanner_devices_by_address(hass, address)
    for candidate in candidates:
        device = candidate.ble_device
        if path := local_bluez_path(device):
            break
    else:
        raise MeterError("Glukomer nie je v dosahu lokálneho Bluetooth adaptéra")

    decoder = GlucoseRecords(dt_util.get_default_time_zone())
    readings = []
    result = asyncio.get_running_loop().create_future()
    receiving_records = False

    def on_measurement(_characteristic, data):
        reading = decoder.decode(data)
        if reading is not None:
            readings.append(reading)

    def on_response(_characteristic, data):
        if len(data) >= 4 and data[:3] == bytes((6, 0, 1)) and not result.done():
            result.set_result(data[3])

    def on_disconnect(client):
        if receiving_records and not client.is_connected and not result.done():
            result.set_result(None)

    try:
        await ensure_paired(path, pin, allow_pair=not automatic)
        async with asyncio.timeout(45 if automatic else 90):
            client = await establish_connection(
                BleakClientWithServiceCache,
                device,
                "Accu-Chek Instant",
                disconnected_callback=on_disconnect,
                max_attempts=2 if automatic else 3,
            )
            receiving_records = True
            try:
                service = client.services.get_service(sig_uuid("1808"))
                measurement = service.get_characteristic(sig_uuid("2a18")) if service else None
                context = service.get_characteristic(sig_uuid("2a34")) if service else None
                racp = service.get_characteristic(sig_uuid("2a52")) if service else None
                if measurement is None or racp is None:
                    raise MeterError("Glukomer neponúka štandardnú službu Glucose")
                if context is not None:
                    await client.start_notify(context, lambda _characteristic, _data: None)
                await client.start_notify(measurement, on_measurement)
                await client.start_notify(racp, on_response)
                await client.write_gatt_char(racp, REPORT_ALL, response=True)
                status = await result
            finally:
                receiving_records = False
                try:
                    async with asyncio.timeout(5):
                        await client.disconnect()
                except (BleakError, DBusError, OSError, TimeoutError) as err:
                    _LOGGER.debug("Odpojenie glukomera zlyhalo: %s", err)
    except (BleakError, DBusError, OSError, TimeoutError) as err:
        detail = str(err) or type(err).__name__
        raise MeterError(f"Bluetooth synchronizácia zlyhala: {detail}") from err

    if status is None:
        raise MeterError("Glukomer sa odpojil pred dokončením prenosu")
    if status == 6 or (status == 1 and not readings):
        raise MeterError("V glukomeri sa nenašlo použiteľné meranie")
    if status != 1:
        raise MeterError(f"Glukomer odmietol čítanie záznamov (RACP {status})")
    return max(readings, key=lambda reading: reading.sequence)
