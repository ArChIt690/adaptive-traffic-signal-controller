"""Timing ROM: the link between the AI agent and the circuit.

Address = (dNS << 2) | dEW   (traffic level 0-3 on each road)
Data    = (gNS << 4) | gEW   (green seconds for each road)
"""

YELLOW = 2
G_MIN, G_MAX = 2, 15
LEVELS = range(4)

Policy = dict[tuple[int, int], tuple[int, int]]


def uniform_policy(g_ns: int, g_ew: int) -> Policy:
    return {(a, b): (g_ns, g_ew) for a in LEVELS for b in LEVELS}


def encode_rom(policy: Policy) -> list[int]:
    rom = []
    for d_ns in LEVELS:
        for d_ew in LEVELS:
            if (d_ns, d_ew) not in policy:
                raise ValueError(f"policy has no entry for densities {(d_ns, d_ew)}")
            g_ns, g_ew = policy[(d_ns, d_ew)]
            for g in (g_ns, g_ew):
                if not G_MIN <= g <= G_MAX:
                    raise ValueError(f"green time {g} for {(d_ns, d_ew)} outside {G_MIN}-{G_MAX}")
            rom.append((g_ns << 4) | g_ew)
    return rom


def decode_rom(rom: list[int]) -> Policy:
    return {(addr >> 2, addr & 3): (byte >> 4, byte & 0xF) for addr, byte in enumerate(rom)}


def _hex_lines(rom: list[int]) -> str:
    return "".join(" ".join(f"{b:02x}" for b in rom[i:i + 8]) + "\n" for i in range(0, len(rom), 8))


def logisim_contents(rom: list[int]) -> str:
    """Value of the ROM component's `contents` attribute in a .circ file."""
    return "addr/data: 4 8\n" + _hex_lines(rom)


def raw_image(rom: list[int]) -> str:
    """Logisim memory image file (File > Load Image in the ROM's menu)."""
    return "v2.0 raw\n" + _hex_lines(rom)
