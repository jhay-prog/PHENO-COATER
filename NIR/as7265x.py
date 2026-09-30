from dataclasses import dataclass
import re
from typing import Optional


WAVELENGTHS = (410, 435, 460, 485, 510, 535, 560, 585, 610, 645, 680, 705, 730, 760, 810, 860, 900, 940)
_CHANNELS = ("A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "R", "S", "T", "U", "V", "W")


@dataclass(frozen=True)
class NIRReading:
    wavelength_nm: int
    value: Optional[float]
    status: str = "NO DATA"


class AS7265XReader:
    """Parser and optional serial reader for the Arduino AS7265X output."""

    def __init__(self, serial_connection=None):
        self.serial_connection = serial_connection

    def read_line(self) -> Optional[str]:
        if self.serial_connection is None:
            return None
        raw_line = self.serial_connection.readline()
        if isinstance(raw_line, bytes):
            return raw_line.decode("utf-8", errors="replace").strip()
        return str(raw_line).strip() or None

    @staticmethod
    def parse_line(line: str) -> list[NIRReading]:
        readings = []
        values = {channel: None for channel in _CHANNELS}
        for match in re.finditer(r"(\d+)nm:\s*([-+]?\d*\.?\d+)", line):
            wavelength = int(match.group(1))
            value = float(match.group(2))
            if wavelength in WAVELENGTHS:
                values[_CHANNELS[WAVELENGTHS.index(wavelength)]] = value

        for wavelength, channel in zip(WAVELENGTHS, _CHANNELS):
            value = values[channel]
            readings.append(NIRReading(wavelength, value, "OK" if value is not None else "NO DATA"))
        return readings

    def read_measurement(self) -> list[NIRReading]:
        line = self.read_line()
        return self.parse_line(line) if line else [NIRReading(wavelength, None) for wavelength in WAVELENGTHS]

    @staticmethod
    def demo_measurement() -> list[NIRReading]:
        values = (0.61, 0.63, 0.66, 0.69, 0.72, 0.75, 0.78, 0.74, 0.71, 0.76, 0.81, 0.79, 0.74, 0.68, 0.73, 0.77, 0.71, 0.66)
        return [NIRReading(wavelength, value, "DEMO") for wavelength, value in zip(WAVELENGTHS, values)]
