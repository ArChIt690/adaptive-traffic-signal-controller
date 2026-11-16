"""Discrete-time traffic simulator for a two-road junction (1 step = 1 second).

Phase order matches the hardware FSM: NS green -> yellow -> EW green -> yellow.
"""
from dataclasses import dataclass

import numpy as np

from hw.rom import YELLOW

ARRIVAL_RATE = (0.05, 0.15, 0.30, 0.45)  # cars per second for traffic level 0..3
DISCHARGE_PER_S = 1                       # cars that can leave per second of green


@dataclass(frozen=True)
class SimResult:
    avg_wait: float   # seconds a car spends queued, on average
    avg_queue: float  # cars waiting on both roads, averaged over time
    arrived: int
    served: int


def simulate(green_ns: int, green_ew: int, density_ns: int, density_ew: int,
             seconds: int = 1800, seed: int = 0) -> SimResult:
    rng = np.random.default_rng(seed)
    arr_ns = (rng.random(seconds) < ARRIVAL_RATE[density_ns]).tolist()
    arr_ew = (rng.random(seconds) < ARRIVAL_RATE[density_ew]).tolist()

    # which road has green in each second of one cycle (0 = NS, 1 = EW, None = yellow)
    cycle = [0] * green_ns + [None] * YELLOW + [1] * green_ew + [None] * YELLOW
    q_ns = q_ew = served = queue_seconds = 0
    for t in range(seconds):
        q_ns += arr_ns[t]
        q_ew += arr_ew[t]
        g = cycle[t % len(cycle)]
        if g == 0:
            out = min(q_ns, DISCHARGE_PER_S); q_ns -= out; served += out
        elif g == 1:
            out = min(q_ew, DISCHARGE_PER_S); q_ew -= out; served += out
        queue_seconds += q_ns + q_ew
    arrived = int(sum(arr_ns) + sum(arr_ew))
    return SimResult(avg_wait=queue_seconds / arrived if arrived else 0.0,
                     avg_queue=queue_seconds / seconds,
                     arrived=arrived, served=served)
