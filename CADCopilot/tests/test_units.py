import math

from cad_mcp import units


def test_length_to_cm():
    assert units.to_cm(20, "mm") == 2.0
    assert units.to_cm(1, "in") == 2.54
    assert units.to_cm(1, "cm") == 1.0
    assert round(units.to_cm(1, "ft"), 4) == 30.48


def test_length_round_trip():
    assert round(units.from_cm(units.to_cm(3.5, "in"), "in"), 6) == 3.5
    assert units.cm_to_mm(2.0) == 20.0
    assert units.mm_to_cm(20.0) == 2.0


def test_aliases_and_quotes():
    assert units.to_cm(1, "inches") == 2.54
    assert units.to_cm(1, '"') == 2.54
    assert units.to_cm(2, "millimeters") == 0.2


def test_angles():
    assert abs(units.deg_to_rad(180) - math.pi) < 1e-12
    assert abs(units.rad_to_deg(math.pi) - 180) < 1e-12


def test_unknown_unit_raises():
    try:
        units.to_cm(1, "furlong")
    except ValueError:
        return
    raise AssertionError("expected ValueError for unknown unit")
