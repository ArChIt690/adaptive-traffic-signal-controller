# P6 Adaptive Traffic Signal Controller — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A Logisim 2.7.1 traffic-light controller (FSM + timer + timing ROM) whose ROM is filled by a Python Q-learning agent trained on a traffic simulator, with proof that circuit and a Python reference model agree tick-for-tick.

**Architecture:** Python generates the `.circ` XML (components connected by named tunnels, so no hand-routed wires). The same generator emits a *demo* variant (input pins, LEDs, hex display) and a *test* variant (constant densities, output pins, tick counter, `halt` pin) that runs headless via `java -jar logisim.jar -tty table`. The AI side (simulator → Q-learning → ROM bytes) is plain Python; `make_all.py` chains training, export, chart generation and circuit generation.

**Tech Stack:** Python 3.11 (project venv), numpy, matplotlib, pytest; Logisim 2.7.1 generic jar on Java 8; javac 17 (`--release 8`) only for the spike helper.

**Spec:** `docs/superpowers/specs/2026-11-16-adaptive-traffic-signal-design.md`

## Global Constraints

- Circuit file: Logisim 2.7.1 format (`<project source="2.7.1" version="1.0">`), built-in libraries only (Wiring, Gates, Plexers, Arithmetic, Memory, I/O, Base).
- Two roads NS and EW; FSM states `00 NS_GREEN → 01 NS_YELLOW → 10 EW_GREEN → 11 EW_YELLOW → 00`.
- Yellow fixed 2 s; green 2–15 s (4-bit); 1 clock tick = 1 s.
- ROM: address = `(dNS << 2) | dEW` (4-bit, 16 entries); data = `(gNS << 4) | gEW` (8-bit).
- Density levels 0–3 per road (2-bit).
- Python deps limited to numpy, matplotlib (+ pytest for tests).
- All randomness seeded; `make_all.py` is reproducible run-to-run.
- No git commits unless the user asks (folder is not a repo yet).
- Load the `dataviz` skill before writing any chart code.

## Review Focus

1. **Densities changed mid-phase** — must only affect the *next* green load, never the running countdown. Test in Task 3.
2. **Out-of-range green times** (0, 1, 16+) reaching the ROM — `encode_rom` must raise `ValueError`. Test in Task 3.
3. **Opening the demo file in Logisim-evolution** — can't run evolution here; guard by asserting only built-in libs and `source="2.7.1"`. Test in Task 5; manual open check listed in README.
4. **Zero traffic** (density 0/0, possibly no arrivals) — simulator returns `avg_wait == 0.0`, no division error. Test in Task 6.
5. **Saturated traffic** (3/3) — simulator stays finite, agent gives more total green than for 0/0. Tests in Tasks 6 and 7.

---

## File Structure

```
requirements.txt            numpy, matplotlib, pytest
pytest.ini                  markers: logisim (needs jar), slow
tools/                      downloaded logisim-generic-2.7.1.jar; spike helper PortDump.java
docs/logisim-notes.md       spike findings: port offsets, counter semantics, tty format
hw/rom.py                   constants + ROM encode/decode/format
hw/geometry.py              port offsets per component (from spike notes)
hw/circ.py                  tiny .circ XML writer (Circuit, Comp, tunnels)
hw/traffic_controller.py    core controller + demo/test variants
verify/reference.py         cycle-accurate Python model of the circuit
verify/logisim_run.py       run jar headless, parse table into Rows
ai/traffic.py               traffic simulator
ai/agent.py                 Q-learning agent, baseline, evaluation
ai/report.py                charts + CSV tables
make_all.py                 train → export → charts → logisim/traffic_controller.circ
logisim/traffic_controller.circ   generated demo circuit
results/                    generated charts, CSVs, policy.json, timing_rom.txt
docs/state-diagram.md       mermaid state diagram + state/ROM tables for report
README.md                   run + demo instructions
tests/                      test_*.py per module
```

---

### Task 1: Environment + Logisim spike

Throwaway investigation whose only lasting outputs are the venv, the jar, and `docs/logisim-notes.md`. Every later hardware task depends on these notes.

**Files:**
- Create: `requirements.txt`, `pytest.ini`, `tools/PortDump.java`, `tools/spike.circ`, `docs/logisim-notes.md`

**Produces:** `docs/logisim-notes.md` containing, for each factory below, the port names you'll use and their `(dx, dy)` offset from the component's `loc` with the stated attributes; plus the facts in Step 4.

- [ ] **Step 1: venv and deps**

Run: `python -m venv .venv` then `.venv/Scripts/python -m pip install numpy matplotlib pytest`
Write `requirements.txt` (the three names) and `pytest.ini` registering markers `logisim` and `slow`.
Expected: `.venv/Scripts/python -c "import numpy, matplotlib, pytest"` exits 0.

- [ ] **Step 2: download Logisim 2.7.1**

Download `logisim-generic-2.7.1.jar` from the SourceForge project `circuit` (path `2.7.x/2.7.1/`) into `tools/`. Verify it is a zip (`PK` header), record its SHA-256 in the notes.
Expected: `java -jar tools/logisim-generic-2.7.1.jar -help` prints usage including `-tty`.

- [ ] **Step 3: port offsets via PortDump**

Write `tools/PortDump.java`, compiled with `javac --release 8 -cp tools/logisim-generic-2.7.1.jar`, which for each factory creates the attribute set, applies the attributes below, creates the component at `Location.create(0,0)` and prints every `getEnds()` location with its index/width. (If the jar ships `.java` sources, cross-check against them.) Factories and attributes:

| Factory (lib) | Attributes |
|---|---|
| Pin (Wiring) | width 1/2/4/8, output true/false, facing east/west |
| Constant, Tunnel, Clock (Wiring) | width 1/2/4 |
| Splitter (Wiring) | fanout 2, incoming 4 (bits 0-1→0, 2-3→1); fanout 2, incoming 8 (0-3→0, 4-7→1); fanout 4, incoming 4 |
| NOT Gate, Buffer (Gates) | width 1 |
| AND/XOR Gate (Gates) | inputs 2, size 50 |
| NOR Gate (Gates) | inputs 3, size 50 |
| D Flip-Flop (Memory) | defaults |
| Counter (Memory) | width 4, max 0xf; width 8 |
| ROM (Memory) | addrWidth 4, dataWidth 8 |
| Multiplexer (Plexers) | select 1, width 4 |
| LED, Hex Digit Display (I/O) | defaults |

Record the table in `docs/logisim-notes.md`.

- [ ] **Step 4: behaviour facts via spike.circ**

Hand-write `tools/spike.circ` (clock, 4-bit counter, output pins incl. one labelled `halt`, joined by tunnels using Step 3 offsets) and run `java -jar tools/logisim-generic-2.7.1.jar tools/spike.circ -tty table`. Record in notes:
- table format: column order (by what?), how multi-bit values print, whether the initial state prints, whether rows print per clock toggle or only on change, that `halt`=1 stops the run;
- Counter semantics for (load, count) = (0,1), (1,0), (1,1) — expected up / load / down; and when `carry` is 1;
- whether ROM `sel` may be left unconnected;
- that tunnels placed exactly on a port location connect.

If Counter (1,1) does not count down, record it; Task 4 then builds the timer as Register + Subtractor + MUX instead (same signal names).
Expected: notes file complete; spike runs and halts.

---

### Task 2: .circ writer

**Files:**
- Create: `hw/__init__.py`, `hw/geometry.py`, `hw/circ.py`
- Test: `tests/test_circ.py`

**Interfaces:**
- Consumes: offsets from `docs/logisim-notes.md`.
- Produces:
  - `geometry.LIB: dict[str, int]` factory → lib index (Wiring 0, Gates 1, Plexers 2, Arithmetic 3, Memory 4, I/O 5, Base 6)
  - `geometry.port_offset(factory: str, attrs: dict[str, str], port: str) -> tuple[int, int]`
  - `class Comp`: `.port(name) -> tuple[int, int]` absolute
  - `class Circuit(name="main")`: `.add(factory, loc, attrs=None) -> Comp`; `.connect(comp, port, signal, width)` (puts a Tunnel labelled `signal` on that port); `.text(text, at)`; `.to_xml() -> str`
  - `project_xml(circuits: list[Circuit], main="main") -> str`
  - All coordinates multiples of 10; `.add` raises `ValueError` if a new component's bounding origin is within 60 px of an existing one (prevents accidental port overlap).

- [ ] **Step 1: failing tests**

```python
def test_project_header_and_libs():
    xml = project_xml([Circuit("main")])
    root = ET.fromstring(xml)
    assert root.get("source") == "2.7.1"
    assert {l.get("desc") for l in root.findall("lib")} <= {"#Wiring","#Gates","#Plexers","#Arithmetic","#Memory","#I/O","#Base"}

def test_connect_places_tunnel_on_port():
    c = Circuit(); g = c.add("AND Gate", (200, 200), {"inputs": "2"})
    c.connect(g, "out", "x", 1)
    tun = [e for e in ET.fromstring(c.to_xml()).iter("comp") if e.get("name") == "Tunnel"][0]
    assert tun.get("loc") == "(%d,%d)" % g.port("out")

def test_overlap_rejected():
    c = Circuit(); c.add("NOT Gate", (100, 100))
    with pytest.raises(ValueError): c.add("NOT Gate", (110, 100))

@pytest.mark.logisim
def test_counter_circuit_runs_headless():
    # clock -> 4-bit up counter (max 5) -> output pin "q"; carry -> output pin "halt"
    rows = run_raw_table(xml)        # small helper in the test: subprocess + split lines
    assert last_q_value(rows) == 5
```

- [ ] **Step 2: run, expect FAIL** — `.venv/Scripts/python -m pytest tests/test_circ.py -v` → import errors.
- [ ] **Step 3: implement `hw/geometry.py` and `hw/circ.py`** per Interfaces, using `xml.etree.ElementTree`; attribute values as Logisim strings (e.g. `"0x2"` for constants, `"#00ff00"` for LED colour).
- [ ] **Step 4: run, expect PASS** (logisim test skipped automatically if jar missing — implement via `pytest.mark.skipif(not logisim_available())` imported lazily or a local check on the jar path).

---

### Task 3: ROM encoding + reference model

**Files:**
- Create: `hw/rom.py`, `verify/__init__.py`, `verify/reference.py`
- Test: `tests/test_rom.py`, `tests/test_reference.py`

**Interfaces:**
- Produces:
  - `hw/rom.py`: `YELLOW = 2`, `G_MIN = 2`, `G_MAX = 15`; `Policy = dict[tuple[int, int], tuple[int, int]]` keyed `(dNS, dEW)` → `(gNS, gEW)`;
    `encode_rom(policy) -> list[int]` (16 ints); `decode_rom(rom) -> Policy`; `logisim_contents(rom) -> str` (`"addr/data: 4 8\n"` + hex bytes); `raw_image(rom) -> str` (`"v2.0 raw\n"` + hex bytes); `uniform_policy(g_ns, g_ew) -> Policy`
  - `verify/reference.py`: `@dataclass(frozen=True) Row(tick: int, state: int, timer: int, lights: tuple[int, int, int, int, int, int])` with lights ordered `NS_R, NS_Y, NS_G, EW_R, EW_Y, EW_G`;
    `run_reference(rom: list[int], densities: tuple[int, int] | Callable[[int], tuple[int, int]], ticks: int) -> list[Row]` returning rows for ticks `0..ticks`

Reference semantics (this *is* the hardware spec; Task 4 must match it):
```
tick 0: state = 0, timer = 0
each clock edge:  done = timer <= 1
  if done: timer = load(state, densities(at this tick)); state = (state + 1) % 4
  else:    timer = timer - 1
load(s): s0 == 0 -> YELLOW;  s0 == 1 -> (gNS if s1 else gEW)   # from rom[(dNS<<2)|dEW]
lights: NS_G = s==0, NS_Y = s==1, NS_R = s>=2, EW_G = s==2, EW_Y = s==3, EW_R = s<=1
```
(The first NS green lasts 1 tick after reset — documented startup behaviour.)

- [ ] **Step 1: failing tests**

```python
def test_encode_layout():
    p = uniform_policy(5, 3); p[(3, 1)] = (15, 2)
    rom = encode_rom(p)
    assert len(rom) == 16 and rom[0] == 0x53 and rom[13] == 0xF2
    assert decode_rom(rom) == p

@pytest.mark.parametrize("bad", [(0, 5), (1, 5), (5, 16)])
def test_encode_rejects_out_of_range(bad):
    p = uniform_policy(5, 3); p[(0, 0)] = bad
    with pytest.raises(ValueError): encode_rom(p)

def test_raw_image_header():
    assert raw_image(encode_rom(uniform_policy(5, 3))).startswith("v2.0 raw\n")

def test_reference_sequence_uniform_5_3():
    rows = run_reference(encode_rom(uniform_policy(5, 3)), (0, 0), 13)
    assert [(r.state, r.timer) for r in rows] == [
        (0,0),(1,2),(1,1),(2,3),(2,2),(2,1),(3,2),(3,1),(0,5),(0,4),(0,3),(0,2),(0,1),(1,2)]
    assert rows[8].lights == (0,0,1,1,0,0)

def test_reference_uses_density_address():
    p = uniform_policy(5, 3); p[(3, 1)] = (9, 7)
    rows = run_reference(encode_rom(p), (3, 1), 20)
    assert rows[3].timer == 7 and rows[11].timer == 9

def test_density_change_mid_green_only_affects_next_load():
    p = uniform_policy(5, 3); p[(2, 2)] = (12, 12)
    dens = lambda t: (0, 0) if t < 10 else (2, 2)
    rows = run_reference(encode_rom(p), dens, 30)
    assert [r.timer for r in rows[8:13]] == [5, 4, 3, 2, 1]   # NS green loaded at tick 7 with (0,0)
    assert any(r.timer == 12 for r in rows[13:])
```

- [ ] **Step 2: run, expect FAIL.**
- [ ] **Step 3: implement `hw/rom.py` and `verify/reference.py`.**
- [ ] **Step 4: run, expect PASS** — `.venv/Scripts/python -m pytest tests/test_rom.py tests/test_reference.py -v`.

---

### Task 4: Controller core + headless equivalence

**Files:**
- Create: `hw/traffic_controller.py`, `verify/logisim_run.py`
- Test: `tests/test_equivalence.py`

**Interfaces:**
- Consumes: `Circuit`, `project_xml` (Task 2); `logisim_contents`, `Row`, `run_reference` (Task 3).
- Produces:
  - `add_core(c: Circuit, rom: list[int], origin: tuple[int, int]) -> None` — consumes tunnels `clk`, `dNS`(2), `dEW`(2); produces tunnels `S1`, `S0`, `T`(4), `NS_R`, `NS_Y`, `NS_G`, `EW_R`, `EW_Y`, `EW_G`
  - `build_test_circuit(rom: list[int], density_ns: int, density_ew: int, ticks: int) -> str` — project XML; Constants for densities; 8-bit tick counter (max = `ticks`) on `clk`, output pins `tick`, `S1`, `S0`, `T`, six lights, and `halt` = tick-counter carry
  - `verify/logisim_run.py`: `JAR = Path(os.environ.get("LOGISIM_JAR", "tools/logisim-generic-2.7.1.jar"))`; `logisim_available() -> bool`; `run_logisim(circ_xml: str, timeout_s: float = 60) -> list[Row]` (writes temp file, runs `-tty table`, parses using column order from notes, dedups to one Row per tick, `state = 2*S1 + S0`)

Core contents (signal names are tunnel labels; students will read these):
- `D Flip-Flop` ×2 on `clk`: `S1_next → S1`, `S0_next → S0`
- next state: `XOR(S0, done) → S0_next`; `AND(S0, done) → c1`; `XOR(S1, c1) → S1_next`
- `Splitter` T → `T1, T2, T3`; `NOR(T1, T2, T3) → done`; `NOT(done) → count_en`
- `Counter` 4-bit: data `load_val`, load = Constant 1, count `count_en`, clk `clk`, out `T` (or Task 1 fallback)
- `Splitter` (`dEW` bits 0-1, `dNS` bits 2-3) → `addr`; `ROM` 4×8 (contents from `logisim_contents(rom)`, sel = Constant 1 if notes require) → `rom_out`; `Splitter` → `gEW` (0-3), `gNS` (4-7)
- `Multiplexer` sel `S1`: in0 `gEW`, in1 `gNS` → `g_next`; `Multiplexer` sel `S0`: in0 Constant 2 (4-bit), in1 `g_next` → `load_val`
- lights: `NOT S1 → nS1`, `NOT S0 → nS0`; `AND(nS1,nS0) → NS_G`; `AND(nS1,S0) → NS_Y`; `Buffer(S1) → NS_R`; `AND(S1,nS0) → EW_G`; `AND(S1,S0) → EW_Y`; `Buffer(nS1) → EW_R`
- Lay out left→right in columns: state register, next-state logic, timer, ROM path, light decode; `Text` heading above each column.

- [ ] **Step 1: failing tests**

```python
pytestmark = pytest.mark.logisim

ROM_MIXED = encode_rom({**uniform_policy(5, 3), (3, 1): (9, 7), (0, 2): (2, 15), (2, 2): (15, 15)})

@pytest.mark.parametrize("dens", [(0, 0), (3, 1), (0, 2), (2, 2)])
def test_circuit_matches_reference(dens):
    hw = run_logisim(build_test_circuit(ROM_MIXED, *dens, ticks=120))
    ref = run_reference(ROM_MIXED, dens, 120)
    assert hw == ref

def test_lights_one_hot_per_road():
    for r in run_logisim(build_test_circuit(ROM_MIXED, 3, 1, ticks=60)):
        assert sum(r.lights[:3]) == 1 and sum(r.lights[3:]) == 1
```

- [ ] **Step 2: run, expect FAIL.**
- [ ] **Step 3: implement `verify/logisim_run.py`, then `hw/traffic_controller.py`.**
- [ ] **Step 4: run, expect PASS** — `.venv/Scripts/python -m pytest tests/test_equivalence.py -v`. On mismatch, diff the first differing Row and check that component's offsets in the notes before changing logic.

---

### Task 5: Demo circuit variant

**Files:**
- Modify: `hw/traffic_controller.py` (add demo builder)
- Test: `tests/test_demo_circuit.py`

**Interfaces:**
- Produces: `build_demo_circuit(rom: list[int]) -> str` — calls `add_core`; adds `Clock`; input Pins width 2 labelled `Traffic NS` → `dNS`, `Traffic EW` → `dEW`; six LEDs (colours red `#ff0000`, yellow `#ffcc00`, green `#00cc00`) arranged as two signal heads with labels; `Hex Digit Display` on `T` labelled "seconds left"; `Text` title "P6 Adaptive Traffic Signal Controller" and a one-line instruction ("Set traffic levels 0-3, then Simulate > Ticks Enabled").

- [ ] **Step 1: failing tests**

```python
def test_demo_only_builtin_libs_and_2_7_1():
    root = ET.fromstring(build_demo_circuit(encode_rom(uniform_policy(5, 3))))
    assert root.get("source") == "2.7.1"
    assert all(l.get("desc").startswith("#") for l in root.findall("lib"))

def test_demo_has_controls_and_lights():
    root = ET.fromstring(build_demo_circuit(encode_rom(uniform_policy(5, 3))))
    labels = {a.get("val") for a in root.iter("a") if a.get("name") == "label"}
    assert {"Traffic NS", "Traffic EW"} <= labels
    assert sum(1 for e in root.iter("comp") if e.get("name") == "LED") == 6

@pytest.mark.logisim
def test_demo_loads_without_error():
    # no halt pin: run with short timeout, kill, assert stderr has no exception / "error"
```

- [ ] **Step 2: run, expect FAIL.** **Step 3: implement.** **Step 4: run, expect PASS.**

---

### Task 6: Traffic simulator

**Files:**
- Create: `ai/__init__.py`, `ai/traffic.py`
- Test: `tests/test_traffic.py`

**Interfaces:**
- Consumes: `YELLOW` from `hw/rom.py`.
- Produces: `ARRIVAL_RATE = (0.05, 0.15, 0.30, 0.45)` (cars/s per level); `DISCHARGE_PER_S = 1`; `@dataclass SimResult(avg_wait: float, avg_queue: float, arrived: int, served: int)`; `simulate(green_ns: int, green_ew: int, density_ns: int, density_ew: int, seconds: int = 1800, seed: int = 0) -> SimResult`

Model: 1 s steps; each road gets a Bernoulli(p = rate) arrival per second (numpy `default_rng(seed)`, arrivals pre-drawn as arrays); phase cycle NS green `green_ns` s → yellow `YELLOW` → EW green `green_ew` → yellow; during a road's green, `min(queue, DISCHARGE_PER_S)` cars leave; `avg_queue` = mean over seconds of `qNS + qEW`; `avg_wait` = total queue-seconds / arrived (0.0 if arrived == 0).

- [ ] **Step 1: failing tests**

```python
def test_deterministic():
    assert simulate(7, 7, 2, 1, seed=4) == simulate(7, 7, 2, 1, seed=4)

def test_zero_traffic_no_crash():
    r = simulate(9, 9, 0, 0, seconds=30, seed=0)
    assert r.avg_wait >= 0.0 and math.isfinite(r.avg_wait)

def test_no_arrivals_gives_zero_wait(monkeypatch):
    monkeypatch.setattr(traffic, "ARRIVAL_RATE", (0.0, 0.0, 0.0, 0.0))
    assert simulate(9, 9, 0, 0).avg_wait == 0.0

def test_longer_green_helps_busy_road():
    assert simulate(13, 3, 3, 0, seed=1).avg_wait < simulate(3, 13, 3, 0, seed=1).avg_wait

def test_saturated_finite():
    r = simulate(15, 15, 3, 3, seconds=3600)
    assert math.isfinite(r.avg_wait) and r.served <= r.arrived
```

- [ ] **Step 2: run, expect FAIL.** **Step 3: implement.** **Step 4: run, expect PASS.**

---

### Task 7: Q-learning agent

**Files:**
- Create: `ai/agent.py`
- Test: `tests/test_agent.py`

**Interfaces:**
- Consumes: `simulate`, `SimResult` (Task 6); `Policy` (Task 3).
- Produces: `G_CHOICES = (3, 5, 7, 9, 11, 13, 15)`; `ACTIONS: list[tuple[int, int]]` (49 pairs); `FIXED_GREEN = (9, 9)`; `@dataclass TrainResult(policy: Policy, q: np.ndarray  # shape (16, 49), curve: list[float]  # mean reward per 500-episode window)`; `train(episodes=20000, episode_seconds=900, alpha=0.1, eps_start=1.0, eps_end=0.05, seed=0) -> TrainResult`; `fixed_policy() -> Policy`; `evaluate(policy: Policy, seconds=1800, seed=123) -> dict[tuple[int, int], SimResult]`

Algorithm: tabular Q-learning in its one-step form (each episode = one traffic state, so the update is `Q[s,a] += alpha * (r - Q[s,a])`); state `s = (dNS<<2)|dEW` drawn uniformly each episode; ε-greedy with ε decaying linearly `eps_start → eps_end`; reward `r = -simulate(gNS, gEW, dNS, dEW, episode_seconds, seed=episode_seed).avg_wait`; Q initialised to 0; policy = argmax per state. The docstring states plainly that this is the γ=0 (contextual bandit) case of Q-learning, so the report can say so honestly.

- [ ] **Step 1: failing tests**

```python
@pytest.fixture(scope="module")
def trained():
    return train(episodes=8000, episode_seconds=600, seed=0)

def test_policy_complete_and_valid(trained):
    assert set(trained.policy) == {(a, b) for a in range(4) for b in range(4)}
    assert all(g in G_CHOICES for pair in trained.policy.values() for g in pair)

def test_favours_busy_road(trained):
    ns, ew = trained.policy[(3, 0)]; assert ns > ew
    ns, ew = trained.policy[(0, 3)]; assert ew > ns

def test_more_green_when_saturated(trained):
    assert sum(trained.policy[(3, 3)]) > sum(trained.policy[(0, 0)])

def test_beats_fixed_timer(trained):
    ai, fx = evaluate(trained.policy), evaluate(fixed_policy())
    mean = lambda d: sum(r.avg_wait for r in d.values()) / len(d)
    assert mean(ai) < 0.9 * mean(fx)

def test_deterministic():
    assert train(episodes=300, episode_seconds=120, seed=5).policy == train(episodes=300, episode_seconds=120, seed=5).policy
```

- [ ] **Step 2: run, expect FAIL.** **Step 3: implement.** **Step 4: run, expect PASS** (mark the module `slow`; target < 60 s).

---

### Task 8: Pipeline, report outputs, docs

**Files:**
- Create: `ai/report.py`, `make_all.py`, `docs/state-diagram.md`, `README.md`
- Generated: `logisim/traffic_controller.circ`, `results/policy.json`, `results/timing_rom.txt`, `results/rom_table.csv`, `results/comparison.csv`, `results/comparison.png`, `results/learning_curve.png`
- Test: `tests/test_pipeline.py`

**Interfaces:**
- Consumes: everything above.
- Produces: `ai/report.py`: `comparison_chart(ai: dict, fixed: dict, path: Path)` (grouped bars of avg wait, 16 density states, AI vs fixed), `learning_curve(curve: list[float], path: Path)`, `rom_table_csv(policy: Policy, path: Path)` (columns `address, dNS, dEW, gNS, gEW, hex`), `comparison_csv(ai, fixed, path)` (columns `dNS, dEW, ai_wait, fixed_wait, ai_queue, fixed_queue`); `make_all.py`: `main(episodes: int = 20000, out_dir: Path = Path("."))` and CLI `--episodes`.

- [ ] **Step 1: failing tests**

```python
def test_pipeline_writes_everything(tmp_path):
    main(episodes=400, out_dir=tmp_path)
    for f in ["logisim/traffic_controller.circ", "results/timing_rom.txt", "results/rom_table.csv",
              "results/comparison.csv", "results/comparison.png", "results/learning_curve.png", "results/policy.json"]:
        assert (tmp_path / f).stat().st_size > 0

def test_circ_rom_matches_policy(tmp_path):
    main(episodes=400, out_dir=tmp_path)
    policy = load_policy(tmp_path / "results/policy.json")
    assert logisim_contents(encode_rom(policy)) in (tmp_path / "logisim/traffic_controller.circ").read_text()

def test_reproducible(tmp_path):
    main(episodes=400, out_dir=tmp_path / "a"); main(episodes=400, out_dir=tmp_path / "b")
    assert (tmp_path / "a/results/policy.json").read_text() == (tmp_path / "b/results/policy.json").read_text()
```

- [ ] **Step 2: run, expect FAIL.**
- [ ] **Step 3: implement `ai/report.py` (load `dataviz` skill first) and `make_all.py`.**
- [ ] **Step 4: run, expect PASS.**
- [ ] **Step 5: full run** — `.venv/Scripts/python make_all.py` then `.venv/Scripts/python -m pytest -v`. Expected: all pass; console prints AI vs fixed mean wait and the % reduction.
- [ ] **Step 6: docs** — `docs/state-diagram.md`: mermaid state diagram, state table (code, lights, duration source), next-state equations (`S0' = S0 ⊕ done`, `S1' = S1 ⊕ (S0·done)`, `done = ¬(T3+T2+T1)`), output equations, ROM layout, and the generated ROM table. `README.md`: what P6 is, folder map, setup (venv + `pip install -r requirements.txt`), `python make_all.py`, how to demo in Logisim (open `logisim/traffic_controller.circ`, set Traffic NS/EW with the poke tool, Simulate → Ticks Enabled, watch green times change), how to run verification, note that it opens in Logisim 2.7.1 and Logisim-evolution (open once in evolution to confirm before the demo).
