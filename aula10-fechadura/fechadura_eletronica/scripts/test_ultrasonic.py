#!/usr/bin/env python3
from __future__ import annotations

import sys
import time
from pathlib import Path

from gpiozero import DistanceSensor

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from config import LockConfig


def main() -> None:
    cfg = LockConfig.load_or_create("config/lock_config.json")
    sensor = DistanceSensor(
        echo=cfg.ultrasonic_echo_gpio,
        trigger=cfg.ultrasonic_trigger_gpio,
        max_distance=cfg.sensor_max_distance_m,
        queue_len=5,
        partial=True,
    )
    print("Aproxime e afaste um objeto. Ctrl+C encerra.")
    try:
        while True:
            distance_cm = sensor.distance * 100
            status = "FECHADA" if distance_cm <= cfg.closed_threshold_cm else "ABERTA"
            print(f"Distância: {distance_cm:6.2f} cm | Porta: {status}", flush=True)
            time.sleep(0.25)
    finally:
        sensor.close()


if __name__ == "__main__":
    main()
