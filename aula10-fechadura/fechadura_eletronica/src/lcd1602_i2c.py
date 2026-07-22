from __future__ import annotations

import time
from collections.abc import Sequence

try:
    from smbus import SMBus  # pacote python3-smbus do Raspberry Pi OS
except ImportError:  # alternativa útil em ambientes virtuais
    from smbus2 import SMBus  # type: ignore[no-redef]


class LCD1602I2C:
    """Driver LCD1602 + PCF8574 compatível com a ligação da Freenove.

    Mapeamento do expansor usado na documentação:
    P0=RS, P1=RW, P2=EN, P3=backlight e P4..P7=D4..D7.
    """

    LCD_CLEAR = 0x01
    LCD_HOME = 0x02
    LCD_ENTRY_MODE = 0x06
    LCD_DISPLAY_ON = 0x0C
    LCD_FUNCTION_4BIT_2LINE = 0x28
    LCD_SET_DDRAM = 0x80

    RS = 0x01
    RW = 0x02
    ENABLE = 0x04
    BACKLIGHT = 0x08

    def __init__(
        self,
        *,
        bus_number: int = 1,
        candidate_addresses: Sequence[int] = (0x27, 0x3F),
        backlight: bool = True,
    ) -> None:
        self._bus = SMBus(bus_number)
        self._backlight = self.BACKLIGHT if backlight else 0
        self.address = self._detect(candidate_addresses)
        self._last_lines: tuple[str, str] | None = None
        self._initialize()

    def _detect(self, addresses: Sequence[int]) -> int:
        for address in addresses:
            try:
                self._bus.write_byte(address, self._backlight)
                return address
            except OSError:
                continue
        expected = ", ".join(f"0x{address:02X}" for address in addresses)
        self._bus.close()
        raise RuntimeError(
            f"LCD I2C não encontrado. Endereços testados: {expected}."
        )

    def _expander_write(self, value: int) -> None:
        self._bus.write_byte(self.address, value | self._backlight)

    def _pulse_enable(self, value: int) -> None:
        self._expander_write(value | self.ENABLE)
        time.sleep(0.000001)
        self._expander_write(value & ~self.ENABLE)
        time.sleep(0.00005)

    def _write4bits(self, value: int) -> None:
        self._expander_write(value)
        self._pulse_enable(value)

    def _send(self, value: int, *, data: bool = False) -> None:
        mode = self.RS if data else 0
        high = (value & 0xF0) | mode
        low = ((value << 4) & 0xF0) | mode
        self._write4bits(high)
        self._write4bits(low)

    def command(self, value: int) -> None:
        self._send(value, data=False)
        if value in (self.LCD_CLEAR, self.LCD_HOME):
            time.sleep(0.002)

    def write_char(self, char: str) -> None:
        if len(char) != 1:
            raise ValueError("write_char recebe exatamente um caractere.")
        self._send(ord(char), data=True)

    def _initialize(self) -> None:
        time.sleep(0.05)
        # Sequência padrão para entrar em modo de 4 bits.
        for value in (0x30, 0x30, 0x30, 0x20):
            self._write4bits(value)
            time.sleep(0.005)
        self.command(self.LCD_FUNCTION_4BIT_2LINE)
        self.command(self.LCD_DISPLAY_ON)
        self.command(self.LCD_CLEAR)
        self.command(self.LCD_ENTRY_MODE)

    @staticmethod
    def _sanitize(text: str) -> str:
        # O conjunto HD44780 não representa bem acentos em todos os módulos.
        substitutions = str.maketrans(
            "áàâãäéèêëíìîïóòôõöúùûüçÁÀÂÃÄÉÈÊËÍÌÎÏÓÒÔÕÖÚÙÛÜÇ",
            "aaaaaeeeeiiiiooooouuuucAAAAAEEEEIIIIOOOOOUUUUC",
        )
        return text.translate(substitutions).encode("ascii", "replace").decode("ascii")

    def write_line(self, row: int, text: str) -> None:
        if row not in (0, 1):
            raise ValueError("O LCD1602 possui somente as linhas 0 e 1.")
        address = 0x00 if row == 0 else 0x40
        self.command(self.LCD_SET_DDRAM | address)
        content = self._sanitize(text)[:16].ljust(16)
        for char in content:
            self.write_char(char)

    def write_lines(self, line1: str, line2: str = "") -> None:
        normalized = (
            self._sanitize(line1)[:16].ljust(16),
            self._sanitize(line2)[:16].ljust(16),
        )
        if normalized == self._last_lines:
            return
        self.write_line(0, normalized[0])
        self.write_line(1, normalized[1])
        self._last_lines = normalized

    def clear(self) -> None:
        self.command(self.LCD_CLEAR)
        self._last_lines = None

    def close(self) -> None:
        try:
            self.clear()
            self._backlight = 0
            self._expander_write(0)
        finally:
            self._bus.close()
