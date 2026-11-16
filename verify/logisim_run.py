"""Run a generated test circuit headless in Logisim and read back one Row per tick.

Works with Logisim 2.7.1 and Logisim-evolution: with a `halt` pin in the circuit, both print
the same `-tty table` format. The test circuit's output pins, top to bottom, must be:
tick(8), S1, S0, T(4), NS_R, NS_Y, NS_G, EW_R, EW_Y, EW_G   (plus a `halt` pin, not printed).
"""
import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from verify.reference import Row

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
COLUMNS = ["tick", "S1", "S0", "T", "NS_R", "NS_Y", "NS_G", "EW_R", "EW_Y", "EW_G"]


@dataclass(frozen=True)
class Engine:
    """One Logisim installation: how to start it, and which circuit layout (target) it needs."""
    name: str
    command: tuple[str, ...]  # program and arguments that come before the .circ file
    target: str               # "2.7.1" or "evolution" (see hw/geometry.py)


def _java_for_evolution(env) -> str | None:
    """Logisim-evolution needs a newer Java than 2.7.1 (3.8: Java 16+, 3.9 and later: Java 21+)."""
    if env.get("LOGISIM_EVOLUTION_JAVA"):
        return env["LOGISIM_EVOLUTION_JAVA"]
    if env.get("JAVA_HOME"):
        for exe in ("java.exe", "java"):
            p = Path(env["JAVA_HOME"]) / "bin" / exe
            if p.exists():
                return str(p)
    return None


def engines(tools: Path = TOOLS, env=os.environ) -> list[Engine]:
    """Logisim 2.7.1 from tools/logisim-generic-2.7.1.jar (or $LOGISIM_JAR), plus one engine per
    tools/evolution-*/ folder: its packaged launcher if it has one (that brings its own Java),
    else its -all.jar run with $LOGISIM_EVOLUTION_JAVA or $JAVA_HOME's java."""
    found = []
    jar = Path(env.get("LOGISIM_JAR", tools / "logisim-generic-2.7.1.jar"))
    if jar.exists():
        found.append(Engine("2.7.1", ("java", "-jar", str(jar)), "2.7.1"))
    for d in sorted(p for p in tools.glob("evolution-*") if p.is_dir()):
        exes = sorted(d.rglob("logisim-evolution.exe"))
        if exes:
            found.append(Engine(d.name, (str(exes[0]),), "evolution"))
            continue
        jars, java = sorted(d.rglob("logisim-evolution-*-all.jar")), _java_for_evolution(env)
        if jars and java:
            found.append(Engine(d.name, (java, "-jar", str(jars[0])), "evolution"))
    return found


def run_table(circ_xml: str, engine: Engine, timeout_s: float = 120) -> subprocess.CompletedProcess:
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "circuit.circ"
        f.write_text(circ_xml, encoding="utf-8")
        return subprocess.run([*engine.command, str(f), "-tty", "table"],
                              capture_output=True, text=True, timeout=timeout_s)


def _bits(s: str) -> int:
    s = s.replace(" ", "")
    if not s or set(s) - {"0", "1"}:
        raise ValueError(f"undefined or error value in Logisim output: {s!r}")
    return int(s, 2)


def run_logisim(circ_xml: str, engine: Engine, timeout_s: float = 120) -> list[Row]:
    proc = run_table(circ_xml, engine, timeout_s)
    if proc.returncode != 0:
        raise RuntimeError(f"Logisim {engine.name} exited {proc.returncode}: {proc.stderr or proc.stdout}")
    by_tick: dict[int, Row] = {}
    for line in proc.stdout.splitlines():
        if not line.strip():
            continue
        cells = line.split("\t")
        if len(cells) != len(COLUMNS):
            raise ValueError(f"expected {len(COLUMNS)} columns, got {line!r}")
        v = dict(zip(COLUMNS, map(_bits, cells)))
        by_tick[v["tick"]] = Row(v["tick"], 2 * v["S1"] + v["S0"], v["T"],
                                 tuple(v[k] for k in COLUMNS[4:]))
    return [by_tick[t] for t in sorted(by_tick)]
