#!/usr/bin/env python3
from __future__ import annotations

import sys
import time
from pathlib import Path

from gpiozero import Buzzer

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from config import LockConfig


def pulse(buzzer: Buzzer, seconds: float) -> None:
    buzzer.on()
    time.sleep(seconds)
    buzzer.off()


def main() -> None:
    cfg = LockConfig.load_or_create("config/lock_config.json")
    buzzer = Buzzer(cfg.active_buzzer_gpio)
    try:
        print("Padrão de sucesso: dois bipes curtos")
        pulse(buzzer, 0.08)
        time.sleep(0.08)
        pulse(buzzer, 0.08)
        time.sleep(0.5)
        print("Padrão de erro: um bipe longo")
        pulse(buzzer, 0.65)
    finally:
        buzzer.close()


if __name__ == "__main__":
    main()
