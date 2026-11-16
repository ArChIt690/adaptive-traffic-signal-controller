import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from hw.circ import Circuit, project_xml

JAR = Path(__file__).resolve().parents[1] / "tools" / "logisim-generic-2.7.1.jar"
needs_jar = pytest.mark.skipif(not JAR.exists(), reason="Logisim jar not in tools/")


def run_raw_table(xml: str) -> list[list[str]]:
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "t.circ"
        f.write_text(xml, encoding="utf-8")
        out = subprocess.run(["java", "-jar", str(JAR), str(f), "-tty", "table"],
                             capture_output=True, text=True, timeout=60)
    return [line.split("\t") for line in out.stdout.splitlines() if line.strip()]


def test_project_header_and_libs():
    root = ET.fromstring(project_xml([Circuit("main", target="2.7.1")]))
    assert root.get("source") == "2.7.1"
    assert {l.get("desc") for l in root.findall("lib")} <= {
        "#Wiring", "#Gates", "#Plexers", "#Arithmetic", "#Memory", "#I/O", "#Base"}
    assert root.find("main").get("name") == "main"


def test_connect_places_tunnel_on_port():
    c = Circuit()
    g = c.add("AND Gate", (200, 200), {"inputs": "2", "size": "50"})
    c.connect(g, "out", "x", 1)
    c.connect(g, "in1", "y", 1)
    tunnels = {e.find("a[@name='label']").get("val"): e.get("loc")
               for e in ET.fromstring(c.to_xml()).iter("comp") if e.get("name") == "Tunnel"}
    assert tunnels == {"x": "(200,200)", "y": "(150,220)"}
    assert g.port("in1") == (150, 220)


def test_port_offsets_from_notes():
    c = Circuit()
    assert c.add("D Flip-Flop", (500, 500)).port("D") == (460, 520)
    assert c.add("Counter", (700, 500), {"width": "4"}).port("load") == (670, 490)
    assert c.add("Splitter", (900, 500), {"fanout": "4", "incoming": "4"}).port("end3") == (920, 490)
    with pytest.raises(KeyError):
        c.add("NOT Gate", (1100, 500)).port("in5")


def test_overlap_rejected():
    c = Circuit()
    c.add("NOT Gate", (100, 100))
    with pytest.raises(ValueError):
        c.add("NOT Gate", (110, 100))


def test_rom_contents_written_as_element_text():
    c = Circuit()
    c.add("ROM", (300, 300), {"addrWidth": "4", "dataWidth": "8", "contents": "addr/data: 4 8\n10 21\n"})
    a = next(e for e in ET.fromstring(c.to_xml()).iter("a") if e.get("name") == "contents")
    assert a.get("val") is None and a.text == "addr/data: 4 8\n10 21\n"


@needs_jar
def test_counter_circuit_runs_headless():
    c = Circuit(target="2.7.1")
    clk = c.add("Clock", (100, 100))
    c.connect(clk, "out", "clk", 1)
    ctr = c.add("Counter", (300, 100), {"width": "4", "max": "0x5"})
    c.connect(ctr, "clk", "clk", 1)
    c.connect(ctr, "out", "q", 4)
    c.connect(ctr, "carry", "done", 1)
    c.connect(c.add("Pin", (500, 100), {"output": "true", "width": "4", "facing": "west", "label": "q"}), "port", "q", 4)
    c.connect(c.add("Pin", (500, 200), {"output": "true", "facing": "west", "label": "halt"}), "port", "done", 1)
    rows = run_raw_table(project_xml([c]))
    assert [int(r[0].replace(" ", ""), 2) for r in rows] == [0, 1, 2, 3, 4, 5]


def test_evolution_files_have_an_evolution_header():
    # a "2.7.1" header makes evolution show an "Old file format -- compatibility mode" warning
    root = ET.fromstring(project_xml([Circuit("main", target="evolution")]))
    assert root.get("source") == "3.8.0"


def test_default_target_is_evolution():
    assert Circuit().target == "evolution"


def test_unknown_target_rejected():
    with pytest.raises(ValueError):
        Circuit(target="3.0")


ROM_ATTRS = {"addrWidth": "4", "dataWidth": "8"}


def test_rom_ports_depend_on_target():
    # 2.7.1 anchors the ROM at its data output; evolution at its top-left corner
    # (tools/PortDump.java vs tools/PortDumpEvo.java)
    old = Circuit(target="2.7.1").add("ROM", (500, 500), ROM_ATTRS)
    assert (old.port("addr"), old.port("data")) == ((360, 500), (500, 500))
    evo = Circuit(target="evolution").add("ROM", (500, 500), ROM_ATTRS)
    assert (evo.port("addr"), evo.port("data")) == ((500, 510), (740, 560))
    assert (evo.side("addr"), evo.side("data")) == ("W", "E")


def test_place_puts_the_named_port_on_the_point():
    for target in ("2.7.1", "evolution"):
        rom = Circuit(target=target).place("ROM", "data", (440, 860), ROM_ATTRS)
        assert rom.port("data") == (440, 860)
    assert Circuit(target="evolution").place("ROM", "data", (440, 860), ROM_ATTRS).loc == (200, 800)


def test_project_rejects_mixed_targets():
    with pytest.raises(ValueError):
        project_xml([Circuit("a", target="2.7.1"), Circuit("b", target="evolution")])
