from __future__ import annotations

import time
from collections import deque
from enum import Enum, auto
from typing import Protocol

from config import LockConfig
from credentials import CredentialStore


class LockHardware(Protocol):
    """Interface mínima usada pelo controlador, facilitando testes sem GPIO."""

    def poll_key(self) -> str | None: ...
    def set_lcd(self, line1: str, line2: str = "") -> None: ...
    def lock(self) -> None: ...
    def unlock(self) -> None: ...
    def buzzer_on(self) -> None: ...
    def buzzer_off(self) -> None: ...
    def read_distance_cm(self, *, force: bool = False) -> float | None: ...
    def door_is_closed(self) -> bool | None: ...


class State(Enum):
    LOCKED = auto()
    UNLOCKED = auto()
    WAITING_CLOSE = auto()
    COOLDOWN = auto()
    ALARM = auto()


class BuzzerPattern:
    """Sequenciador não bloqueante de sinais para buzzer ativo."""

    def __init__(self, hardware: LockHardware) -> None:
        self.hardware = hardware
        self._steps: deque[tuple[bool, float]] = deque()
        self._deadline = 0.0
        self._repeat: list[tuple[bool, float]] | None = None

    def play(self, steps: list[tuple[bool, float]], *, repeat: bool = False) -> None:
        self.stop()
        self._repeat = list(steps) if repeat else None
        self._steps = deque(steps)
        self._advance(time.monotonic())

    def stop(self) -> None:
        self._steps.clear()
        self._repeat = None
        self._deadline = 0.0
        self.hardware.buzzer_off()

    def _advance(self, now: float) -> None:
        if not self._steps and self._repeat:
            self._steps = deque(self._repeat)
        if not self._steps:
            self.hardware.buzzer_off()
            return
        enabled, duration = self._steps.popleft()
        self.hardware.buzzer_on() if enabled else self.hardware.buzzer_off()
        self._deadline = now + duration

    def update(self, now: float) -> None:
        if self._deadline and now >= self._deadline:
            self._advance(now)


class LockController:
    def __init__(
        self,
        config: LockConfig,
        hardware: LockHardware,
        credentials: CredentialStore,
    ) -> None:
        self.cfg = config
        self.hw = hardware
        self.credentials = credentials
        self.buzzer = BuzzerPattern(hardware)

        self.state = State.LOCKED
        self.pin_buffer = ""
        self.failed_attempts = 0
        self.state_deadline = 0.0
        self.message_deadline = 0.0
        self.cooldown_deadline = 0.0
        self._last_closed: bool | None = None
        self._sensor_candidate: bool | None = None
        self._sensor_candidate_since = time.monotonic()
        self._opened_while_locked_since: float | None = None
        self._last_cooldown_second: int | None = None

    def start(self) -> None:
        self.hw.lock()
        self.hw.set_lcd("FECHADURA", "Digite a senha")

    def _set_state(self, new_state: State) -> None:
        self.state = new_state

    def _display_prompt(self) -> None:
        self.hw.set_lcd("FECHADURA", "Senha: " + "*" * len(self.pin_buffer))

    def _show_temporary(self, line1: str, line2: str, duration_s: float) -> None:
        self.hw.set_lcd(line1, line2)
        self.message_deadline = time.monotonic() + duration_s

    def _success(self, now: float) -> None:
        self.failed_attempts = 0
        self.pin_buffer = ""
        self.hw.unlock()
        self.buzzer.play([(True, 0.08), (False, 0.08), (True, 0.08)])
        self.state_deadline = now + self.cfg.unlock_duration_s
        self._set_state(State.UNLOCKED)
        self.hw.set_lcd("ACESSO LIBERADO", "Fechadura aberta")

    def _failure(self, now: float) -> None:
        self.failed_attempts += 1
        self.pin_buffer = ""
        self.buzzer.play([(True, 0.65)])
        if self.failed_attempts >= self.cfg.max_failed_attempts:
            self.cooldown_deadline = now + self.cfg.cooldown_s
            self._last_cooldown_second = None
            self._set_state(State.COOLDOWN)
            self.hw.set_lcd("BLOQUEADO", f"Aguarde {int(self.cfg.cooldown_s)}s")
        else:
            remaining = self.cfg.max_failed_attempts - self.failed_attempts
            self._show_temporary("ACESSO NEGADO", f"Restam {remaining}", 1.5)

    def _submit_pin(self, now: float) -> None:
        if not self.cfg.pin_min_digits <= len(self.pin_buffer) <= self.cfg.pin_max_digits:
            self.pin_buffer = ""
            self.buzzer.play([(True, 0.20)])
            self._show_temporary("SENHA INVALIDA", "Use 4 a 6 dig.", 1.4)
            return
        if self.credentials.verify(self.pin_buffer):
            self._success(now)
        else:
            self._failure(now)

    def _handle_key(self, key: str, now: float) -> None:
        if self.state == State.COOLDOWN:
            self.buzzer.play([(True, 0.05)])
            return

        if key.isdigit():
            if len(self.pin_buffer) < self.cfg.pin_max_digits:
                self.pin_buffer += key
            self._display_prompt()
            return

        if key == "*":
            self.pin_buffer = self.pin_buffer[:-1]
            self._display_prompt()
            return

        if key == "D":
            self.pin_buffer = ""
            self._display_prompt()
            return

        if key == "#":
            self._submit_pin(now)
            return

        if key == "A":
            # Comando de fechamento manual, útil durante os testes.
            self.pin_buffer = ""
            closed = self.hw.door_is_closed()
            if closed:
                self.hw.lock()
                self.buzzer.stop()
                self._set_state(State.LOCKED)
                self.hw.set_lcd("TRANCADA", "Digite a senha")
            else:
                self._show_temporary("PORTA ABERTA", "Nao pode trancar", 1.5)
            return

        if key == "B":
            distance = self.hw.read_distance_cm(force=True)
            text = "Sensor indispon." if distance is None else f"Dist: {distance:5.1f}cm"
            self._show_temporary("STATUS SENSOR", text, 1.5)

    def _update_sensor_state(self, now: float) -> bool | None:
        raw = self.hw.door_is_closed()
        if raw != self._sensor_candidate:
            self._sensor_candidate = raw
            self._sensor_candidate_since = now
            return self._last_closed
        if now - self._sensor_candidate_since >= self.cfg.sensor_stable_time_s:
            if raw != self._last_closed:
                self._last_closed = raw
            return raw
        return self._last_closed

    def _enter_alarm(self) -> None:
        if self.state == State.ALARM:
            return
        self.pin_buffer = ""
        self._set_state(State.ALARM)
        self.hw.set_lcd("ALERTA!", "PORTA FORCADA")
        self.buzzer.play([(True, 0.25), (False, 0.15)], repeat=True)

    def _update_locked(self, now: float, closed: bool | None) -> None:
        if closed is False:
            if self._opened_while_locked_since is None:
                self._opened_while_locked_since = now
            elif now - self._opened_while_locked_since >= self.cfg.forced_open_grace_s:
                self._enter_alarm()
        else:
            self._opened_while_locked_since = None

    def _update_unlocked(self, now: float, closed: bool | None) -> None:
        if now < self.state_deadline:
            return
        if closed is True:
            self.hw.lock()
            self._set_state(State.LOCKED)
            self.hw.set_lcd("TRANCADA", "Digite a senha")
        else:
            self._set_state(State.WAITING_CLOSE)
            self.hw.set_lcd("FECHE A PORTA", "Aguardando...")
            self.buzzer.play([(True, 0.10), (False, 0.90)], repeat=True)

    def _update_waiting_close(self, closed: bool | None) -> None:
        if closed is True:
            self.buzzer.stop()
            self.hw.lock()
            self._set_state(State.LOCKED)
            self.hw.set_lcd("TRANCADA", "Digite a senha")

    def _update_cooldown(self, now: float) -> None:
        remaining = max(0, int(self.cooldown_deadline - now + 0.999))
        if remaining != self._last_cooldown_second:
            self._last_cooldown_second = remaining
            self.hw.set_lcd("BLOQUEADO", f"Aguarde {remaining:2d}s")
        if now >= self.cooldown_deadline:
            self.failed_attempts = 0
            self._set_state(State.LOCKED)
            self.hw.set_lcd("TRANCADA", "Digite a senha")

    def update(self) -> None:
        now = time.monotonic()
        self.buzzer.update(now)

        key = self.hw.poll_key()
        if key is not None:
            self._handle_key(key, now)

        closed = self._update_sensor_state(now)

        # O alarme físico tem prioridade mesmo durante cooldown.
        if self.state in (State.LOCKED, State.COOLDOWN):
            self._update_locked(now, closed)

        if self.state == State.UNLOCKED:
            self._update_unlocked(now, closed)
        elif self.state == State.WAITING_CLOSE:
            self._update_waiting_close(closed)
        elif self.state == State.COOLDOWN:
            self._update_cooldown(now)
        elif self.state == State.ALARM:
            # Senha correta continua podendo reconhecer o alarme e abrir.
            pass

        if self.message_deadline and now >= self.message_deadline:
            self.message_deadline = 0.0
            if self.state == State.LOCKED:
                self._display_prompt()

    def close(self) -> None:
        self.buzzer.stop()
