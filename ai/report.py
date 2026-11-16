"""Charts and tables for the project report."""
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from ai.traffic import SimResult  # noqa: E402
from hw.rom import Policy, encode_rom  # noqa: E402

AI_COLOUR, FIXED_COLOUR = "#2a78d6", "#eb6834"   # categorical slots 1-2, validated light mode
SURFACE, INK, INK_2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"

Results = dict[tuple[int, int], SimResult]


def _style(ax):
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=INK_2, labelsize=9)
    ax.yaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def _mean_wait(results: Results) -> float:
    return sum(r.avg_wait for r in results.values()) / len(results)


def comparison_chart(ai: Results, fixed: Results, path: Path, fixed_label: str = "Fixed timer") -> None:
    states = sorted(ai)
    x = range(len(states))
    w = 0.38
    fig, ax = plt.subplots(figsize=(10, 4.2), facecolor=SURFACE)
    _style(ax)
    # 2 px surface gap between the paired bars
    ax.bar([i - w / 2 for i in x], [fixed[s].avg_wait for s in states], w, color=FIXED_COLOUR,
           edgecolor=SURFACE, linewidth=2, label=fixed_label)
    ax.bar([i + w / 2 for i in x], [ai[s].avg_wait for s in states], w, color=AI_COLOUR,
           edgecolor=SURFACE, linewidth=2, label="AI timing ROM")
    ax.set_xticks(list(x), [f"{a}/{b}" for a, b in states])
    ax.set_xlabel("Traffic level  NS / EW  (0 = empty … 3 = jammed)", color=INK_2, fontsize=9)
    ax.set_ylabel("Average wait per car (s)", color=INK_2, fontsize=9)
    f, a = _mean_wait(fixed), _mean_wait(ai)
    ax.set_title(f"AI timing vs the best fixed timer: average wait {f:.1f} s → {a:.1f} s "
                 f"({100 * (1 - a / f):.0f}% less)", color=INK, fontsize=12, loc="left")
    top = max(max(r.avg_wait for r in fixed.values()), max(r.avg_wait for r in ai.values()))
    ax.set_ylim(0, top * 1.18)  # headroom so the legend row never sits on a bar
    ax.legend(frameon=False, fontsize=9, labelcolor=INK_2, loc="upper center", ncol=2)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=160, facecolor=SURFACE)
    plt.close(fig)


def learning_curve(curve: list[float], path: Path, window: int = 500, fixed_wait: float | None = None,
                   fixed_label: str = "fixed timer") -> None:
    fig, ax = plt.subplots(figsize=(7, 3.6), facecolor=SURFACE)
    _style(ax)
    xs = [(i + 1) * window for i in range(len(curve))]
    ax.plot(xs, [-r for r in curve], color=AI_COLOUR, linewidth=2)
    ax.plot(xs, [-r for r in curve], "o", color=AI_COLOUR, markersize=4, markeredgecolor=SURFACE)
    if fixed_wait is not None:
        ax.axhline(fixed_wait, color=INK_2, linewidth=1, linestyle=(0, (4, 3)))
        ax.annotate(fixed_label, (xs[-1], fixed_wait), textcoords="offset points", xytext=(0, 4),
                    ha="right", fontsize=8, color=INK_2)
    ax.set_ylim(bottom=0)
    ax.set_xlabel("Training episodes", color=INK_2, fontsize=9)
    ax.set_ylabel(f"Avg wait per car (s), mean of {window} episodes", color=INK_2, fontsize=9)
    ax.set_title("Q-learning: waits fall as the agent learns", color=INK, fontsize=12, loc="left")
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=160, facecolor=SURFACE)
    plt.close(fig)


def rom_table_csv(policy: Policy, path: Path) -> None:
    rom = encode_rom(policy)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["address", "dNS", "dEW", "gNS", "gEW", "hex"])
        for addr, byte in enumerate(rom):
            w.writerow([addr, addr >> 2, addr & 3, byte >> 4, byte & 0xF, f"{byte:02x}"])


def comparison_csv(ai: Results, fixed: Results, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["dNS", "dEW", "ai_wait", "fixed_wait", "ai_queue", "fixed_queue"])
        for s in sorted(ai):
            w.writerow([s[0], s[1], f"{ai[s].avg_wait:.2f}", f"{fixed[s].avg_wait:.2f}",
                        f"{ai[s].avg_queue:.2f}", f"{fixed[s].avg_queue:.2f}"])
