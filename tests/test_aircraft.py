import pytest
from crujisim.lib.Aircraft import Aircraft
from datetime import datetime, timedelta

# Fixtures


@pytest.fixture
def aircraft(gta):
    eto = datetime.today()
    a = Aircraft("test_callsign", "A320", "LEMD", "LECE",
                 320., 340., "BELEN,NORTA",
                 next_wp="NORTA", next_wp_eto=eto, wake_hint="M")
    return a

# Tests


def test_init(gta):
    # a = Aircraft.Aircraft(callsign, type, adep, ades,
    #                       float(cfl), float(rfl), route,
    #                       next_wp=ef.fix, next_wp_eto=eto,
    #                       wake_hint=ef.wtc)

    eto = datetime.today()
    Aircraft("test_callsign", "A320", "LEMD", "LECE",
             320., 340., "BELEN,NORTA",
             next_wp="NORTA", next_wp_eto=eto, wake_hint="M")


def test_int_ils(aircraft):
    aircraft.int_ils()
    d = timedelta(seconds=5)
    aircraft.next(aircraft.t + d)
    assert aircraft.app_auth is True
    assert aircraft.to_do == "app"


@pytest.mark.parametrize("cfl,expected", [
    (0, True),
    (100, True),
    (1000, False)])
def test_set_cfl(flight, cfl, expected):
    result, max_flightlevel = flight.set_cfl(cfl)
    assert result == expected
    if result:
        assert flight.cfl == cfl


def test_set_heading(flight):
    flight.set_heading(185)
    assert flight.tgt_hdg == 185


def test_set_heading_right(gta, flight):
    flight.set_heading(100)
    flight.hdg = 100
    gta.timer()
    flight.set_heading(95, 'DCHA')
    hdg_0 = flight.hdg
    gta.t += timedelta(seconds=5)
    gta.timer()
    hdg_1 = flight.hdg
    assert hdg_1 > hdg_0


def test_set_heading_left(gta, flight):
    flight.set_heading(100)
    gta.timer()
    flight.set_heading(200, 'IZDA')
    hdg_0 = flight.hdg
    gta.t += timedelta(seconds=5)
    gta.timer()
    hdg_1 = flight.hdg
    assert hdg_1 < hdg_0


@pytest.mark.parametrize("ias,expected", [
    (0, True),
    (100, True),
    (1000, False)])
def test_set_ias(flight, ias, expected):
    result, max_flightlevel = flight.set_ias(ias)
    assert result == expected
    if result:
        assert flight.tgt_ias == ias


def test_set_std_spd(flight):
    flight.set_std_spd()
