import pytest
from crujisim.lib.Aircraft import Aircraft, FPM_TO_LEVELS_PER_HOUR, LANDED
from datetime import datetime, timedelta


# Fixtures


@pytest.fixture
def aircraft(gta):
    eto = datetime.today()
    a = Aircraft("test_callsign", "A320", "LEMD", "LECE",
                 320., 340., "BELEN,NORTA",
                 next_wp="NORTA", next_wp_eto=eto, wake_hint="M")
    return a


@pytest.fixture
def td_1m():
    return timedelta(seconds=60)

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


@pytest.mark.parametrize("start_hdg, end_hdg, dir, expected", [
    (350, 10, 'IZDA', True),
    (10, 350, 'DCHA', False)])
def test_set_heading(flight, td_1m, start_hdg, end_hdg, dir, expected):
    flight.hdg = 360
    flight.set_heading(start_hdg)
    flight.next(flight.t + td_1m)
    assert flight.hdg == start_hdg

    flight.set_heading(end_hdg, dir)
    hdg_0 = flight.hdg
    flight.next(flight.t + td_1m)
    hdg_1 = flight.hdg
    assert (hdg_1 < hdg_0) == expected


def test_set_vertical_rate_climb(flight, td_1m):
    flight.lvl = 100
    flight.cfl = 200
    flight.set_vertical_rate(1000 * FPM_TO_LEVELS_PER_HOUR)
    assert flight.rocd == 600
    flight.next(flight.t + td_1m)
    assert flight.lvl == 110

    flight.lvl = 200
    flight.cfl = 100
    flight.set_vertical_rate(1000 * FPM_TO_LEVELS_PER_HOUR)
    assert flight.rocd == -600
    flight.next(flight.t + td_1m)
    assert flight.lvl == 190


@pytest.mark.parametrize("ias,expected", [
    (0, True),
    (100, True),
    (1000, False)])
def test_set_ias(flight, ias, expected):
    result, max_flightlevel = flight.set_ias(ias)
    assert result == expected
    if result:
        assert flight.tgt_ias == ias


def test_execute_app(gta, flight):
    flight.execute_app()
    assert flight.app_auth is True
    for i in range(250):
        gta.timer()
    assert flight.pof == LANDED


def test_set_std_spd(flight):
    flight.set_std_spd()


def test_target_hdg_after_ils(flight, td_1m):
    # Found this bug for a different aircraft. This position triggers the bug
    flight.pos = (150.54, 59.67)
    flight.set_heading(200)
    flight.next(flight.t + 2 * td_1m)
    assert flight.hdg == 200
    flight.int_ils()
    assert flight.get_target_heading(0, flight.t) == 200
