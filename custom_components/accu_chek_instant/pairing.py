"""Pair through the local BlueZ adapter with a scoped D-Bus agent."""
import asyncio

from dbus_fast.aio import MessageBus
from dbus_fast.constants import BusType
from dbus_fast.errors import DBusError
from dbus_fast.service import ServiceInterface, method

from .protocol import PairingRequired

BLUEZ = "org.bluez"
DEVICE = "org.bluez.Device1"
AGENT_PATH = "/org/homeassistant/accu_chek_instant/agent"


class PasskeyAgent(ServiceInterface):
    def __init__(self, path, pin):
        super().__init__("org.bluez.Agent1")
        self.path = path
        self.pin = pin

    def _check(self, device):
        if device != self.path or not self.pin:
            raise DBusError("org.bluez.Error.Rejected", "Pairing PIN unavailable")

    @method()
    def RequestPasskey(self, device: "o") -> "u":
        self._check(device)
        return int(self.pin)

    @method()
    def RequestPinCode(self, device: "o") -> "s":
        self._check(device)
        return self.pin

    @method()
    def Release(self):
        pass

    @method()
    def Cancel(self):
        pass


async def ensure_paired(path: str, pin: str, *, allow_pair: bool) -> None:
    async with asyncio.timeout(45 if allow_pair else 5):
        bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
        try:
            device_xml = await bus.introspect(BLUEZ, path)
            device = bus.get_proxy_object(BLUEZ, path, device_xml)
            props = device.get_interface("org.freedesktop.DBus.Properties")
            values = await props.call_get_all(DEVICE)
            bonded = values.get("Bonded") or values.get("Paired")
            if bonded and bonded.value:
                return
            if not allow_pair:
                raise PairingRequired("Najprv spáruj glukomer tlačidlom Načítať meranie")
            manager_xml = await bus.introspect(BLUEZ, "/org/bluez")
            manager = bus.get_proxy_object(BLUEZ, "/org/bluez", manager_xml)
            agent_manager = manager.get_interface("org.bluez.AgentManager1")
            bus.export(AGENT_PATH, PasskeyAgent(path, pin))
            await agent_manager.call_register_agent(AGENT_PATH, "KeyboardOnly")
            # BlueZ uses the agent registered by the caller of Pair().
            await device.get_interface(DEVICE).call_pair()
        finally:
            # Closing this unique D-Bus connection removes its temporary agent.
            bus.disconnect()
