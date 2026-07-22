from __future__ import annotations

import logging
import time

from gpiozero import AngularServo, Buzzer, DistanceSensor

from config import LockConfig
from keypad_matrix import MatrixKeypad
from lcd1602_i2c import LCD1602I2C


class FreenoveHardware:
    """Abstração dos componentes usados na fechadura eletrônica."""

    def __init__(self, config: LockConfig) -> None:
        self.config = config
        self.log = logging.getLogger(__name__)

        self.keypad = MatrixKeypad(
            config.keypad_rows,
            config.keypad_cols,
            debounce_ms=config.keypad_debounce_ms,
        )
        self.lcd = LCD1602I2C(
            bus_number=config.lcd_i2c_bus,
            candidate_addresses=config.lcd_addresses,
        )
        self.buzzer = Buzzer(config.active_buzzer_gpio)
        self.servo = AngularServo(
            config.servo_gpio,
            initial_angle=config.servo_locked_angle,
            min_angle=0,
            max_angle=180,
            min_pulse_width=config.servo_min_pulse_ms / 1000.0,
            max_pulse_width=config.servo_max_pulse_ms / 1000.0,
        )
        self.distance_sensor = DistanceSensor(
            echo=config.ultrasonic_echo_gpio,
            trigger=config.ultrasonic_trigger_gpio,
            max_distance=config.sensor_max_distance_m,
            queue_len=5,
            partial=True,
        )
        self._last_distance_cm: float | None = None
        self._last_sensor_sample = 0.0

    def poll_key(self) -> str | None:
        return self.keypad.poll()

    def set_lcd(self, line1: str, line2: str = "") -> None:
        self.lcd.write_lines(line1, line2)

    def lock(self) -> None:
        self.servo.angle = self.config.servo_locked_angle

    def unlock(self) -> None:
        self.servo.angle = self.config.servo_unlocked_angle

    def buzzer_on(self) -> None:
        self.buzzer.on()

    def buzzer_off(self) -> None:
        self.buzzer.off()

    def read_distance_cm(self, *, force: bool = False) -> float | None:
        now = time.monotonic()
        if not force and now - self._last_sensor_sample < self.config.sensor_sample_period_s:
            return self._last_distance_cm
        self._last_sensor_sample = now
        try:
            value = float(self.distance_sensor.distance) * 100.0
            if value <= 0:
                return self._last_distance_cm
            self._last_distance_cm = value
        except Exception as exc:  # falha do sensor não deve derrubar a aplicação
            self.log.warning("Falha ao ler sensor ultrassônico: %s", exc)
        return self._last_distance_cm

    def door_is_closed(self) -> bool | None:
        distance = self.read_distance_cm()
        if distance is None:
            return None
        return distance <= self.config.closed_threshold_cm

    def close(self) -> None:
        errors: list[Exception] = []
        try:
            self.buzzer_off()
        except Exception as exc:
            errors.append(exc)
        for resource in (
            self.keypad,
            self.distance_sensor,
            self.servo,
            self.buzzer,
            self.lcd,
        ):
            try:
                resource.close()
            except Exception as exc:
                errors.append(exc)
        if errors:
            self.log.warning("Erros durante liberação do hardware: %s", errors)
