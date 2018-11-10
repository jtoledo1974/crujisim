import pytest


@pytest.fixture
def perf(gta):
    return gta.flights[0].perf


d1 = {0: 0., 10: 5.}
d2 = {0: 0., 1: 2., 3: 4, 5: -10, 6: 10, 10: 0}


@pytest.mark.parametrize("d, level, result", [
    (d1, -1, 0.),
    (d1, 5, 2.5),
    (d1, 0, 0.),
    (d1, 10, 5.),
    (d1, 11, 5.),
    (d2, 2, 3),
    (d2, 5.5, 0)
])
def test_interpolate(perf, d, level, result):
    assert perf.interpolate(d, level) == result
    # Do it twice when levels are cached
    assert perf.interpolate(d, level) == result
