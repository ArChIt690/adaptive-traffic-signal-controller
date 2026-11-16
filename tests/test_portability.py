"""Guards for opening the circuit in Logisim-evolution as well as 2.7.1."""
import xml.etree.ElementTree as ET

import pytest

from hw.rom import encode_rom, uniform_policy
from hw.traffic_controller import build_demo_circuit, build_test_circuit

ROM = encode_rom(uniform_policy(5, 3))
CLASSIC = {"D Flip-Flop", "Register", "Counter", "ROM"}  # parts whose ports move under evolution's appearance


@pytest.fixture(params=["demo", "test"])
def root(request):
    xml = build_demo_circuit(ROM) if request.param == "demo" else build_test_circuit(ROM, 1, 2, ticks=10)
    return request.param, ET.fromstring(xml)


def test_timer_does_not_use_counter(root):
    # 2.7.1 counts DOWN when load=1 and count=1; evolution loads instead, freezing the FSM.
    # So the timer is a Register + Subtractor + MUX; only the test harness's tick counter
    # (plain count-up, same in both versions) may be a Counter.
    which, root = root
    names = [e.get("name") for e in root.iter("comp")]
    assert "Register" in names and "Subtractor" in names
    assert names.count("Counter") == (0 if which == "demo" else 1)


def test_stateful_parts_use_classic_appearance(root):
    _, root = root
    for e in root.iter("comp"):
        if e.get("name") in CLASSIC:
            a = e.find("a[@name='appearance']")
            assert a is not None and a.get("val") == "classic", e.get("name")
