import csv

import pytest

from hw.rom import encode_rom, logisim_contents
from make_all import load_policy, main

pytestmark = pytest.mark.slow

OUTPUTS = ["logisim/traffic_controller.circ", "results/timing_rom.txt", "results/rom_table.csv",
           "results/comparison.csv", "results/comparison.png", "results/learning_curve.png",
           "results/policy.json"]


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    out = tmp_path_factory.mktemp("run")
    main(episodes=400, out_dir=out)
    return out


def test_pipeline_writes_everything(run):
    for f in OUTPUTS:
        assert (run / f).stat().st_size > 0, f


def test_circ_rom_matches_policy(run):
    policy = load_policy(run / "results/policy.json")
    assert logisim_contents(encode_rom(policy)) in (run / "logisim/traffic_controller.circ").read_text()


def test_rom_table_has_16_rows(run):
    with open(run / "results/rom_table.csv", newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 16
    assert set(rows[0]) == {"address", "dNS", "dEW", "gNS", "gEW", "hex"}
    assert rows[13]["dNS"] == "3" and rows[13]["dEW"] == "1"


def test_comparison_csv_columns(run):
    with open(run / "results/comparison.csv", newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 16
    assert set(rows[0]) == {"dNS", "dEW", "ai_wait", "fixed_wait", "ai_queue", "fixed_queue"}


def test_reproducible(tmp_path):
    main(episodes=400, out_dir=tmp_path / "a")
    main(episodes=400, out_dir=tmp_path / "b")
    assert (tmp_path / "a/results/policy.json").read_text() == (tmp_path / "b/results/policy.json").read_text()


def test_baseline_is_best_fixed_timer(run):
    from ai.agent import best_fixed_policy, evaluate
    best = best_fixed_policy()
    expected = evaluate(best)
    with open(run / "results/comparison.csv", newline="") as f:
        rows = {(int(r["dNS"]), int(r["dEW"])): float(r["fixed_wait"]) for r in csv.DictReader(f)}
    assert all(abs(rows[s] - expected[s].avg_wait) < 0.01 for s in expected)


def test_demo_is_written_for_evolution_by_default(run):
    assert 'source="3.8.0"' in (run / "logisim/traffic_controller.circ").read_text()


def test_target_option_writes_a_2_7_1_circuit(tmp_path):
    main(episodes=50, out_dir=tmp_path, target="2.7.1")
    assert 'source="2.7.1"' in (tmp_path / "logisim/traffic_controller.circ").read_text()
