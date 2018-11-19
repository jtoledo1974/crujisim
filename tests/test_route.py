import random
import pytest

import crujisim.lib.Route
from crujisim.lib.Route import Route, WayPoint, get_waypoints


class FIR(object):
    def get_point_coordinates(*arg):
        if arg[1] == 'PARLA':
            pos = (100, 200)  # Fixed position for equality tests
        else:
            pos = (random.random() * 100, random.random() * 100)
        return pos


@pytest.fixture
def fir():
    fir = FIR()
    crujisim.lib.Route.fir = fir


@pytest.fixture
def route(fir):
    wp_list = get_waypoints("pdt parla canes pi pi pi pi")
    return Route(wp_list)


def test_wp_list(fir):
    wp_list = get_waypoints("pdt parla canes pi pi pi pi")
    assert type(wp_list) is list


def test_route_to_str(route):
    r = route
    assert str(r) == "PDT, PARLA, CANES, PI, PI, PI, PI"


def test_substitute_after(route):
    r = route
    r.substitute_after("parla", get_waypoints("laks aldkfj slkjf"))
    assert str(r) == "PDT, PARLA, LAKS, ALDKFJ, SLKJF"


def test_substitute_before(route):
    r = route
    r.substitute_before("pdt", get_waypoints("x10.1y20 x10y0 tres"))
    assert str(r) == "X10.1Y20.0, X10.0Y0.0, TRES, PDT, PARLA, CANES, PI, PI, PI, PI"


def test_element_of_route_in_route(route):
    assert route[0] in route


def test_route_get_waypoint_index(route):
    assert route.index("parla") == route.index(route[1])


def test_route_get_inbd_track(route):
    r = route
    r.substitute_before("pdt", get_waypoints("x10.1y20 x10y0 tres"))
    assert r[0].pos() == (10.1, 20.0)
    assert r[1].pos() == (10.0, 0.0)
    assert r.get_inbd_track(0) == pytest.approx(180.28647)
    assert r.get_inbd_track(1) == pytest.approx(180.28647)
    assert r.get_outbd_track(0) == pytest.approx(180.28647)


def test_route_slice_type(route):
    assert type(route[2:4]) is Route


def test_route_element_type(route):
    assert type(route['pdt']) is WayPoint


def test_route_reduce(route):
    assert str(Route(get_waypoints("pdt parla X10Y10 X10Y10 papa")).reduce()) == 'PDT, PARLA, X10.0Y10.0, PAPA'


def test_route_other(route):
    r = route
    r = Route(get_waypoints("logro vtb ge pdt kaka"))
    r.substitute_after('pdt', get_waypoints('rbo dgo'))
    r.substitute_before('pdt', get_waypoints('crisa logro'))
    assert str(r) == "CRISA, LOGRO, PDT, RBO, DGO"


def test_wp_equality(fir):
    wp = WayPoint('PARLA')
    wp2 = wp.copy()
    wp3 = WayPoint('PARLA')
    assert wp.pos() == wp2.pos()
    assert wp == wp3
    assert wp == wp2


def test_element_in_route(route):
    assert "PI" in route
    assert "pi" in route
    wp = WayPoint('parla')
    assert wp in route
    with pytest.raises(TypeError):
        2 in route


def test_delete_from(route):
    with pytest.raises(ValueError):
        route.delete_from('PEPE')
    route.delete_from('PARLA')
    assert str(route) == "PDT"
