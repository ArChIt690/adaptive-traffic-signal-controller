# Logisim notes: 2.7.1 (spike findings) and Logisim-evolution (verified)

Jar: `tools/logisim-generic-2.7.1.jar` (SourceForge project `circuit`, path `2.7.x/2.7.1/`)
SHA-256 `362a78c12ad18c203fed868872c4a01cd9c12141379d92e892bbe2c37e627bc2`.
The jar ships its Java sources under `src/`; facts below come from those sources plus
`tools/PortDump.java` (port offsets) and `tools/spike.circ` (behaviour, run headless).

## Port offsets (relative to the component's `loc`, default facing east)

| Factory (lib index) | Attributes used | Port → offset |
|---|---|---|
| Pin (0) | any width; output true or false | the single port is at `(0,0)` |
| Constant (0) | `width`, `value` (e.g. `0x2`) | out `(0,0)` |
| Tunnel (0) | `width`, `label` | `(0,0)` |
| Clock (0) | — | out `(0,0)` |
| Splitter (0), fanout 2 | `incoming`, `bitN` = end index | combined `(0,0)`; end0 `(20,-20)`; end1 `(20,-10)` |
| Splitter (0), fanout 4 | `incoming` 4 | combined `(0,0)`; end0..3 `(20,-40)`,`(20,-30)`,`(20,-20)`,`(20,-10)` |
| NOT Gate (1) | — | out `(0,0)`; in `(-30,0)` |
| Buffer (1) | — | out `(0,0)`; in `(-20,0)` |
| AND Gate (1) | `inputs` 2, `size` 50 | out `(0,0)`; in0 `(-50,-20)`; in1 `(-50,20)` |
| XOR Gate (1) | `inputs` 2, `size` 50 | out `(0,0)`; in0 `(-60,-20)`; in1 `(-60,20)` |
| NOR Gate (1) | `inputs` 3, `size` 50 | out `(0,0)`; in0 `(-60,-20)`; in1 `(-60,0)`; in2 `(-60,20)` |
| D Flip-Flop (4) | — | **D `(-40,20)`**; **clk `(-40,0)`**; Q `(0,0)`; nQ `(0,20)`; reset `(-10,30)`; preset `(-30,30)`; enable `(-20,30)` |
| Counter (4) | `width`, `max` | out `(0,0)`; data `(-30,0)`; clk `(-20,20)`; clear `(-10,20)`; load `(-30,-10)`; count `(-30,10)`; carry `(0,10)` |
| Register (4) | `width` 4 | out `(0,0)`; in `(-30,0)`; clk `(-20,20)`; clear `(-10,20)`; enable `(-30,10)` |
| Subtractor (3) | `width` 4 | A `(-40,-10)`; B `(-40,10)`; out `(0,0)`; borrow-in `(-20,-20)`; borrow-out `(-20,20)` |
| ROM (4) | `addrWidth` 4, `dataWidth` 8 | data out `(0,0)`; addr `(-140,0)`; sel `(-90,40)` |
| Multiplexer (2) | `select` 1, `width` 4 | in0 `(-30,-10)`; in1 `(-30,10)`; sel `(-20,20)`; out `(0,0)` |
| LED (5) | — | in `(0,0)` (body extends to the right) |
| Hex Digit Display (5) | — | value in `(0,0)`; decimal point `(10,0)` (body above) |

Splitter end 0 carries the lowest bits when `bit0..bit3 = 0`, `bit4..bit7 = 1` (verified:
an 8-bit value split this way puts bits 0-3 on end0).

Bounding boxes (for spacing): AND/XOR/NOR 50-60 wide × 50 tall; ROM 140 × 80; counter 30 × 40.

## Behaviour

- **Counter** (`Counter.java` propagate): on a rising clock edge
  - load=0, count=1 → +1;  load=1, count=0 → loads data;  load=1, count=1 → **−1**;  both 0 → hold.
  - `carry` = 1 when the new value equals `max` (counting up) or 0 (counting down).
  - Verified headless: load 9, then 8.
- **ROM**: `sel` unconnected counts as selected (`!= FALSE`). Contents must be the
  **text of the element** `<a name="contents">addr/data: 4 8\n10 21 ...\n</a>`; putting it in
  `val="..."` loses the newlines and the ROM reads as all zeros.
- **Tunnels** placed exactly on a port location connect to it (verified).
- **Clock**: tick 1 drives it high, so the first rising edge is on the first simulation tick.

## Headless table mode (`java -jar tools/logisim-generic-2.7.1.jar FILE -tty table`)

- Columns = every *output* pin except `halt`, ordered **top-to-bottom by y, then left-to-right
  by x** (`Analyze.getPinLabels`). Columns are tab-separated; no header row.
- Value format: 1-bit `0`/`1`/`x`/`E`; multi-bit is binary MSB-first with a space every
  4 bits from the LSB end (e.g. 8-bit `0000 0101`). Strip spaces before `int(s, 2)`.
- The initial state (before any tick) prints as the first row; after that a row prints
  only when some output changed. With a tick counter on the outputs there is exactly one
  row per rising edge.
- An output pin labelled `halt` stops the run once it reads 1; that row is still printed.
  Exit code 0 on halt, 1 on oscillation. With no `halt` pin and a clock, it runs forever.

## Logisim-evolution (verified in 3.8.0 and 5.0.0)

Installs used: `tools/evolution-3.8.0/logisim-evolution-3.8.0-all.jar` (GitHub release, run with
JDK 17; SHA-256 `4c59be7d…6c2c`, the release publishes no checksum) and
`tools/evolution-5.0.0/extracted/` (the `windows-amd64.zip`, SHA-256 matched the release's
`59f11c42…7e83427`; it bundles Java 21+). 3.9.0 and later need Java 21.
Port positions come from `tools/PortDumpEvo.java` (same as `PortDump.java`, with evolution's
renamed library classes) and from evolution's sources for 3.8.0 / 4.0.0 / 5.0.0.

**Port layout.** Same as 2.7.1 for every part used here, except:

| Part | Evolution | 2.7.1 |
|---|---|---|
| ROM (classic appearance too) | `loc` is the **top-left corner**; addr `(0,10)`, data `(240,60)`; body 240 × 140; no select pin | addr `(-140,0)`, data `(0,0)`, sel `(-90,40)` |
| Hex Digit Display | decimal point `(20,0)` | `(10,0)` |
| D Flip-Flop | no enable pin | enable `(-20,30)` |
| Counter | an extra input at `(-20,-20)` | — |

Evolution's file loader does not move old ROMs, so a ROM placed for 2.7.1 is left unconnected
(the timer read `UUUU`, then `EEEE`). The generator therefore has a `target`:
`hw/geometry.py` keeps both layouts and `Circuit.place("ROM", "data", (x, y))` puts the data
pin on the same spot in either. Everything else is shared.

**Behaviour.**
- Counter: load has priority over count, so the 2.7.1 count-down trick doesn't work. The timer
  is a Register + Subtractor + MUX; the test harness's tick counter only counts up.
- `-tty table` with a `halt` pin prints exactly 2.7.1's format, so `verify/logisim_run.py`
  parses both. `-tty stats` works too. The packaged 5.0.0 `logisim-evolution.exe` accepts the
  same arguments; it starts a second `logisim-evolution` process for the window.

**Opening the file** (each of these is a pop-up in the GUI, logged by `OptionPane` headless):
- `source="2.7.1"` → "Old file format -- compatibility mode" warning. Evolution files say
  `source="3.8.0"` (the oldest evolution tested), and the warning is gone.
- Every part that has an `appearance` attribute but none in the file gets the *evolution*
  look, whatever the file's version, so the stateful parts carry `appearance="classic"`.
- A label equal to the part's own name ("clock" on a Clock) is removed, with a message.
- Labels must be valid HDL names (`SyntaxChecker`: a letter first, then letters, digits or
  `_`; no `__`, no trailing `_`, no VHDL/Verilog keyword), or they are renamed:
  "Traffic NS" became `Traffic_NS_498072b2`.
- Default label font is SansSerif **bold 16** (2.7.1: plain 12). Every tunnel, label and
  text gets `SansSerif plain 12` written explicitly, so both versions draw the same sizes.

**Menus:** *Simulate → Auto-Tick Enabled / Auto-Tick Frequency / Reset Simulation*;
ROM → right-click → *Edit Contents*.
