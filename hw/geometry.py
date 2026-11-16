"""Port positions, sides and outlines of Logisim components (see docs/logisim-notes.md).

Offsets are relative to the component's `loc`, with the default east facing
(output Pins face west, so their body sits to the right of the port).

Two targets: "2.7.1" (original Logisim) and "evolution" (Logisim-evolution, tested in
3.8.0 and 5.0.0). They agree on every part used here except the ROM, which evolution anchors
at its top-left corner (and the unused hex-display decimal point and D flip-flop enable).
"""

TARGETS = ("evolution", "2.7.1")
DEFAULT_TARGET = "evolution"   # the lab uses Logisim-evolution
EVOLUTION_SOURCE = "3.8.0"     # header version for evolution files: the oldest evolution tested

LIB_NAMES = ["#Wiring", "#Gates", "#Plexers", "#Arithmetic", "#Memory", "#I/O", "#Base"]

LIB: dict[str, int] = {
    "Pin": 0, "Constant": 0, "Tunnel": 0, "Clock": 0, "Splitter": 0,
    "NOT Gate": 1, "Buffer": 1, "AND Gate": 1, "XOR Gate": 1, "NOR Gate": 1,
    "Multiplexer": 2,
    "Subtractor": 3,
    "D Flip-Flop": 4, "Counter": 4, "Register": 4, "ROM": 4,
    "LED": 5, "Hex Digit Display": 5,
    "Text": 6,
}

# port -> (dx, dy, side); side is the edge of the body the port sits on: W, E, S or N
_FIXED: dict[str, dict[str, tuple[int, int, str]]] = {
    "Constant": {"out": (0, 0, "E")},
    "Clock": {"out": (0, 0, "E")},
    "NOT Gate": {"out": (0, 0, "E"), "in0": (-30, 0, "W")},
    "Buffer": {"out": (0, 0, "E"), "in0": (-20, 0, "W")},
    "D Flip-Flop": {"D": (-40, 20, "W"), "clk": (-40, 0, "W"), "Q": (0, 0, "E"), "nQ": (0, 20, "E"),
                    "reset": (-10, 30, "S"), "preset": (-30, 30, "S"), "enable": (-20, 30, "S")},
    "Counter": {"out": (0, 0, "E"), "data": (-30, 0, "W"), "clk": (-20, 20, "S"), "clear": (-10, 20, "S"),
                "load": (-30, -10, "W"), "count": (-30, 10, "W"), "carry": (0, 10, "E")},
    "Register": {"out": (0, 0, "E"), "in": (-30, 0, "W"), "clk": (-20, 20, "S"), "clear": (-10, 20, "S"),
                 "enable": (-30, 10, "W")},
    "Subtractor": {"A": (-40, -10, "W"), "B": (-40, 10, "W"), "out": (0, 0, "E"),
                   "b_in": (-20, -20, "N"), "b_out": (-20, 20, "S")},
    "ROM": {"data": (0, 0, "E"), "addr": (-140, 0, "W"), "sel": (-90, 40, "S")},
    "Multiplexer": {"in0": (-30, -10, "W"), "in1": (-30, 10, "W"), "sel": (-20, 20, "S"), "out": (0, 0, "E")},
    "LED": {"in0": (0, 0, "W")},
    "Hex Digit Display": {"in0": (0, 0, "S"), "dp": (10, 0, "S")},
}

# where Logisim-evolution differs (tools/PortDumpEvo.java; same in 3.8.0 and 5.0.0)
_EVOLUTION_FIXED: dict[str, dict[str, tuple[int, int, str]]] = {
    "ROM": {"addr": (0, 10, "W"), "data": (240, 60, "E")},  # no chip-select port
    "Hex Digit Display": {"in0": (0, 0, "S"), "dp": (20, 0, "S")},
    "D Flip-Flop": {k: v for k, v in _FIXED["D Flip-Flop"].items() if k != "enable"},
}

# outline (dx, dy, w, h) for parts whose outline doesn't depend on attributes
_BOUNDS: dict[str, tuple[int, int, int, int]] = {
    "Constant": (-16, -8, 16, 16), "Clock": (-20, -10, 20, 20),
    "NOT Gate": (-30, -9, 30, 18), "Buffer": (-20, -9, 20, 18),
    "AND Gate": (-50, -25, 50, 50), "XOR Gate": (-60, -25, 60, 50), "NOR Gate": (-60, -25, 60, 50),
    "D Flip-Flop": (-40, -10, 40, 40), "Counter": (-30, -20, 30, 40), "Register": (-30, -20, 30, 40),
    "Subtractor": (-40, -20, 40, 40), "ROM": (-140, -40, 140, 80), "Multiplexer": (-30, -20, 30, 40),
    "LED": (0, -10, 20, 20), "Hex Digit Display": (-15, -60, 40, 60),
}
_EVOLUTION_BOUNDS: dict[str, tuple[int, int, int, int]] = {"ROM": (0, 0, 240, 140)}


def check_target(target: str) -> str:
    if target not in TARGETS:
        raise ValueError(f"unknown Logisim target {target!r}; use one of {TARGETS}")
    return target


def _gate_ports(factory: str, attrs: dict[str, str]) -> dict[str, tuple[int, int, str]]:
    n = int(attrs.get("inputs", "2"))
    if attrs.get("size", "50") != "50":
        raise ValueError("only size 50 gates are mapped")
    x = -50 if factory == "AND Gate" else -60
    ys = {2: (-20, 20), 3: (-20, 0, 20)}[n]
    return {"out": (0, 0, "E"), **{f"in{i}": (x, y, "W") for i, y in enumerate(ys)}}


def _splitter_ports(attrs: dict[str, str]) -> dict[str, tuple[int, int, str]]:
    fanout = int(attrs.get("fanout", "2"))
    return {"combined": (0, 0, "W"), **{f"end{i}": (20, -10 * fanout + 10 * i, "E") for i in range(fanout)}}


def _ports(factory: str, attrs: dict[str, str], target: str) -> dict[str, tuple[int, int, str]]:
    if check_target(target) == "evolution" and factory in _EVOLUTION_FIXED:
        return _EVOLUTION_FIXED[factory]
    if factory in ("AND Gate", "XOR Gate", "NOR Gate"):
        return _gate_ports(factory, attrs)
    if factory == "Splitter":
        return _splitter_ports(attrs)
    if factory == "Pin":
        return {"port": (0, 0, "W" if attrs.get("output") == "true" else "E")}
    return _FIXED[factory]


def port_offset(factory: str, attrs: dict[str, str], port: str,
                target: str = DEFAULT_TARGET) -> tuple[int, int]:
    dx, dy, _ = _ports(factory, attrs, target)[port]
    return dx, dy


def port_side(factory: str, attrs: dict[str, str], port: str, target: str = DEFAULT_TARGET) -> str:
    return _ports(factory, attrs, target)[port][2]


def bounds(factory: str, attrs: dict[str, str], target: str = DEFAULT_TARGET) -> tuple[int, int, int, int]:
    if check_target(target) == "evolution" and factory in _EVOLUTION_BOUNDS:
        return _EVOLUTION_BOUNDS[factory]
    if factory == "Pin":
        w = max(20, 10 * int(attrs.get("width", "1")))
        return (0, -10, w, 20) if attrs.get("output") == "true" else (-w, -10, w, 20)
    if factory == "Splitter":
        fanout = int(attrs.get("fanout", "2"))
        return 0, -10 * fanout, 21, 10 * fanout + 1
    return _BOUNDS[factory]


# Font written on every label and text. It is 2.7.1's default; evolution's default is
# SansSerif bold 16, far wider than the layout below is measured for, so it is always explicit.
LABEL_FONT = "SansSerif plain 12"

# Tunnel label box, from Tunnel.computeBounds: 12 pt font, MARGIN 3, ARROW_MARGIN 5.
# Logisim estimates 6 px per character; 7 is used here to leave room for real font metrics.
CHAR_W = 7


def text_box(text: str) -> tuple[int, int, int, int]:
    """Outline of a Text part: centred on its loc, baseline at its loc (Logisim's defaults)."""
    w = CHAR_W * len(text)
    return -w // 2, -12, w, 15


def tunnel_box(label: str, facing: str) -> tuple[int, int, int, int]:
    bw, bh = max(10, CHAR_W * len(label)), 12
    if facing == "east":   # point on the east, label to the west
        return -8 - bw, -9, bw + 8, bh + 6
    if facing == "west":
        return 0, -9, bw + 8, bh + 6
    if facing == "north":  # point on top, label below
        return -bw // 2 - 3, 0, bw + 6, bh + 8
    return -bw // 2 - 3, -bh - 8, bw + 6, bh + 8
