# P6 — Adaptive Traffic Signal Controller: Design

Date: 2026-11-16
Course: ESC392 Digital Electronics — AI-Assisted / Agentic-AI project list, P6 (CO2, CO3)

## Intent

Build the P6 project: "Digital FSM handles base sequencing; an AI agent overrides
timing based on real/simulated traffic density." The team does its digital lab in
Logisim, so the hardware must be a Logisim circuit the instructor can open, run and
grade. Logisim cannot run an AI program, so the AI lives in Python and its decisions
are handed to the circuit through a ROM. The demo shows (1) the circuit adapting its
green times to traffic, and (2) evidence that the AI-chosen timings beat a fixed timer.

## Goals

- A working Logisim circuit: FSM sequencing a two-road junction, timer, density
  inputs, and a timing ROM that the AI fills.
- A Python traffic simulator and an AI agent that learns the green time for each
  traffic situation.
- An export step that writes the agent's decisions as a Logisim ROM image.
- Evidence for the report: fixed-vs-AI comparison (average wait, queue length),
  FSM state diagram, state table, ROM contents table.
- Verification that the circuit and a Python reference model behave identically.

## Non-goals

- Real hardware (FPGA/Arduino), real cameras or sensors.
- Pedestrian crossings, emergency-vehicle priority, turn arrows, more than two roads.
- A live link between Python and Logisim while the circuit runs.
- Writing the final report document (separate request once the build is done).
- An animated traffic visualisation (optional extra only if time allows).

## Anti-goals

- An "AI" that is just hard-coded if/else rules in Python dressed up as an agent.
- A circuit that only works in one Logisim version or needs plugins/libraries.
- Logic that can't be explained by a student at the demo (no opaque mega-circuits).

## Constraints

- Logisim file format: Logisim 2.7.1 `.circ` (opens in 2.7.1 and Logisim-evolution).
  Built-in components only.
- Python 3.11, dependencies limited to numpy and matplotlib.
- Machine has Java 8 → Logisim 2.7.1 jar used headless (`-tty table`) for testing.

## Approaches considered

| Approach | Trade-off | Decision |
|---|---|---|
| A. Logisim only, "AI" as comparator + MUX rules | All in the lab tool, but the "agent" is fixed rules — weak on the AI half | Rejected |
| B. Python only, simulation + agent | Clearly AI, but drops the digital-electronics core being graded | Rejected |
| **C. Logisim hardware + Python AI agent, linked by ROM** | Two parts to build; the link is offline (file load) not live | **Chosen by the team** |

## Design

### Hardware (Logisim)

Two roads: **NS** (north–south) and **EW** (east–west), each with red/yellow/green LEDs.

**FSM** — 4 states in a 2-bit state register (D flip-flops), next-state logic from gates:

| State | Code | NS | EW | Leaves when |
|---|---|---|---|---|
| NS_GREEN  | 00 | G | R | timer reaches 0 |
| NS_YELLOW | 01 | Y | R | timer reaches 0 |
| EW_GREEN  | 10 | R | G | timer reaches 0 |
| EW_YELLOW | 11 | R | Y | timer reaches 0 |

Output (light) logic is combinational from the state bits — a Moore machine.

**Timer** — 4-bit counter. On entering a state it loads that state's duration and
counts down; "timer = 0" drives the FSM to the next state. 1 clock tick = 1 second.

**Durations**
- Yellow: fixed 2 s (constant).
- Green: from the **timing ROM**. Address = `{densityNS[1:0], densityEW[1:0]}`
  (16 entries). Data = 8 bits = `{greenNS[3:0], greenEW[3:0]}`, each 2–15 s.
  A MUX picks greenNS or greenEW depending on which green state is being entered.

**Density inputs** — each road has a 2-bit density level (0 = empty … 3 = jammed),
set with a DIP switch acting as the simulated traffic sensor. Densities are read
at the moment a green phase is loaded, so changing them mid-phase affects the next cycle.

**Display** — hex digit display showing seconds remaining; state shown via LEDs.

**Override behaviour** — the FSM alone always cycles G→Y→G→Y (the "base sequencing").
The AI does not change the sequence, only how long each green lasts — that is the
"override" in the P6 summary.

### AI (Python)

**Traffic simulator** — discrete time, 1 s steps, two queues. Cars arrive per road
at a rate set by that road's density level. During a road's green, cars leave at a
fixed discharge rate; yellow and red discharge nothing. Measures average wait per car
and average queue length.

**Agent** — tabular Q-learning. State = (densityNS, densityEW), 16 states.
Action = a (greenNS, greenEW) pair from the allowed range. Reward = negative total
waiting over a simulated cycle. After training, the best action per state is the
learned timing policy.

**Baseline** — fixed timer with equal green on both roads, same yellow.

**Export** — writes the policy as a Logisim ROM image (`v2.0 raw` hex format) and
places it into the ROM contents of the `.circ` file, so the circuit opens ready to run.

**Report outputs** — comparison chart (fixed vs AI, per density pattern), learning
curve, ROM table (address → green times, with density meaning), saved as PNG/CSV.

### Verification

- A Python reference model of the FSM + timer + ROM, cycle-accurate.
- Run the Logisim circuit headless for N ticks across density settings; compare its
  light outputs tick-by-tick with the reference model. Must match exactly.
- Unit tests for the simulator, agent export format, and reference model.

### Repository layout

```
DE_Assignment/
  logisim/      traffic_controller.circ
  ai/           simulator, agent, training, ROM export
  verify/       reference model + Logisim comparison
  results/      charts, tables, ROM image
  docs/         this design, state diagram, build notes
  README.md     how to run the demo
```

## Calls made by Claude (open to correction)

- Logisim 2.7.1 format, so it opens in either version.
- Two-road junction (not four separate roads).
- Density = 2-bit level set by DIP switch, rather than counting button presses.
- Green 2–15 s (4-bit), yellow fixed 2 s, 1 tick = 1 s.
- Q-learning chosen for the agent: simple to explain and genuinely learns.
- Python ↔ Logisim link is a ROM file loaded before running, not live.

## Left to the builder

- Circuit layout and wire placement inside Logisim.
- Exact arrival/discharge rates per density level in the simulator.
- Q-learning hyperparameters and the action set granularity.
- Chart styling.
