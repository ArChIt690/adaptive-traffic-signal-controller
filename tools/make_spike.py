"""Throwaway spike: writes tools/spike.circ to check Logisim 2.7.1 behaviour headless.

Checks: counter count-down (ld=1,ct=1) / load (ld=1,ct=0), carry, D flip-flop port
order, splitter bit->end mapping, ROM with contents + unconnected sel, 2:1 mux,
tunnels on ports, and the `halt` pin.
"""
from pathlib import Path

comps = []


def comp(lib, name, loc, **attrs):
    a = "".join(f'<a name="{k}" val="{v}"/>' for k, v in attrs.items())
    comps.append(f'<comp lib="{lib}" loc="({loc[0]},{loc[1]})" name="{name}">{a}</comp>')


def tun(label, loc, width=1):
    comp(0, "Tunnel", loc, width=width, label=label)


def out_pin(label, loc, width=1):
    comp(0, "Pin", loc, facing="west", output="true", width=width, label=label)
    tun(label, loc, width)


# clock
comp(0, "Clock", (50, 50)); tun("clk", (50, 50))
# tick counter 8 bit, max 12, carry -> halt
x, y = 200, 100
comp(4, "Counter", (x, y), width=8, max="0xc")
tun("clk", (x - 20, y + 20)); tun("tick", (x, y), 8); tun("halt_s", (x, y + 10))
# down counter: ld=1, ct = ctl ; data = 9
x, y = 200, 250
comp(4, "Counter", (x, y), width=4, max="0xf")
tun("clk", (x - 20, y + 20)); tun("T", (x, y), 4); tun("nine", (x - 30, y), 4)
tun("one", (x - 30, y - 10)); tun("ctl", (x - 30, y + 10))
comp(0, "Constant", (100, 250), width=4, value="0x9"); tun("nine", (100, 250), 4)
comp(0, "Constant", (100, 300), value="0x1"); tun("one", (100, 300))
# ctl = DFF toggling: D = nQ  -> ctl alternates 0,1,0,1 (checks DFF port order)
x, y = 400, 100
comp(4, "D Flip-Flop", (x, y))
tun("nq", (x - 40, y + 20)); tun("clk", (x - 40, y)); tun("ctl", (x, y)); tun("nq", (x, y + 20))
# splitter: tick (8) -> low nibble end0? high nibble end1?
x, y = 400, 300
comp(0, "Splitter", (x, y), fanout=2, incoming=8, bit0=0, bit1=0, bit2=0, bit3=0, bit4=1, bit5=1, bit6=1, bit7=1)
tun("tick", (x, y), 8); tun("end0", (x + 20, y - 20), 4); tun("end1", (x + 20, y - 10), 4)
# ROM addr = end0 (tick low nibble), data 8 bit
x, y = 700, 300
comp(4, "ROM", (x, y), addrWidth=4, dataWidth=8)
# contents must be element text, not a val attribute (attribute newlines get normalised)
comps[-1] = comps[-1].replace("</comp>", '<a name="contents">addr/data: 4 8\n10 21 32 43 54 65 76 87\n98 a9 ba cb dc ed fe 0f\n</a></comp>')
tun("end0", (x - 140, y), 4); tun("rom", (x, y), 8)
# mux: sel = ctl, in0 = end0, in1 = Constant 0xa
x, y = 700, 100
comp(2, "Multiplexer", (x, y), select=1, width=4)
tun("end0", (x - 30, y - 10), 4); tun("ten", (x - 30, y + 10), 4); tun("ctl", (x - 20, y + 20)); tun("mux", (x, y), 4)
comp(0, "Constant", (600, 200), width=4, value="0xa"); tun("ten", (600, 200), 4)

# outputs (top-down order = column order)
for i, (lbl, w) in enumerate([("tick", 8), ("ctl", 1), ("T", 4), ("end0", 4), ("end1", 4), ("rom", 8), ("mux", 4)]):
    out_pin(lbl, (1000, 50 + 40 * i), w)
comp(0, "Pin", (1000, 400), facing="west", output="true", label="halt"); tun("halt_s", (1000, 400))

libs = ["#Wiring", "#Gates", "#Plexers", "#Arithmetic", "#Memory", "#I/O", "#Base"]
xml = ['<?xml version="1.0" encoding="UTF-8" standalone="no"?>', '<project source="2.7.1" version="1.0">']
xml += [f'<lib desc="{d}" name="{i}"/>' for i, d in enumerate(libs)]
xml += ['<main name="main"/>', '<circuit name="main">'] + comps + ["</circuit>", "</project>"]
Path(__file__).with_name("spike.circ").write_text("\n".join(xml), encoding="utf-8")
