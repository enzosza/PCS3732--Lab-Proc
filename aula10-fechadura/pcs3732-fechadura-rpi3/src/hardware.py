import time
from typing import Callable, Optional, Protocol

class HardwareBackend(Protocol):
    def buzzer_on(self) -> None: ...
    def buzzer_off(self) -> None: ...
    def lcd_print(self, text: str, line: int = 1) -> None: ...
    def lcd_clear(self) -> None: ...
    def get_distance_cm(self) -> float: ...
    def scan_keypad(self) -> Optional[str]: ...
    def close(self) -> None: ...

class MockBackend:
    """Backend simulado para testes unitários."""
    def __init__(self):
        self.events = []
        self.closed = False
        self.mock_distance = 100.0
        self.mock_key = None

    def _record(self, name: str, value: any):
        self.events.append((time.monotonic_ns(), name, value))

    def buzzer_on(self):
        self._record("buzzer", "on")

    def buzzer_off(self):
        self._record("buzzer", "off")

    def lcd_print(self, text: str, line: int = 1):
        self._record(f"lcd_line_{line}", text)

    def lcd_clear(self):
        self._record("lcd", "clear")

    def get_distance_cm(self) -> float:
        self._record("sensor", f"read {self.mock_distance}cm")
        return self.mock_distance

    def scan_keypad(self) -> Optional[str]:
        if self.mock_key:
            self._record("keypad", f"pressed {self.mock_key}")
            k = self.mock_key
            self.mock_key = None
            return k
        return None

    def close(self):
        self.closed = True
        self._record("backend", "closed")


class RPiHardwareBackend:
    """Backend real usando bibliotecas padrão do tutorial Freenove (RPi.GPIO e smbus)."""
    def __init__(self):
        try:
            import RPi.GPIO as GPIO
            import smbus
        except ImportError:
            raise RuntimeError("Bibliotecas RPi.GPIO ou smbus não encontradas.")
        
        self.GPIO = GPIO
        self.GPIO.setmode(self.GPIO.BCM)
        self.GPIO.setwarnings(False)

        # Configurações do Buzzer (Ativo) - Exemplo: GPIO 18
        self.buzzer_pin = 18
        self.GPIO.setup(self.buzzer_pin, self.GPIO.OUT)
        self.GPIO.output(self.buzzer_pin, self.GPIO.LOW)

        # Configurações do Sensor Ultrassônico (HC-SR04)
        self.trig_pin = 23
        self.echo_pin = 24
        self.GPIO.setup(self.trig_pin, self.GPIO.OUT)
        self.GPIO.setup(self.echo_pin, self.GPIO.IN)
        self.GPIO.output(self.trig_pin, self.GPIO.LOW)

        # Configurações do Teclado Matricial 4x4
        self.row_pins = [17, 27, 22, 10]
        self.col_pins = [9, 11, 5, 6]
        self.keys = [
            ['1', '2', '3', 'A'],
            ['4', '5', '6', 'B'],
            ['7', '8', '9', 'C'],
            ['*', '0', '#', 'D']
        ]
        for pin in self.row_pins:
            self.GPIO.setup(pin, self.GPIO.OUT)
            self.GPIO.output(pin, self.GPIO.LOW)
        for pin in self.col_pins:
            self.GPIO.setup(pin, self.GPIO.IN, pull_up_down=self.GPIO.PUD_UP)

        # Configurações do LCD I2C
        self.I2C_ADDR = 0x27
        self.bus = smbus.SMBus(1)
        self._lcd_init()

    def _lcd_write_byte(self, bits, mode):
        # mode: 1 for data, 0 for command
        bits_high = mode | (bits & 0xF0) | 0x08
        bits_low = mode | ((bits << 4) & 0xF0) | 0x08
        self.bus.write_byte(self.I2C_ADDR, bits_high)
        self._lcd_toggle_enable(bits_high)
        self.bus.write_byte(self.I2C_ADDR, bits_low)
        self._lcd_toggle_enable(bits_low)

    def _lcd_toggle_enable(self, bits):
        time.sleep(0.0005)
        self.bus.write_byte(self.I2C_ADDR, (bits | 0x04))
        time.sleep(0.0005)
        self.bus.write_byte(self.I2C_ADDR, (bits & ~0x04))
        time.sleep(0.0005)

    def _lcd_init(self):
        self._lcd_write_byte(0x33, 0)
        self._lcd_write_byte(0x32, 0)
        self._lcd_write_byte(0x06, 0)
        self._lcd_write_byte(0x0C, 0)
        self._lcd_write_byte(0x28, 0)
        self.lcd_clear()
        time.sleep(0.005)

    def buzzer_on(self):
        self.GPIO.output(self.buzzer_pin, self.GPIO.HIGH)

    def buzzer_off(self):
        self.GPIO.output(self.buzzer_pin, self.GPIO.LOW)

    def lcd_print(self, text: str, line: int = 1):
        if line == 1:
            self._lcd_write_byte(0x80, 0)
        elif line == 2:
            self._lcd_write_byte(0xC0, 0)
        
        text = text.ljust(16, ' ')
        for char in text:
            self._lcd_write_byte(ord(char), 1)

    def lcd_clear(self):
        self._lcd_write_byte(0x01, 0)
        time.sleep(0.002)

    def get_distance_cm(self) -> float:
        self.GPIO.output(self.trig_pin, self.GPIO.HIGH)
        time.sleep(0.00001)
        self.GPIO.output(self.trig_pin, self.GPIO.LOW)

        t0 = time.time()
        timeout = t0 + 0.05
        while self.GPIO.input(self.echo_pin) == 0:
            if time.time() > timeout:
                return -1.0
            t0 = time.time()
        
        t1 = time.time()
        timeout = t1 + 0.05
        while self.GPIO.input(self.echo_pin) == 1:
            if time.time() > timeout:
                return -1.0
            t1 = time.time()
        
        return ((t1 - t0) * 34000) / 2

    def scan_keypad(self) -> Optional[str]:
        for i, row_pin in enumerate(self.row_pins):
            self.GPIO.output(row_pin, self.GPIO.HIGH)
            for j, col_pin in enumerate(self.col_pins):
                if self.GPIO.input(col_pin) == self.GPIO.HIGH:
                    # Debounce
                    time.sleep(0.02)
                    if self.GPIO.input(col_pin) == self.GPIO.HIGH:
                        # Aguarda soltar
                        while self.GPIO.input(col_pin) == self.GPIO.HIGH:
                            pass
                        self.GPIO.output(row_pin, self.GPIO.LOW)
                        return self.keys[i][j]
            self.GPIO.output(row_pin, self.GPIO.LOW)
        return None

    def close(self):
        self.lcd_clear()
        self.buzzer_off()
        self.GPIO.cleanup()
