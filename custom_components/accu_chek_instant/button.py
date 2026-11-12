"""Request an immediate meter sync or initial pairing."""
from homeassistant.components.button import ButtonEntity
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo

from . import DOMAIN
from .protocol import MeterError
from .sync import sync_meter


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([SyncButton(entry)])


class SyncButton(ButtonEntity):
    _attr_name = "Načítať meranie"
    _attr_has_entity_name = True
    _attr_icon = "mdi:bluetooth-connect"

    def __init__(self, entry):
        self.entry = entry
        self._attr_unique_id = f"{entry.unique_id}_sync"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id)}, name=entry.title
        )

    async def async_press(self):
        if self.entry.runtime_data.lock.locked():
            raise HomeAssistantError("Synchronizácia glukomera už prebieha")
        try:
            await sync_meter(self.hass, self.entry)
        except MeterError as err:
            raise HomeAssistantError(str(err)) from err
