"""Cycle-accurate Python model of the Logisim traffic controller.

This is the hardware specification the circuit is checked against, tick by tick.
"""
from dataclasses import dataclass
from typing import Callable

from hw.rom import YELLOW

NS_GREEN, NS_YELLOW, EW_GREEN, EW_YELLOW = range(4)


@dataclass(frozen=True)
class Row:
    tick: int
    state: int
    timer: int
    lights: tuple[int, int, int, int, int, int]  # NS_R, NS_Y, NS_G, EW_R, EW_Y, EW_G


def lights(state: int) -> tuple[int, int, int, int, int, int]:
    return (int(state >= 2), int(state == 1), int(state == 0),
            int(state <= 1), int(state == 3), int(state == 2))


def run_reference(rom: list[int],
                  densities: tuple[int, int] | Callable[[int], tuple[int, int]],
                  ticks: int) -> list[Row]:
    dens = densities if callable(densities) else (lambda _t: densities)
    state, timer = NS_GREEN, 0
    rows = [Row(0, state, timer, lights(state))]
    for t in range(ticks):
        if timer <= 1:  # done
            d_ns, d_ew = dens(t)
            byte = rom[(d_ns << 2) | d_ew]
            g_ns, g_ew = byte >> 4, byte & 0xF
            s1, s0 = state >> 1, state & 1
            timer = (g_ns if s1 else g_ew) if s0 else YELLOW
            state = (state + 1) % 4
        else:
            timer -= 1
        rows.append(Row(t + 1, state, timer, lights(state)))
    return rows
