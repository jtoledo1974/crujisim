from crujisim.lib.features import Point, HoldingPattern


def test_repr():
    p = Point('TERRA', (10, 10))
    assert str(p) == 'TERRA'
    assert repr(p) == "Point('TERRA', (10, 10))"

    h = HoldingPattern(p)
    assert str(h) == repr(h)
    assert repr(h) == "HoldingPattern(Point('TERRA', (10, 10)))"

    h = HoldingPattern(p, endTime=2, inboundCourse=200)
    assert repr(h) == "HoldingPattern(Point('TERRA', (10, 10)), inboundCourse=200, endTime=2)"
