from hw.rom import encode_rom, uniform_policy
from verify.reference import run_reference


def test_reference_sequence_uniform_5_3():
    rows = run_reference(encode_rom(uniform_policy(5, 3)), (0, 0), 13)
    assert [(r.state, r.timer) for r in rows] == [
        (0, 0), (1, 2), (1, 1), (2, 3), (2, 2), (2, 1), (3, 2), (3, 1),
        (0, 5), (0, 4), (0, 3), (0, 2), (0, 1), (1, 2)]
    assert [r.tick for r in rows] == list(range(14))
    assert rows[8].lights == (0, 0, 1, 1, 0, 0)   # NS green, EW red
    assert rows[1].lights == (0, 1, 0, 1, 0, 0)   # NS yellow
    assert rows[3].lights == (1, 0, 0, 0, 0, 1)   # EW green
    assert rows[6].lights == (1, 0, 0, 0, 1, 0)   # EW yellow


def test_reference_uses_density_address():
    p = uniform_policy(5, 3)
    p[(3, 1)] = (9, 7)
    rows = run_reference(encode_rom(p), (3, 1), 20)
    # EW green 7 runs ticks 3-9, EW yellow ticks 10-11, NS green loads 9 at tick 12
    assert rows[3].timer == 7 and rows[12].timer == 9


def test_density_change_mid_green_only_affects_next_load():
    p = uniform_policy(5, 3)
    p[(2, 2)] = (12, 12)
    rows = run_reference(encode_rom(p), lambda t: (0, 0) if t < 10 else (2, 2), 30)
    assert [r.timer for r in rows[8:13]] == [5, 4, 3, 2, 1]   # NS green loaded at tick 7 with (0,0)
    assert any(r.timer == 12 for r in rows[13:])
