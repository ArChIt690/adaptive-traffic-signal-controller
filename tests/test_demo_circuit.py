import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from hw.rom import encode_rom, uniform_policy
from hw.traffic_controller import build_demo_circuit
from verify.logisim_run import engines

ROM = encode_rom(uniform_policy(5, 3))
ENGINES = [pytest.param(e, id=e.name) for e in engines()]


def test_demo_is_an_evolution_file_with_builtin_libs_only():
    root = ET.fromstring(build_demo_circuit(ROM))
    assert root.get("source") == "3.8.0"  # the lab uses Logisim-evolution
    assert all(l.get("desc").startswith("#") for l in root.findall("lib"))
    assert ET.fromstring(build_demo_circuit(ROM, target="2.7.1")).get("source") == "2.7.1"


def test_demo_has_controls_and_lights():
    root = ET.fromstring(build_demo_circuit(ROM))
    labels = {a.get("val") for a in root.iter("a") if a.get("name") == "label"}
    assert {"Traffic_NS", "Traffic_EW"} <= labels
    leds = [e for e in root.iter("comp") if e.get("name") == "LED"]
    assert len(leds) == 6
    colours = sorted(e.find("a[@name='color']").get("val") for e in leds)
    assert colours == sorted(["#ff0000", "#ffcc00", "#00cc00"] * 2)
    assert sum(1 for e in root.iter("comp") if e.get("name") == "Hex Digit Display") >= 1


def test_demo_has_no_halt_pin():
    root = ET.fromstring(build_demo_circuit(ROM))
    labels = {a.get("val") for a in root.iter("a") if a.get("name") == "label"}
    assert "halt" not in labels


@pytest.mark.logisim
@pytest.mark.skipif(not ENGINES, reason="no Logisim in tools/ (see README)")
@pytest.mark.parametrize("engine", ENGINES)
def test_demo_loads_without_error(engine):
    # `-tty stats` loads the file, prints a component census and exits (no endless clock run)
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "demo.circ"
        f.write_text(build_demo_circuit(ROM, target=engine.target), encoding="utf-8")
        p = subprocess.run([*engine.command, str(f), "-tty", "stats"],
                           capture_output=True, text=True, timeout=120)
    assert p.returncode == 0, p.stderr
    assert "Exception" not in p.stderr
    assert "compatibility mode" not in p.stderr  # evolution's warning for 2.7.1-style files
    # evolution logs every dialog it would pop up in the GUI through OptionPane (e.g. a label
    # equal to the part's own name, like "clock" on a Clock, is removed with a message)
    assert "OptionPane" not in p.stderr, p.stderr
    assert re.search(r"\bLED\b", p.stdout) and "ROM" in p.stdout


@pytest.mark.parametrize("which", ["demo", "test"])
def test_every_signal_has_two_ends(which):
    from collections import Counter
    from hw.traffic_controller import build_test_circuit
    xml = build_demo_circuit(ROM) if which == "demo" else build_test_circuit(ROM, 1, 2, ticks=10)
    labels = Counter(e.find("a[@name='label']").get("val")
                     for e in ET.fromstring(xml).iter("comp") if e.get("name") == "Tunnel")
    assert [s for s, n in labels.items() if n < 2] == []
