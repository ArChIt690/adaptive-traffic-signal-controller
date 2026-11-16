"""What Logisim-evolution does to a file on opening, pinned so the demo opens unchanged.

- Labels that are not valid HDL names (com.cburch.logisim.util.SyntaxChecker) are renamed
  on load: "Traffic NS" became "Traffic_NS_498072b2".
- Labels and text without an explicit font get evolution's default, SansSerif bold 16,
  which is much wider than 2.7.1's plain 12 that the layout is measured for.
"""
import re
import xml.etree.ElementTree as ET

import pytest

from hw.geometry import LABEL_FONT
from hw.rom import encode_rom, uniform_policy
from hw.traffic_controller import build_demo_circuit, build_test_circuit

ROM = encode_rom(uniform_policy(5, 3))

# reserved words of VHDL-93 and Verilog-2001 (evolution rejects both, case-insensitively for VHDL)
HDL_KEYWORDS = set("""
abs access after alias all and architecture array assert attribute begin block body buffer bus
case component configuration constant disconnect downto else elsif end entity exit file for
function generate generic group guarded if impure in inertial inout is label library linkage
literal loop map mod nand new next nor not null of on open or others out package port postponed
procedure process pure range record register reject rem report return rol ror select severity
signal shared sla sll sra srl subtype then to transport type unaffected units until use variable
wait when while with xnor xor
always assign automatic casex casez cell config deassign default defparam design disable edge
endcase endconfig endfunction endgenerate endmodule endprimitive endspecify endtable endtask
event force forever fork genvar highz0 highz1 ifnone incdir include initial input instance
integer join large liblist localparam macromodule medium module negedge noshowcancelled nmos
notif0 notif1 output parameter pmos posedge primitive pull0 pull1 pulldown pullup
pulsestyle_onevent pulsestyle_ondetect rcmos real realtime reg release repeat rnmos rpmos rtran
rtranif0 rtranif1 scalared showcancelled signed small specify specparam strong0 strong1 supply0
supply1 table task time tran tranif0 tranif1 tri tri0 tri1 triand trior trireg unsigned vectored
wand weak0 weak1 wire wor
""".split())


def evolution_accepts(label: str) -> bool:
    return (re.fullmatch(r"[A-Za-z]+\w*", label) is not None and "__" not in label
            and not label.endswith("_") and label.lower() not in HDL_KEYWORDS)


def test_checker_matches_evolution_examples():
    assert evolution_accepts("Traffic_NS") and evolution_accepts("S1_next") and evolution_accepts("one4")
    for bad in ("Traffic NS", "4bits", "a__b", "done_", "next", "Buffer", "wire"):
        assert not evolution_accepts(bad), bad


CASES = [(w, t) for w in ("demo", "test") for t in ("evolution", "2.7.1")]


@pytest.fixture(params=CASES, ids=lambda p: f"{p[0]}-{p[1]}")
def comps(request):
    which, target = request.param
    xml = (build_demo_circuit(ROM, target) if which == "demo"
           else build_test_circuit(ROM, 1, 2, ticks=10, target=target))
    return [(e.get("name"), {a.get("name"): a.get("val") for a in e.findall("a")})
            for e in ET.fromstring(xml).iter("comp")]


def test_every_label_is_a_valid_hdl_name(comps):
    bad = [a["label"] for name, a in comps if a.get("label") and not evolution_accepts(a["label"])]
    assert bad == []


def test_labels_and_text_have_an_explicit_font(comps):
    assert LABEL_FONT == "SansSerif plain 12"  # what 2.7.1 uses, and what the layout is measured for
    missing = [(name, a.get("label") or a.get("text")) for name, a in comps
               if (a.get("label") and a.get("labelfont") != LABEL_FONT)
               or (name == "Text" and a.get("font") != LABEL_FONT)]
    assert missing == []
