"""Tiny writer for Logisim .circ files, for Logisim-evolution or Logisim 2.7.1 (the `target`).

Components are joined by named tunnels placed on their ports, so no long wires have to be
routed: two tunnels carrying the same signal name are connected. Each tunnel points at its
port and its label sits on the far side, away from the component body.
"""
import xml.etree.ElementTree as ET

from hw.geometry import (DEFAULT_TARGET, EVOLUTION_SOURCE, LABEL_FONT, LIB, LIB_NAMES,
                         check_target, port_offset, port_side)

MIN_SPACING = 60  # px between component locs, keeps ports from touching by accident
FAN_PITCH = 20    # ports 10 px apart are fanned out to this pitch so their labels don't collide
_TEXT_ATTRS = {"contents"}  # attributes Logisim stores as element text
_FACING = {"W": "east", "E": "west", "S": "north", "N": "south"}  # tunnel facing per port side


class Comp:
    def __init__(self, factory: str, loc: tuple[int, int], attrs: dict[str, str], target: str):
        self.factory, self.loc, self.attrs, self.target = factory, loc, attrs, target

    def port(self, name: str) -> tuple[int, int]:
        dx, dy = port_offset(self.factory, self.attrs, name, self.target)
        return self.loc[0] + dx, self.loc[1] + dy

    def side(self, name: str) -> str:
        return port_side(self.factory, self.attrs, name, self.target)


class Circuit:
    def __init__(self, name: str = "main", target: str = DEFAULT_TARGET):
        self.name, self.target = name, check_target(target)
        self.comps: list[Comp] = []
        self._extras: list[Comp] = []  # tunnels and text: exempt from spacing check
        self.wires: list[tuple[tuple[int, int], tuple[int, int]]] = []

    def add(self, factory: str, loc: tuple[int, int], attrs: dict[str, str] | None = None) -> Comp:
        if loc[0] % 10 or loc[1] % 10:
            raise ValueError(f"{factory} at {loc}: coordinates must be multiples of 10")
        for c in self.comps:
            if max(abs(c.loc[0] - loc[0]), abs(c.loc[1] - loc[1])) < MIN_SPACING:
                raise ValueError(f"{factory} at {loc} is too close to {c.factory} at {c.loc}")
        attrs = dict(attrs or {})
        if attrs.get("label"):
            attrs.setdefault("labelfont", LABEL_FONT)  # else evolution draws it in bold 16
        comp = Comp(factory, loc, attrs, self.target)
        self.comps.append(comp)
        return comp

    def place(self, factory: str, port: str, at: tuple[int, int], attrs: dict[str, str] | None = None) -> Comp:
        """Add a part so that its `port` lands on `at`, whatever the part's anchor is in this target."""
        dx, dy = port_offset(factory, dict(attrs or {}), port, self.target)
        return self.add(factory, (at[0] - dx, at[1] - dy), attrs)

    def tunnel(self, label: str, at: tuple[int, int], width: int, facing: str = "east") -> None:
        self._extras.append(Comp("Tunnel", at, {"facing": facing, "width": str(width), "label": label,
                                                "labelfont": LABEL_FONT}, self.target))

    def wire(self, a: tuple[int, int], b: tuple[int, int]) -> None:
        if a != b:
            if a[0] != b[0] and a[1] != b[1]:
                raise ValueError(f"wire {a}->{b} must be horizontal or vertical")
            self.wires.append((a, b))

    def connect(self, comp: Comp, port: str, signal: str, width: int) -> None:
        self.tunnel(signal, comp.port(port), width, _FACING[comp.side(port)])

    def connect_fanned(self, comp: Comp, items: list[tuple[str, str, int]]) -> None:
        """Connect ports that sit 10 px apart on one vertical edge (E or W), spreading their
        tunnels to FAN_PITCH with short wires so the labels don't stack on each other."""
        sides = {comp.side(p) for p, _, _ in items}
        if len(sides) != 1 or not sides <= {"E", "W"}:
            raise ValueError("connect_fanned needs ports on one east or west edge")
        s = 1 if sides == {"E"} else -1
        items = sorted(items, key=lambda it: comp.port(it[0])[1])
        k = (len(items) - 1) // 2  # this port keeps its height; the others move away from it
        moves = [10 * (i - k) for i in range(len(items))]
        # the port that moves furthest turns closest to the body, so no wires touch
        far = max(abs(m) for m in moves)
        x_tunnel = comp.port(items[0][0])[0] + s * (far + 20)
        for (port, signal, width), move in zip(items, moves):
            x0, y0 = comp.port(port)
            if move:
                x_turn = x0 + s * (far - abs(move) + 10)
                self.wire((x0, y0), (x_turn, y0))
                self.wire((x_turn, y0), (x_turn, y0 + move))
                self.wire((x_turn, y0 + move), (x_tunnel, y0 + move))
            else:
                self.wire((x0, y0), (x_tunnel, y0))
            self.tunnel(signal, (x_tunnel, y0 + move), width, "west" if s == 1 else "east")

    def text(self, text: str, at: tuple[int, int]) -> None:
        self._extras.append(Comp("Text", at, {"text": text, "font": LABEL_FONT}, self.target))

    def element(self) -> ET.Element:
        root = ET.Element("circuit", name=self.name)
        for a, b in self.wires:
            ET.SubElement(root, "wire", {"from": f"({a[0]},{a[1]})", "to": f"({b[0]},{b[1]})"})
        for c in self.comps + self._extras:
            e = ET.SubElement(root, "comp", lib=str(LIB[c.factory]), loc=f"({c.loc[0]},{c.loc[1]})", name=c.factory)
            for k, v in c.attrs.items():
                a = ET.SubElement(e, "a", name=k)
                if k in _TEXT_ATTRS:
                    a.text = v
                else:
                    a.set("val", v)
        return root

    def to_xml(self) -> str:
        return ET.tostring(self.element(), encoding="unicode")


def project_xml(circuits: list[Circuit], main: str = "main") -> str:
    targets = {c.target for c in circuits}
    if len(targets) != 1:
        raise ValueError(f"all circuits in a project need the same target, got {sorted(targets)}")
    source = "2.7.1" if targets == {"2.7.1"} else EVOLUTION_SOURCE
    root = ET.Element("project", source=source, version="1.0")
    for i, desc in enumerate(LIB_NAMES):
        ET.SubElement(root, "lib", desc=desc, name=str(i))
    ET.SubElement(root, "main", name=main)
    for c in circuits:
        root.append(c.element())
    return '<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n' + ET.tostring(root, encoding="unicode")
