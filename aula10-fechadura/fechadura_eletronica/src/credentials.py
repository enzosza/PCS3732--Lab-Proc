from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from pathlib import Path


class CredentialStore:
    ALGORITHM = "pbkdf2_sha256"
    DEFAULT_ITERATIONS = 200_000

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    @staticmethod
    def _validate_pin(pin: str, min_digits: int = 4, max_digits: int = 6) -> None:
        if not pin.isdigit() or not min_digits <= len(pin) <= max_digits:
            raise ValueError(f"A senha deve conter de {min_digits} a {max_digits} dígitos.")

    def set_pin(
        self,
        pin: str,
        *,
        min_digits: int = 4,
        max_digits: int = 6,
        iterations: int = DEFAULT_ITERATIONS,
    ) -> None:
        self._validate_pin(pin, min_digits, max_digits)
        salt = os.urandom(16)
        digest = hashlib.pbkdf2_hmac("sha256", pin.encode(), salt, iterations)
        payload = {
            "algorithm": self.ALGORITHM,
            "iterations": iterations,
            "salt_b64": base64.b64encode(salt).decode("ascii"),
            "hash_b64": base64.b64encode(digest).decode("ascii"),
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        with temporary.open("w", encoding="utf-8") as file:
            json.dump(payload, file, indent=2)
            file.write("\n")
        os.chmod(temporary, 0o600)
        temporary.replace(self.path)

    def ensure_exists(
        self,
        default_pin: str = "1234",
        *,
        min_digits: int = 4,
        max_digits: int = 6,
    ) -> bool:
        """Cria credenciais de laboratório se ausentes.

        Retorna ``True`` apenas quando o arquivo foi criado.
        """
        if self.path.exists():
            return False
        self.set_pin(default_pin, min_digits=min_digits, max_digits=max_digits)
        return True

    def verify(self, pin: str) -> bool:
        try:
            with self.path.open("r", encoding="utf-8") as file:
                payload = json.load(file)
            if payload.get("algorithm") != self.ALGORITHM:
                return False
            iterations = int(payload["iterations"])
            salt = base64.b64decode(payload["salt_b64"], validate=True)
            expected = base64.b64decode(payload["hash_b64"], validate=True)
        except (OSError, ValueError, KeyError, json.JSONDecodeError):
            return False

        actual = hashlib.pbkdf2_hmac("sha256", pin.encode(), salt, iterations)
        return hmac.compare_digest(actual, expected)
