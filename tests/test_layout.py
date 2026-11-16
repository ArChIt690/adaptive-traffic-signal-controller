"""Readability of the generated circuit: tunnel labels must not sit on parts or on each other."""
import re
import xml.etree.ElementTree as ET

import pytest

from hw.geometry import bounds, text_box, tunnel_box
from hw.rom import encode_rom, uniform_policy
from hw.traffic_controller import build_demo_circuit, build_test_circuit

ROM = encode_rom(uniform_policy(5, 3))


def _xy(s):
    return tuple(map(int, re.findall(r"-?\d+", s)))


def _parse(xml, target):
    """parts, tunnels, wires, texts; a tunnel is (label, label box, point)."""
    parts, tunnels, wires, texts = [], [], [], []
    for e in ET.fromstring(xml).iter("comp"):
        name, (x, y) = e.get("name"), _xy(e.get("loc"))
        attrs = {a.get("name"): (a.get("val") if a.get("val") is not None else a.text) for a in e.findall("a")}
        if name == "Tunnel":
            dx, dy, w, h = tunnel_box(attrs["label"], attrs["facing"])
            tunnels.append((attrs["label"], (x + dx, y + dy, w, h), (x, y)))
        elif name == "Text":
            dx, dy, w, h = text_box(attrs["text"])
            texts.append((attrs["text"], (x + dx, y + dy, w, h)))
        else:
            dx, dy, w, h = bounds(name, attrs, target)
            parts.append((name, (x + dx, y + dy, w, h)))
    for w in ET.fromstring(xml).iter("wire"):
        wires.append((_xy(w.get("from")), _xy(w.get("to"))))
    return parts, tunnels, wires, texts


def _overlap(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return min(ax + aw, bx + bw) - max(ax, bx) > 0 and min(ay + ah, by + bh) - max(ay, by) > 0


@pytest.fixture(params=[(w, t) for w in ("demo", "test") for t in ("evolution", "2.7.1")],
                ids=lambda p: f"{p[0]}-{p[1]}")
def layout(request):
    which, target = request.param
    xml = (build_demo_circuit(ROM, target) if which == "demo"
           else build_test_circuit(ROM, 1, 2, ticks=10, target=target))
    return _parse(xml, target)


def test_parts_do_not_overlap(layout):
    # evolution's ROM is much bigger than 2.7.1's (240 x 140), so check it sits on nothing
    parts, _, _, _ = layout
    hits = [(a, b) for i, (a, ba) in enumerate(parts) for b, bb in parts[i + 1:] if _overlap(ba, bb)]
    assert hits == []


def test_tunnel_labels_clear_of_parts(layout):
    parts, tunnels, _, _ = layout
    hits = [(label, name) for label, box, _ in tunnels for name, body in parts if _overlap(box, body)]
    assert hits == []


def test_tunnel_labels_do_not_overlap(layout):
    _, tunnels, _, _ = layout
    hits = [(a, b) for i, (a, ba, _) in enumerate(tunnels) for b, bb, _ in tunnels[i + 1:] if _overlap(ba, bb)]
    assert hits == []


def test_wire_ends_never_land_mid_wire(layout):
    _, _, wires, _ = layout

    def inside(p, seg):
        (x1, y1), (x2, y2) = seg
        if x1 == x2 == p[0]:
            return min(y1, y2) < p[1] < max(y1, y2)
        if y1 == y2 == p[1]:
            return min(x1, x2) < p[0] < max(x1, x2)
        return False

    bad = [(p, s) for w in wires for p in w for s in wires if s is not w and inside(p, s)]
    assert bad == []


def test_wires_are_straight(layout):
    _, _, wires, _ = layout
    assert all(a[0] == b[0] or a[1] == b[1] for a, b in wires)


def test_text_clear_of_parts_labels_and_other_text(layout):
    parts, tunnels, _, texts = layout
    others = parts + [(label, box) for label, box, _ in tunnels]
    hits = [(t, o) for t, tb in texts for o, ob in others if _overlap(tb, ob)]
    hits += [(a, b) for i, (a, ba) in enumerate(texts) for b, bb in texts[i + 1:] if _overlap(ba, bb)]
    assert hits == []


CLEARANCE = 6  # px between a label and any part it is not attached to


def test_labels_keep_clear_of_parts_they_do_not_belong_to(layout):
    # a label right against another part reads as that part's input (dEW/dNS beside the ROM)
    parts, tunnels, _, _ = layout

    def on(pt, body):
        x, y, w, h = body
        return x <= pt[0] <= x + w and y <= pt[1] <= y + h

    g = CLEARANCE
    hits = [(label, name) for label, (x, y, w, h), pt in tunnels for name, body in parts
            if not on(pt, body) and _overlap((x - g, y - g, w + 2 * g, h + 2 * g), body)]
    assert hits == []
