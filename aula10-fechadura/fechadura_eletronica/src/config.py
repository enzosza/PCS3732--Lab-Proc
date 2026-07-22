from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class LockConfig:
    """Configuração da fechadura para a Freenove Projects Board v1.2.

    Todos os números de GPIO usam numeração BCM, conforme a documentação
    oficial da Freenove.
    """

    # Teclado matricial 4x4 (Freenove, capítulo 21)
    keypad_rows: tuple[int, int, int, int] = (16, 20, 21, 26)
    keypad_cols: tuple[int, int, int, int] = (19, 13, 6, 5)
    keypad_debounce_ms: int = 50

    # Atuador e feedback (Freenove, capítulos 6, 13 e 23)
    servo_gpio: int = 18
    active_buzzer_gpio: int = 12
    ultrasonic_trigger_gpio: int = 14
    ultrasonic_echo_gpio: int = 15

    # LCD1602 com PCF8574 via I2C-1
    lcd_i2c_bus: int = 1
    lcd_addresses: tuple[int, int] = (0x27, 0x3F)

    # Ajustes mecânicos. Evitam usar os fins de curso do servo.
    servo_locked_angle: float = 20.0
    servo_unlocked_angle: float = 100.0
    servo_min_pulse_ms: float = 0.5
    servo_max_pulse_ms: float = 2.5

    # Sensor ultrassônico: distância <= limiar indica porta fechada.
    closed_threshold_cm: float = 12.0
    sensor_max_distance_m: float = 3.0
    sensor_sample_period_s: float = 0.10
    sensor_stable_time_s: float = 0.40
    forced_open_grace_s: float = 0.60

    # Regras da aplicação
    pin_min_digits: int = 4
    pin_max_digits: int = 6
    unlock_duration_s: float = 5.0
    max_failed_attempts: int = 3
    cooldown_s: float = 30.0
    main_loop_period_s: float = 0.01

    @classmethod
    def load_or_create(cls, path: str | Path) -> "LockConfig":
        file_path = Path(path)
        if not file_path.exists():
            file_path.parent.mkdir(parents=True, exist_ok=True)
            cfg = cls()
            cfg.save(file_path)
            return cfg

        with file_path.open("r", encoding="utf-8") as file:
            raw: dict[str, Any] = json.load(file)

        # JSON converte tuplas em listas; o construtor aceita sequências,
        # mas normalizamos para manter o tipo declarado.
        for key in ("keypad_rows", "keypad_cols", "lcd_addresses"):
            if key in raw:
                raw[key] = tuple(raw[key])
        return cls(**raw)

    def save(self, path: str | Path) -> None:
        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with file_path.open("w", encoding="utf-8") as file:
            json.dump(asdict(self), file, indent=2, ensure_ascii=False)
            file.write("\n")
