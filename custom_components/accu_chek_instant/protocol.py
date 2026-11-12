"""Bluetooth SIG Glucose Measurement and Record Access Control Point."""
from dataclasses import dataclass
from datetime import datetime, timedelta, tzinfo
import struct

MGDL_PER_MMOL = 18.0182
REPORT_ALL = bytes((1, 1))


class MeterError(Exception):
    """The device did not complete a usable glucose transfer."""


class PairingRequired(MeterError):
    """This adapter has not been paired with the meter."""


@dataclass(frozen=True)
class Reading:
    sequence: int
    measured_at: datetime
    mg_dl: float


class GlucoseRecords:
    """Carry the most recently reported time offset within this transfer."""

    def __init__(self, timezone: tzinfo) -> None:
        self.timezone = timezone
        self.offset_minutes = 0

    def decode(self, packet: bytes) -> Reading | None:
        if len(packet) < 10:
            return None
        flags, sequence, year, month, day, hour, minute, second = struct.unpack_from(
            "<BHHBBBBB", packet
        )
        position = 10
        if flags & 1:
            if len(packet) < position + 2:
                return None
            self.offset_minutes = struct.unpack_from("<h", packet, position)[0]
            position += 2
        if not flags & 2 or len(packet) < position + 3:
            return None
        encoded, sample = struct.unpack_from("<HB", packet, position)
        if encoded in (0x07FE, 0x07FF, 0x0800, 0x0801, 0x0802):
            return None
        if (sample & 0x0F) == 10 or (sample >> 4) == 4:  # Control solution
            return None
        if flags & 8:
            if len(packet) < position + 5:
                return None
            status = struct.unpack_from("<H", packet, position + 3)[0]
            if status & 0x0FFE:
                return None
        try:
            local = datetime(year, month, day, hour, minute, second)
            measured_at = (local + timedelta(minutes=self.offset_minutes)).replace(
                tzinfo=self.timezone
            )
        except (ValueError, OverflowError):
            return None
        exponent = encoded >> 12
        if exponent >= 8:
            exponent -= 16
        mantissa = encoded & 0x0FFF
        if mantissa >= 2048:
            mantissa -= 4096
        concentration = mantissa * 10**exponent
        mg_dl = concentration * (1000 * MGDL_PER_MMOL if flags & 4 else 100_000)
        if not 10 <= mg_dl <= 1000:
            return None
        return Reading(sequence, measured_at, round(mg_dl, 3))
