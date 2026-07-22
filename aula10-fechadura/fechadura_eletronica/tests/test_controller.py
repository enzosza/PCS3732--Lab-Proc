from __future__ import annotations

from collections import deque
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import controller
from config import LockConfig
from controller import LockController, State
from credentials import CredentialStore


class FakeHardware:
    def __init__(self) -> None:
        self.keys: deque[str] = deque()
        self.closed: bool | None = True
        self.distance_cm = 5.0
        self.locked = False
        self.buzzer = False
        self.lcd = ("", "")

    def poll_key(self) -> str | None:
        return self.keys.popleft() if self.keys else None

    def set_lcd(self, line1: str, line2: str = "") -> None:
        self.lcd = (line1, line2)

    def lock(self) -> None:
        self.locked = True

    def unlock(self) -> None:
        self.locked = False

    def buzzer_on(self) -> None:
        self.buzzer = True

    def buzzer_off(self) -> None:
        self.buzzer = False

    def read_distance_cm(self, *, force: bool = False) -> float | None:
        return self.distance_cm

    def door_is_closed(self) -> bool | None:
        return self.closed


class FakeEvents:
    def __init__(self) -> None:
        self.records: list[tuple[str, str, dict[str, object]]] = []

    def write(self, event: str, *, state: str, **details: object) -> None:
        self.records.append((event, state, details))


def build_controller(tmp_path: Path, monkeypatch, **config_overrides):
    now = [100.0]
    monkeypatch.setattr(controller.time, "monotonic", lambda: now[0])
    cfg = LockConfig(**config_overrides)
    credentials = CredentialStore(tmp_path / "credentials.json")
    credentials.set_pin("2580")
    hardware = FakeHardware()
    events = FakeEvents()
    lock = LockController(cfg, hardware, credentials, events)
    lock.start()
    return lock, hardware, events, now


def feed(lock: LockController, hardware: FakeHardware, sequence: str) -> None:
    for key in sequence:
        hardware.keys.append(key)
        lock.update()


def test_correct_pin_unlocks_then_relocks(tmp_path: Path, monkeypatch) -> None:
    lock, hardware, _, now = build_controller(
        tmp_path,
        monkeypatch,
        unlock_duration_s=1.0,
        sensor_stable_time_s=0.0,
    )
    feed(lock, hardware, "2580#")
    assert lock.state is State.UNLOCKED
    assert hardware.locked is False

    now[0] += 1.1
    lock.update()
    assert lock.state is State.LOCKED
    assert hardware.locked is True


def test_three_wrong_passwords_start_cooldown(tmp_path: Path, monkeypatch) -> None:
    lock, hardware, _, _ = build_controller(tmp_path, monkeypatch)
    for _ in range(3):
        feed(lock, hardware, "0000#")
    assert lock.state is State.COOLDOWN
    assert lock.failed_attempts == 3


def test_forced_open_enters_alarm(tmp_path: Path, monkeypatch) -> None:
    lock, hardware, _, now = build_controller(
        tmp_path,
        monkeypatch,
        sensor_stable_time_s=0.0,
        forced_open_grace_s=0.2,
    )
    hardware.closed = False
    lock.update()  # candidata
    now[0] += 0.01
    lock.update()  # estado aberto estabilizado; inicia tolerância
    now[0] += 0.21
    lock.update()
    assert lock.state is State.ALARM
    assert hardware.buzzer is True
