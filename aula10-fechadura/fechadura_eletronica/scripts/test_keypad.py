#!/usr/bin/env python3
from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from config import LockConfig
from keypad_matrix import MatrixKeypad


def main() -> None:
    cfg = LockConfig.load_or_create("config/lock_config.json")
    keypad = MatrixKeypad(
        cfg.keypad_rows,
        cfg.keypad_cols,
        debounce_ms=cfg.keypad_debounce_ms,
    )
    print("Pressione as teclas do teclado matricial. Ctrl+C encerra.")
    try:
        while True:
            key = keypad.poll()
            if key is not None:
                print(f"Tecla: {key}", flush=True)
            time.sleep(0.01)
    finally:
        keypad.close()


if __name__ == "__main__":
    main()
