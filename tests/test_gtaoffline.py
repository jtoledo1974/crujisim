from crujisim.lib.GTA import GTA
import pytest

CALLSIGN = "jkk7148"
ADES = "LECE"
IAF = "TERRA"
# FIXTURES


@pytest.fixture
def gta_with_args(exc_file):
    def _gta(file="sample.exc", stop_after_minutes=15, step_callback=None):
        gta = GTA(exc_file=str(exc_file), offline=True,
                  stop_after_minutes=stop_after_minutes, step_callback=step_callback)
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
