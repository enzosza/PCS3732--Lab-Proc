#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
import time

from config import LockConfig
from controller import LockController
from credentials import CredentialStore
from hardware import FreenoveHardware


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fechadura eletrônica para Raspberry Pi 3 + Freenove Projects Board v1.2"
    )
    parser.add_argument("--config", default="config/lock_config.json")
    parser.add_argument("--credentials", default="config/credentials.json")
    parser.add_argument(
        "--initial-pin",
        default="1234",
        help="senha criada somente se o arquivo de credenciais ainda não existir",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    config = LockConfig.load_or_create(args.config)
    credentials = CredentialStore(args.credentials)
    created = credentials.ensure_exists(
        args.initial_pin,
        min_digits=config.pin_min_digits,
        max_digits=config.pin_max_digits,
    )
    if created:
        print(
            "AVISO: credencial inicial de laboratório criada. "
            "Altere-a com scripts/set_password.py."
        )

    hardware: FreenoveHardware | None = None
    controller: LockController | None = None
    try:
        hardware = FreenoveHardware(config)
        controller = LockController(config, hardware, credentials)
        controller.start()
        while True:
            controller.update()
            time.sleep(config.main_loop_period_s)
    except KeyboardInterrupt:
        print("Encerramento solicitado pelo usuário.")
        return 0
    except Exception as exc:
        print(f"Falha fatal na fechadura eletrônica: {exc}", file=sys.stderr)
        return 1
    finally:
        if controller is not None:
            controller.close()
        if hardware is not None:
            hardware.close()


if __name__ == "__main__":
    raise SystemExit(main())
