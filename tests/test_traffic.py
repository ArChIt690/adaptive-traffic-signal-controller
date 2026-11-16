import math

import ai.traffic as traffic
from ai.traffic import simulate


def test_deterministic():
    assert simulate(7, 7, 2, 1, seed=4) == simulate(7, 7, 2, 1, seed=4)


def test_different_seeds_differ():
    assert simulate(7, 7, 2, 1, seed=4) != simulate(7, 7, 2, 1, seed=5)


def test_zero_traffic_no_crash():
    r = simulate(9, 9, 0, 0, seconds=30, seed=0)
    assert r.avg_wait >= 0.0 and math.isfinite(r.avg_wait)


def test_no_arrivals_gives_zero_wait(monkeypatch):
    monkeypatch.setattr(traffic, "ARRIVAL_RATE", (0.0, 0.0, 0.0, 0.0))
    r = simulate(9, 9, 0, 0)
    assert r.avg_wait == 0.0 and r.arrived == 0


def test_longer_green_helps_busy_road():
    assert simulate(13, 3, 3, 0, seed=1).avg_wait < simulate(3, 13, 3, 0, seed=1).avg_wait


def test_saturated_finite():
    r = simulate(15, 15, 3, 3, seconds=3600)
    assert math.isfinite(r.avg_wait) and r.served <= r.arrived


def test_arrival_rate_roughly_matches_level():
    r = simulate(9, 9, 3, 0, seconds=20000, seed=2)
    assert abs(r.arrived / 20000 - (traffic.ARRIVAL_RATE[3] + traffic.ARRIVAL_RATE[0])) < 0.02
