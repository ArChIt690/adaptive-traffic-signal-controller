import pytest

from hw.rom import decode_rom, encode_rom, logisim_contents, raw_image, uniform_policy


def test_encode_layout():
    p = uniform_policy(5, 3)
    p[(3, 1)] = (15, 2)
    rom = encode_rom(p)
    assert len(rom) == 16 and rom[0] == 0x53 and rom[13] == 0xF2
    assert decode_rom(rom) == p


@pytest.mark.parametrize("bad", [(0, 5), (1, 5), (5, 16)])
def test_encode_rejects_out_of_range(bad):
    p = uniform_policy(5, 3)
    p[(0, 0)] = bad
    with pytest.raises(ValueError):
        encode_rom(p)


def test_encode_rejects_missing_state():
    p = uniform_policy(5, 3)
    del p[(2, 1)]
    with pytest.raises(ValueError):
        encode_rom(p)


def test_raw_image_header():
    assert raw_image(encode_rom(uniform_policy(5, 3))).startswith("v2.0 raw\n")


def test_logisim_contents_format():
    s = logisim_contents(encode_rom(uniform_policy(5, 3)))
    assert s.startswith("addr/data: 4 8\n")
    assert s.split()[3:] == ["53"] * 16
