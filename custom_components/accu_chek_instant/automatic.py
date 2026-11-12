"""Start a bounded synchronization when the local adapter sees the meter."""
import asyncio
from datetime import UTC, datetime, timedelta
import logging
from time import monotonic

from homeassistant.components import bluetooth
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError

from .meter import local_bluez_path
from .protocol import MeterError, PairingRequired
from .sync import sync_meter

_LOGGER = logging.getLogger(__name__)
ADVERTISEMENT_GAP = 5
ATTEMPT_DELAYS = (0.5, 2, 4, 8)


def register_automatic_sync(hass, entry):
    last_advertisement = float("-inf")
    task = None

    async def sync_when_awake(seen_at):
        previous = entry.runtime_data.reading
        for delay in ATTEMPT_DELAYS:
            await asyncio.sleep(delay)
            try:
                reading = await sync_meter(hass, entry, automatic=True)
            except PairingRequired:
                return
            except MeterError as err:
                _LOGGER.debug("Automatické čítanie glukomera: %s", err)
                continue
            except HomeAssistantError as err:
                _LOGGER.warning("Automatická synchronizácia glukomera: %s", err)
                return
            if reading != previous and reading.measured_at >= seen_at - timedelta(seconds=30):
                return

    @callback
    def on_advertisement(info):
        nonlocal last_advertisement, task
        if not info.connectable or not local_bluez_path(info.device):
            return
        now = monotonic()
        gap = now - last_advertisement
        last_advertisement = now
        if gap < ADVERTISEMENT_GAP or (task is not None and not task.done()):
            return
        task = entry.async_create_background_task(
            hass, sync_when_awake(datetime.now(UTC)), "Accu-Chek Instant automatic sync"
        )

    address = entry.data["address"]
    register_advertisement = getattr(bluetooth, "async_register_advertisement_callback", None)
    if register_advertisement is not None:
        entry.async_on_unload(register_advertisement(hass, on_advertisement, address))
        return

    async def watch_advertisement_cache():
        # Older HA versions keep the last packet's timestamp even when their
        # change callbacks suppress identical advertisement payloads.
        last_seen = monotonic()
        while True:
            await asyncio.sleep(1)
            info = bluetooth.async_last_service_info(hass, address, connectable=True)
            if info is not None and info.time > last_seen:
                last_seen = info.time
                on_advertisement(info)

    entry.async_create_background_task(
        hass, watch_advertisement_cache(), "Accu-Chek Instant Bluetooth watch"
    )
