#!/usr/bin/env python3
from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

from config import LockConfig
from controller import LockController
from credentials import CredentialStore
from event_log import EventLog
from hardware import FreenoveHardware


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fechadura eletrônica para Raspberry Pi 3 + Freenove Projects Board v1.2"
    )
    parser.add_argument("--config", default="config/lock_config.json")
    parser.add_argument("--credentials", default="config/credentials.json")
    parser.add_argument("--log", default="logs/electronic_lock.log")
    parser.add_argument("--events", default="logs/events.jsonl")
    parser.add_argument(
        "--initial-pin",
        default="1234",
        help="senha criada somente se o arquivo de credenciais ainda não existir",
    )
    return parser


def configure_logging(path: str) -> None:
    log_path = Path(path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def main() -> int:
    args = build_parser().parse_args()
    configure_logging(args.log)
    log = logging.getLogger("electronic_lock")

    config = LockConfig.load_or_create(args.config)
    credentials = CredentialStore(args.credentials)
    created = credentials.ensure_exists(
        args.initial_pin,
        min_digits=config.pin_min_digits,
        max_digits=config.pin_max_digits,
    )
    if created:
        log.warning(
            "Credencial inicial de laboratório criada. Altere-a com scripts/set_password.py."
        )

    hardware: FreenoveHardware | None = None
    controller: LockController | None = None
    try:
        hardware = FreenoveHardware(config)
        events = EventLog(args.events)
        controller = LockController(config, hardware, credentials, events)
        controller.start()
        while True:
            controller.update()
            time.sleep(config.main_loop_period_s)
    except KeyboardInterrupt:
        log.info("Encerramento solicitado pelo usuário.")
        return 0
    except Exception:
        log.exception("Falha fatal na fechadura eletrônica.")
        return 1
    finally:
        if controller is not None:
            controller.close()
        if hardware is not None:
            hardware.close()


if __name__ == "__main__":
    raise SystemExit(main())
