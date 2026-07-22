#!/usr/bin/env python3
from __future__ import annotations

import sys
import time
from pathlib import Path

from gpiozero import AngularServo

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from config import LockConfig


def main() -> None:
    cfg = LockConfig.load_or_create("config/lock_config.json")
    servo = AngularServo(
        cfg.servo_gpio,
        initial_angle=0,
        min_angle=0,
        max_angle=180,
        min_pulse_width=cfg.servo_min_pulse_ms / 1000,
        max_pulse_width=cfg.servo_max_pulse_ms / 1000,
    )
    try:
        for label, angle in (
            ("TRANCADA", cfg.servo_locked_angle),
            ("ABERTA", cfg.servo_unlocked_angle),
            ("TRANCADA", cfg.servo_locked_angle),
        ):
            print(f"Posição {label}: {angle:.1f} graus")
            servo.angle = max(0.0, min(180.0, angle))
            time.sleep(2)
    finally:
        servo.close()


if __name__ == "__main__":
    main()
