"""Expose the latest meter reading and its original timestamp."""
from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from . import DOMAIN, meter_signal
from .protocol import MGDL_PER_MMOL


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([GlucoseSensor(entry)])


class GlucoseSensor(SensorEntity):
    _attr_name = "Glykémia"
    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.BLOOD_GLUCOSE_CONCENTRATION
    _attr_native_unit_of_measurement = "mmol/L"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 1

    def __init__(self, entry):
        self.entry = entry
        self._attr_unique_id = f"{entry.unique_id}_glucose"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.unique_id)},
            name=entry.title,
            manufacturer="Roche",
            model="Accu-Chek Instant",
        )

    async def async_added_to_hass(self):
        self.async_on_remove(
            async_dispatcher_connect(self.hass, meter_signal(self.entry), self.async_write_ha_state)
        )

    @property
    def native_value(self):
        reading = self.entry.runtime_data.reading
        return None if reading is None else round(reading.mg_dl / MGDL_PER_MMOL, 3)

    @property
    def extra_state_attributes(self):
        reading = self.entry.runtime_data.reading
        if reading is None:
            return {}
        return {
            "measured_at": reading.measured_at.isoformat(),
            "sequence": reading.sequence,
            "glucose_mg_dl": reading.mg_dl,
        }
