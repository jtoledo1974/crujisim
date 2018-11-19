import pytest
import sys
from shutil import copy
from crujisim.lib.GTA import GTA
if sys.version_info >= (3, 0):
    from pathlib import Path
else:
    from pathlib2 import Path


CALLSIGN = "jkk7148"


@pytest.fixture(scope="session")
def exc_directory(tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp("crujisim")
    test_file = Path(__file__)
    test_dir = test_file.parents[0]
    copy(str(test_dir / "sample.exc"), str(tmp_path))
    copy(str(test_dir / "sample.fir"), str(tmp_path))
    return tmp_path


@pytest.fixture(scope="session")
def exc_file(exc_directory):
    exc_file = exc_directory / "sample.exc"
    return exc_file


@pytest.fixture(scope="session")
def fir_file(exc_directory):
    fir_file = exc_directory / "sample.fir"
    return fir_file


@pytest.fixture
def gta(exc_file):
    gta = GTA(exc_file=str(exc_file), offline=True, stop_after_minutes=30)
    return gta


@pytest.fixture
def flight(gta):
    f = gta.get_flight(CALLSIGN)
    return f
