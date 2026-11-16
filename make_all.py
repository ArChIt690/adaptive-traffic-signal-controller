"""Train the AI agent, write its timings into the Logisim circuit, and make the report outputs.

Usage:  python make_all.py [--episodes 20000] [--target evolution|2.7.1]
"""
import argparse
import json
from pathlib import Path

from ai.agent import CURVE_WINDOW, best_fixed_policy, evaluate, fixed_policy, train
from ai.report import comparison_chart, comparison_csv, learning_curve, rom_table_csv
from hw.geometry import DEFAULT_TARGET, TARGETS
from hw.rom import Policy, encode_rom, raw_image
from hw.traffic_controller import build_demo_circuit


def save_policy(policy: Policy, path: Path) -> None:
    path.write_text(json.dumps({f"{a},{b}": list(g) for (a, b), g in sorted(policy.items())}, indent=1))


def load_policy(path: Path) -> Policy:
    raw = json.loads(Path(path).read_text())
    return {tuple(map(int, k.split(","))): tuple(v) for k, v in raw.items()}


def main(episodes: int = 20000, out_dir: Path = Path("."), target: str = DEFAULT_TARGET) -> dict:
    out_dir = Path(out_dir)
    results, circ_dir = out_dir / "results", out_dir / "logisim"
    results.mkdir(parents=True, exist_ok=True)
    circ_dir.mkdir(parents=True, exist_ok=True)

    trained = train(episodes=episodes, seed=0)
    rom = encode_rom(trained.policy)
    best_fixed = best_fixed_policy()
    g_fixed = best_fixed[(0, 0)][0]
    ai, fixed = evaluate(trained.policy), evaluate(best_fixed)
    nine = evaluate(fixed_policy())  # the 9 s / 9 s timer, for context in the README

    save_policy(trained.policy, results / "policy.json")
    (results / "timing_rom.txt").write_text(raw_image(rom))
    rom_table_csv(trained.policy, results / "rom_table.csv")
    comparison_csv(ai, fixed, results / "comparison.csv")
    fixed_label = f"Best fixed timer ({g_fixed} s / {g_fixed} s)"
    comparison_chart(ai, fixed, results / "comparison.png", fixed_label)
    mean = lambda d: sum(r.avg_wait for r in d.values()) / len(d)  # noqa: E731
    fixed_mean, ai_mean, nine_mean = mean(fixed), mean(ai), mean(nine)
    learning_curve(trained.curve, results / "learning_curve.png", CURVE_WINDOW,
                   fixed_wait=fixed_mean, fixed_label=fixed_label.lower())
    (circ_dir / "traffic_controller.circ").write_text(build_demo_circuit(rom, target), encoding="utf-8")

    summary = {"episodes": episodes, "fixed_green": g_fixed, "fixed_mean_wait": fixed_mean,
               "ai_mean_wait": ai_mean, "reduction_pct": 100 * (1 - ai_mean / fixed_mean),
               "nine_nine_mean_wait": nine_mean}
    print(f"Best fixed timer ({g_fixed}/{g_fixed}): {fixed_mean:.1f} s average wait | AI: {ai_mean:.1f} s "
          f"| {summary['reduction_pct']:.0f}% less waiting   (9/9 timer: {nine_mean:.1f} s)")
    print(f"Circuit for Logisim {target} written to {circ_dir / 'traffic_controller.circ'}")
    return summary


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--episodes", type=int, default=20000)
    p.add_argument("--target", choices=TARGETS, default=DEFAULT_TARGET,
                   help="which Logisim the circuit is laid out for (the ROM's pins differ)")
    args = p.parse_args()
    main(args.episodes, target=args.target)
