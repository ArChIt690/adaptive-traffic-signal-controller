"""The real circuit, run headless in every Logisim found in tools/, must match the Python reference."""
import pytest

from hw.rom import encode_rom, uniform_policy
from hw.traffic_controller import build_test_circuit
from verify.logisim_run import engines, run_logisim
from verify.reference import run_reference

ENGINES = [pytest.param(e, id=e.name) for e in engines()]
pytestmark = [pytest.mark.logisim,
              pytest.mark.skipif(not ENGINES, reason="no Logisim in tools/ (see README)")]

ROM_MIXED = encode_rom({**uniform_policy(5, 3), (3, 1): (9, 7), (0, 2): (2, 15), (2, 2): (15, 15)})


@pytest.mark.parametrize("engine", ENGINES)
@pytest.mark.parametrize("dens", [(0, 0), (3, 1), (0, 2), (2, 2)])
def test_circuit_matches_reference(engine, dens):
    hw = run_logisim(build_test_circuit(ROM_MIXED, *dens, ticks=120, target=engine.target), engine)
    ref = run_reference(ROM_MIXED, dens, 120)
    assert hw == ref


@pytest.mark.parametrize("engine", ENGINES)
def test_lights_one_hot_per_road(engine):
    for r in run_logisim(build_test_circuit(ROM_MIXED, 3, 1, ticks=60, target=engine.target), engine):
        assert sum(r.lights[:3]) == 1 and sum(r.lights[3:]) == 1
