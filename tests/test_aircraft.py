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
