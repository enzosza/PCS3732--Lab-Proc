#!/usr/bin/env python3
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from config import LockConfig
from lcd1602_i2c import LCD1602I2C


def main() -> None:
    cfg = LockConfig.load_or_create("config/lock_config.json")
    lcd = LCD1602I2C(
        bus_number=cfg.lcd_i2c_bus,
        candidate_addresses=cfg.lcd_addresses,
    )
    try:
        lcd.write_lines("FECHADURA", "LCD I2C OK")
        print(f"LCD encontrado no endereço 0x{lcd.address:02X}.")
        time.sleep(5)
    finally:
        lcd.close()


if __name__ == "__main__":
    main()
