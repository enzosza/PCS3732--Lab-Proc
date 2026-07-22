#!/usr/bin/env python3
from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from config import LockConfig
from credentials import CredentialStore


def main() -> int:
    parser = argparse.ArgumentParser(description="Altera a senha da fechadura.")
    parser.add_argument("--config", default="config/lock_config.json")
    parser.add_argument("--credentials", default="config/credentials.json")
    args = parser.parse_args()

    cfg = LockConfig.load_or_create(args.config)
    first = getpass.getpass("Nova senha numérica: ")
    second = getpass.getpass("Confirme a nova senha: ")
    if first != second:
        print("As senhas não coincidem.", file=sys.stderr)
        return 1

    store = CredentialStore(args.credentials)
    store.set_pin(
        first,
        min_digits=cfg.pin_min_digits,
        max_digits=cfg.pin_max_digits,
    )
    print(f"Senha atualizada em {args.credentials}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
