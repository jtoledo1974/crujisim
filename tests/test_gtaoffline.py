from crujisim.lib.GTAoffline import GTAoffline
from crujisim.lib.Aircraft import Aircraft
from crujisim.lib.GTAoffline import RIGHT, LEFT
import pytest

CALLSIGN = "jkk7148"
ADES = "LECE"
IAF = "TERRA"
# FIXTURES


@pytest.fixture
def gta_with_args(exc_file):
    def _gta(file="sample.exc", stop_after_minutes=15, step_callback=None):
        gta = GTAoffline(exc_file=str(exc_file), stop_after_minutes=15, step_callback=step_callback)
        return gta

    return _gta


@pytest.fixture
def gta(gta_with_args):
    gta = gta_with_args()
    return gta


@pytest.fixture
def flight(gta):
    f = gta.get_flight(CALLSIGN)
    return f


# TESTS

def test_full_run(gta):
    gta.start()


def test_gta_callback(gta_with_args):
    global called
    called = False

    def test_callback(gta):
        global called
        called = True
        gta.exit()

    gta = gta_with_args(step_callback=test_callback)
    gta.start()
    assert called is True


def test_find_flight(gta, flight):
    f = gta.get_flight(CALLSIGN)
    assert type(f) is Aircraft


def test_find_flight_with_aircraft(gta, flight):
    f = gta.get_flight(flight)
    assert f == flight


@pytest.mark.parametrize("ades,expected", [
    (ADES, True)])
# ("LEMD", False)])  # LEMD is not present in the FIR file
# It's uninmplemented in Aircraft.py, so not testing yet
def test_execute_app(gta, flight, ades, expected):
    gta.execute_app(CALLSIGN, ades, IAF)
    assert flight.app_auth is expected


@pytest.mark.parametrize("cfl,expected", [
    (0, True),
    (100, True),
    (1000, False)])
def test_set_cfl(gta, flight, cfl, expected):
    result, max_flightlevel = gta.set_cfl(CALLSIGN, cfl)
    assert result == expected
    if result:
        assert flight.cfl == cfl


def test_set_heading(gta, flight):
    gta.set_heading(CALLSIGN, 185)
    assert flight.tgt_hdg == 185


def test_set_heading_right(gta, flight):
    gta.set_heading(CALLSIGN, 100)
    gta.timer()
    gta.set_heading(CALLSIGN, 10, RIGHT)
    hdg_0 = flight.hdg
    gta.timer()
    hdg_1 = flight.hdg
    assert hdg_1 > hdg_0


def test_set_heading_left(gta, flight):
    gta.set_heading(CALLSIGN, 100)
    gta.timer()
    gta.set_heading(CALLSIGN, 200, LEFT)
    hdg_0 = flight.hdg
    gta.timer()
    hdg_1 = flight.hdg
    assert hdg_1 < hdg_0


@pytest.mark.parametrize("ias,expected", [
    (0, True),
    (100, True),
    (1000, False)])
def test_set_ias(gta, flight, ias, expected):
    result, max_flightlevel = gta.set_ias(CALLSIGN, ias)
    assert result == expected
    if result:
        assert flight.tgt_ias == ias


def test_set_std_spd(gta, flight):
    gta.set_std_spd(CALLSIGN)
