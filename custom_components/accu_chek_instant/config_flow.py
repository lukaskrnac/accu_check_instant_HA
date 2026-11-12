"""Configure a local Accu-Chek Instant."""
import re
from urllib.parse import urlsplit

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers import selector

from . import DOMAIN

MAC = re.compile(r"(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}")
PASSWORD = selector.TextSelector(
    selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
)


class AccuChekConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        return await self._configure("user", user_input)

    async def async_step_reconfigure(self, user_input=None):
        return await self._configure("reconfigure", user_input)

    async def _configure(self, step, user_input):
        errors = {}
        defaults = self._get_reconfigure_entry().data if step == "reconfigure" else {}
        if user_input is not None:
            address = user_input["address"].strip().upper()
            pin = user_input.get("pin", "").strip()
            url = user_input.get("nightscout_url", "").strip().rstrip("/")
            secret = user_input.get("write_secret", "").strip()
            if not MAC.fullmatch(address):
                errors["address"] = "invalid_mac"
            if pin and not re.fullmatch(r"[0-9]{6}", pin):
                errors["pin"] = "invalid_pin"
            if url:
                try:
                    parsed = urlsplit(url)
                    if (
                        parsed.scheme not in ("http", "https") or not parsed.hostname
                        or parsed.username or parsed.password or parsed.path
                        or parsed.query or parsed.fragment
                        or (parsed.port is not None and not 1 <= parsed.port <= 65535)
                    ):
                        errors["nightscout_url"] = "invalid_url"
                except ValueError:
                    errors["nightscout_url"] = "invalid_url"
            if bool(url) != bool(secret):
                errors["base"] = "incomplete_nightscout"
            if not errors:
                data = {
                    "address": address, "pin": pin,
                    "nightscout_url": url, "write_secret": secret,
                }
                await self.async_set_unique_id(address)
                if step == "reconfigure":
                    self._abort_if_unique_id_mismatch()
                    return self.async_update_reload_and_abort(
                        self._get_reconfigure_entry(), data_updates=data
                    )
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=f"Accu-Chek Instant ({address[-5:]})", data=data)
        return self.async_show_form(
            step_id=step,
            data_schema=vol.Schema({
                vol.Required("address", default=defaults.get("address", "")): str,
                vol.Optional("pin", default=defaults.get("pin", "")): PASSWORD,
                vol.Optional("nightscout_url", default=defaults.get("nightscout_url", "")): str,
                vol.Optional("write_secret", default=defaults.get("write_secret", "")): PASSWORD,
            }),
            errors=errors,
        )
