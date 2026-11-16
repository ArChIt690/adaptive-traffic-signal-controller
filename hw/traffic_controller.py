"""Generates the P6 traffic-light controller as a Logisim circuit.

Every connection is a named tunnel; the names below are the signal names used in
the report (S1, S0, done, T, load_val, ...). Only parts that behave the same in
Logisim 2.7.1 and Logisim-evolution are used. Stateful parts get appearance="classic"
(2.7.1 ignores the attribute) so evolution keeps their classic port layout. The ROM is
still laid out differently by the two, so it is placed by its data port for the chosen
`target` (default: Logisim-evolution).
"""
from hw.circ import Circuit, project_xml
from hw.geometry import DEFAULT_TARGET
from hw.rom import YELLOW, logisim_contents

G2 = {"inputs": "2", "size": "50"}
CLASSIC = {"appearance": "classic"}


def _gate(c, factory, loc, ins, out, attrs=None):
    g = c.add(factory, loc, attrs if attrs is not None else G2)
    for i, sig in enumerate(ins):
        c.connect(g, f"in{i}", sig, 1)
    c.connect(g, "out", out, 1)
    return g


def add_core(c: Circuit, rom: list[int]) -> None:
    """Controller core. Needs tunnels clk, dNS(2), dEW(2).
    Drives tunnels S1, S0, T(4), gNS(4), gEW(4), NS_R, NS_Y, NS_G, EW_R, EW_Y, EW_G.
    Occupies x 80-1100, y 40-940."""
    # ---- Row 1 ------------------------------------------------------------------------
    # 1. State register: two D flip-flops hold the FSM state S1 S0
    c.text("1. State register (S1 S0)", (170, 50))
    for y, nxt, cur in ((120, "S1_next", "S1"), (220, "S0_next", "S0")):
        ff = c.add("D Flip-Flop", (200, y), CLASSIC)
        c.connect(ff, "D", nxt, 1)
        c.connect(ff, "clk", "clk", 1)
        c.connect(ff, "Q", cur, 1)

    # 2. Next-state logic: S advances by one when the timer is done
    c.text("2. Next state", (420, 50))
    c.text("S0' = S0 xor done,  S1' = S1 xor (S0 and done)", (420, 70))
    _gate(c, "XOR Gate", (440, 120), ["S0", "done"], "S0_next")
    _gate(c, "AND Gate", (440, 220), ["S0", "done"], "c1")
    _gate(c, "XOR Gate", (440, 320), ["S1", "c1"], "S1_next")

    # 5. Output decoder: state -> lights (Moore outputs)
    c.text("5. Light decoder", (860, 50))
    _gate(c, "NOT Gate", (700, 120), ["S1"], "nS1", {})
    _gate(c, "NOT Gate", (700, 200), ["S0"], "nS0", {})
    _gate(c, "AND Gate", (880, 120), ["nS1", "nS0"], "NS_G")
    _gate(c, "AND Gate", (880, 200), ["nS1", "S0"], "NS_Y")
    _gate(c, "AND Gate", (880, 280), ["S1", "nS0"], "EW_G")
    _gate(c, "AND Gate", (880, 360), ["S1", "S0"], "EW_Y")
    _gate(c, "Buffer", (1040, 120), ["S1"], "NS_R", {})
    _gate(c, "Buffer", (1040, 200), ["nS1"], "EW_R", {})

    # ---- Row 2 ------------------------------------------------------------------------
    # 3. Timer: T_next = done ? load_val : T - 1   (register + subtractor + MUX)
    c.text("3. Timer: done = (T <= 1);  T loads load_val when done, else T - 1", (380, 450))
    sp = c.add("Splitter", (120, 540), {"fanout": "4", "incoming": "4"})
    c.connect(sp, "combined", "T", 4)
    # end0 carries bit 0 (not needed), end1..3 carry bits 1..3
    c.connect_fanned(sp, [("end1", "T1", 1), ("end2", "T2", 1), ("end3", "T3", 1)])
    _gate(c, "NOR Gate", (300, 520), ["T1", "T2", "T3"], "done", {"inputs": "3", "size": "50"})
    sub = c.add("Subtractor", (300, 640), {"width": "4"})
    c.connect(sub, "A", "T", 4)
    c.connect(sub, "B", "one4", 4)
    c.connect(sub, "out", "T_dec", 4)
    c.connect(c.add("Constant", (160, 650), {"width": "4", "value": "0x1"}), "out", "one4", 4)
    mux = c.add("Multiplexer", (480, 640), {"select": "1", "width": "4"})
    c.connect(mux, "in0", "T_dec", 4)
    c.connect(mux, "in1", "load_val", 4)
    c.connect(mux, "sel", "done", 1)
    c.connect(mux, "out", "T_next", 4)
    reg = c.add("Register", (620, 640), {"width": "4", **CLASSIC})
    c.connect(reg, "in", "T_next", 4)
    c.connect(reg, "clk", "clk", 1)
    c.connect(reg, "out", "T", 4)

    # ---- Row 3 ------------------------------------------------------------------------
    # 4. Timing ROM (filled by the AI agent) + choosing the next duration
    c.text("4. Timing ROM (AI): addr = dNS dEW, data = gNS gEW;  MUXes pick the next duration", (460, 770))
    # well left of the ROM, so dEW/dNS don't read as ROM inputs (evolution's ROM starts at x=200)
    addr = c.add("Splitter", (60, 860), {"fanout": "2", "incoming": "4",
                                         "bit0": "0", "bit1": "0", "bit2": "1", "bit3": "1"})
    c.connect(addr, "combined", "addr", 4)
    c.connect_fanned(addr, [("end0", "dEW", 2), ("end1", "dNS", 2)])
    r = c.place("ROM", "data", (440, 860),
                {"addrWidth": "4", "dataWidth": "8", "contents": logisim_contents(rom), **CLASSIC})
    c.connect(r, "addr", "addr", 4)
    c.connect(r, "data", "rom_out", 8)
    data = c.add("Splitter", (580, 860), {"fanout": "2", "incoming": "8",
                                          "bit0": "0", "bit1": "0", "bit2": "0", "bit3": "0",
                                          "bit4": "1", "bit5": "1", "bit6": "1", "bit7": "1"})
    c.connect(data, "combined", "rom_out", 8)
    c.connect_fanned(data, [("end0", "gEW", 4), ("end1", "gNS", 4)])
    m1 = c.add("Multiplexer", (780, 860), {"select": "1", "width": "4"})
    c.connect(m1, "in0", "gEW", 4)
    c.connect(m1, "in1", "gNS", 4)
    c.connect(m1, "sel", "S1", 1)
    c.connect(m1, "out", "g_next", 4)
    m2 = c.add("Multiplexer", (960, 860), {"select": "1", "width": "4"})
    c.connect(m2, "in0", "t_yellow", 4)
    c.connect(m2, "in1", "g_next", 4)
    c.connect(m2, "sel", "S0", 1)
    c.connect(m2, "out", "load_val", 4)
    c.connect(c.add("Constant", (820, 940), {"width": "4", "value": hex(YELLOW)}), "out", "t_yellow", 4)


LIGHT_COLOURS = {"R": "#ff0000", "Y": "#ffcc00", "G": "#00cc00"}


def build_demo_circuit(rom: list[int], target: str = DEFAULT_TARGET) -> str:
    """The circuit students open in Logisim: traffic-level inputs, two signal heads, displays."""
    c = Circuit("main", target)
    add_core(c, rom)

    c.text("P6 Adaptive Traffic Signal Controller  (FSM + AI timing ROM)", (1420, 30))
    menu = "Auto-Tick Enabled" if target == "evolution" else "Ticks Enabled"  # 2.7.1's name
    c.text(f"Set Traffic_NS / Traffic_EW (0-3) with the poke tool, then Simulate > {menu}", (1420, 50))

    # signal heads: one column of LEDs per road
    for x, road, name in ((1300, "NS", "North-South"), (1440, "EW", "East-West")):
        c.text(name, (x + 10, 90))
        for y, colour in ((120, "R"), (180, "Y"), (240, "G")):
            led = c.add("LED", (x, y), {"color": LIGHT_COLOURS[colour], "label": f"{road}_{colour}"})
            c.connect(led, "in0", f"{road}_{colour}", 1)

    # displays: seconds left in this phase, and the AI's green times for the current traffic
    for x, sig, label in ((1300, "T", "seconds left"), (1420, "gNS", "AI green NS"), (1540, "gEW", "AI green EW")):
        c.text(label, (x + 5, 325))
        c.connect(c.add("Hex Digit Display", (x, 400)), "in0", sig, 4)

    # not "clock": evolution removes a label equal to the part's name, with a pop-up
    clk = c.add("Clock", (1300, 560), {"label": "sys_clk"})
    c.connect(clk, "out", "clk", 1)
    # labels must be valid HDL names, or evolution renames them on load ("Traffic_NS_498072b2")
    for y, sig, label in ((640, "dNS", "Traffic_NS"), (720, "dEW", "Traffic_EW")):
        pin = c.add("Pin", (1300, y), {"width": "2", "tristate": "false", "label": label})
        c.connect(pin, "port", sig, 2)
    return project_xml([c])


TEST_OUTPUTS = [("tick", 8), ("S1", 1), ("S0", 1), ("T", 4), ("NS_R", 1), ("NS_Y", 1),
                ("NS_G", 1), ("EW_R", 1), ("EW_Y", 1), ("EW_G", 1)]


def build_test_circuit(rom: list[int], density_ns: int, density_ew: int, ticks: int,
                       target: str = DEFAULT_TARGET) -> str:
    """Headless test harness: fixed densities, output pins in TEST_OUTPUTS order, halts after `ticks`."""
    if not 1 <= ticks <= 255:
        raise ValueError("ticks must be 1-255 (8-bit tick counter)")
    c = Circuit("main", target)
    add_core(c, rom)
    c.connect(c.add("Clock", (1300, 560)), "out", "clk", 1)
    for y, sig, val in ((640, "dNS", density_ns), (720, "dEW", density_ew)):
        c.connect(c.add("Constant", (1300, y), {"width": "2", "value": hex(val)}), "out", sig, 2)
    # tick counter only counts up (load=0, count=1), which behaves the same in both Logisims
    tick = c.add("Counter", (1300, 840), {"width": "8", "max": hex(ticks), **CLASSIC})
    c.connect(tick, "clk", "clk", 1)
    c.connect_fanned(tick, [("out", "tick", 8), ("carry", "halt_sig", 1)])
    for i, (sig, w) in enumerate(TEST_OUTPUTS):
        pin = c.add("Pin", (1600, 100 + 60 * i), {"facing": "west", "output": "true",
                                                  "width": str(w), "label": sig})
        c.connect(pin, "port", sig, w)
    halt = c.add("Pin", (1600, 100 + 60 * len(TEST_OUTPUTS)), {"facing": "west", "output": "true", "label": "halt"})
    c.connect(halt, "port", "halt_sig", 1)
    return project_xml([c])
