"""Home Assistant integration for the Accu-Chek Instant meter."""
from dataclasses import dataclass, field
import asyncio

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .protocol import Reading

DOMAIN = "accu_chek_instant"
PLATFORMS = (Platform.SENSOR, Platform.BUTTON)


@dataclass
class MeterRuntime:
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    reading: Reading | None = None
    last_sent: Reading | None = None


type MeterEntry = ConfigEntry[MeterRuntime]


async def async_setup_entry(hass: HomeAssistant, entry: MeterEntry) -> bool:
    entry.runtime_data = MeterRuntime()
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    from .automatic import register_automatic_sync

    register_automatic_sync(hass, entry)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: MeterEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


def meter_signal(entry: MeterEntry) -> str:
    return f"{DOMAIN}_{entry.entry_id}_reading"
