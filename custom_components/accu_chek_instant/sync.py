"""Shared synchronization for Bluetooth discovery and the manual button."""
import asyncio
from datetime import UTC, datetime, timedelta
from hashlib import sha256

from aiohttp import ClientError, ClientTimeout
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.dispatcher import async_dispatcher_send

from . import meter_signal
from .meter import read_latest


async def sync_meter(hass, entry, *, automatic=False):
    runtime = entry.runtime_data
    async with runtime.lock:
        settings = entry.data
        reading = await read_latest(
            hass, settings["address"], settings["pin"], automatic=automatic
        )
        if reading != runtime.reading:
            runtime.reading = reading
            async_dispatcher_send(hass, meter_signal(entry))
        if settings["nightscout_url"] and reading != runtime.last_sent:
            try:
                await _send_reading(hass, reading, settings)
            except UploadConnectionError:
                if not automatic:
                    raise
                await asyncio.sleep(2)
                await _send_reading(hass, reading, settings)
            runtime.last_sent = reading
        return reading


class UploadConnectionError(HomeAssistantError):
    """A Nightscout Lite request can be retried without rereading the meter."""


async def _send_reading(hass, reading, settings):
    measured_at = reading.measured_at.astimezone(UTC)
    if measured_at > datetime.now(UTC) + timedelta(minutes=5):
        raise HomeAssistantError("Nightscout: skontroluj čas na glukomeri, meranie je v budúcnosti")
    timestamp = int(measured_at.timestamp() * 1000)
    identity = f'{settings["address"]}:{reading.sequence}:{timestamp}'
    remote_id = sha256(identity.encode()).hexdigest()[:24]
    payload = {
        "_id": remote_id,
        "identifier": f"accu-chek-{remote_id}",
        "date": timestamp,
        "created_at": measured_at.isoformat(),
        "eventType": "BG Check",
        "type": "fingerstick",
        "glucose": reading.mg_dl,
        "glucoseValueMgDl": reading.mg_dl,
        "glucoseType": "Finger",
        "units": "mg/dl",
        "enteredBy": "Accu-Chek Instant / Home Assistant",
    }
    session = async_get_clientsession(hass)
    try:
        async with session.post(
            f'{settings["nightscout_url"]}/api/v1/treatments',
            json=payload,
            headers={"api-secret": settings["write_secret"]},
            timeout=ClientTimeout(total=10),
            allow_redirects=False,
        ) as response:
            if not 200 <= response.status < 300:
                raise HomeAssistantError(f"Nightscout Lite odmietol zápis (HTTP {response.status})")
    except (ClientError, asyncio.TimeoutError) as err:
        raise UploadConnectionError("Meranie je v HA, zápis do Nightscout Lite zlyhal") from err
