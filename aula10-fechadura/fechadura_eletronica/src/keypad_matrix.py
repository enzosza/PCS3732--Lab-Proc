from __future__ import annotations

import time
from collections.abc import Sequence

from gpiozero import DigitalInputDevice, DigitalOutputDevice


DEFAULT_KEYMAP: tuple[tuple[str, ...], ...] = (
    ("1", "2", "3", "A"),
    ("4", "5", "6", "B"),
    ("7", "8", "9", "C"),
    ("*", "0", "#", "D"),
)


class MatrixKeypad:
    """Leitor não bloqueante de teclado 4x4.

    A varredura segue o princípio descrito pela Freenove: uma coluna é levada
    a nível baixo por vez e as linhas, mantidas com pull-up, são lidas.
    O método ``poll`` gera somente um evento por pressionamento.
    """

    def __init__(
        self,
        row_pins: Sequence[int],
        col_pins: Sequence[int],
        *,
        keymap: Sequence[Sequence[str]] = DEFAULT_KEYMAP,
        debounce_ms: int = 50,
        settle_time_s: float = 0.0003,
    ) -> None:
        if len(row_pins) != 4 or len(col_pins) != 4:
            raise ValueError("O teclado deve possuir quatro linhas e quatro colunas.")
        if len(keymap) != 4 or any(len(row) != 4 for row in keymap):
            raise ValueError("O mapa do teclado deve ser 4x4.")

        self._keymap = tuple(tuple(row) for row in keymap)
        self._debounce_s = debounce_ms / 1000.0
        self._settle_time_s = settle_time_s

        # Linhas: entradas com pull-up. Colunas: saídas normalmente em HIGH.
        self._rows = [DigitalInputDevice(pin, pull_up=True) for pin in row_pins]
        self._cols = [DigitalOutputDevice(pin, initial_value=True) for pin in col_pins]

        self._candidate: str | None = None
        self._candidate_since = time.monotonic()
        self._reported: str | None = None

    def _scan_raw(self) -> str | None:
        pressed: str | None = None
        for col_index, column in enumerate(self._cols):
            column.off()  # LOW apenas na coluna sob teste
            time.sleep(self._settle_time_s)
            try:
                for row_index, row in enumerate(self._rows):
                    # Assim como no exemplo da aula 8, usamos ``value``
                    # diretamente. Com pull_up=True, o gpiozero considera o
                    # nível LOW como ativo: value vale 1 quando a tecla fecha
                    # o circuito entre a linha e a coluna em LOW.
                    if row.value:
                        pressed = self._keymap[row_index][col_index]
                        break
            finally:
                column.on()
            if pressed is not None:
                break
        return pressed

    def poll(self) -> str | None:
        """Retorna uma nova tecla estável ou ``None``.

        Enquanto a tecla permanecer pressionada, nenhum novo evento é gerado.
        É necessário liberar a tecla antes de um novo evento da mesma tecla.
        """

        now = time.monotonic()
        raw = self._scan_raw()

        if raw != self._candidate:
            self._candidate = raw
            self._candidate_since = now
            return None

        if now - self._candidate_since < self._debounce_s:
            return None

        if raw is None:
            self._reported = None
            return None

        if raw == self._reported:
            return None

        self._reported = raw
        return raw

    def close(self) -> None:
        for column in self._cols:
            column.on()
            column.close()
        for row in self._rows:
            row.close()
