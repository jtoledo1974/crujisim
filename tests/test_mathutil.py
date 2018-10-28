import pytest
from crujisim.lib import MathUtil as MU

p1 = (0.1, 0.1)
p2 = (0, 0)
p3 = (1, 1)
poly1 = (0, 0), (0, 1), (1, 0)


@pytest.mark.parametrize("point,polygon,result", [
    (p1, poly1, True),
    (p2, poly1, True),
    (p3, poly1, False),
])
def test_point_within_poligon(point, polygon, result):
    assert MU.point_within_polygon(point, polygon) is result
