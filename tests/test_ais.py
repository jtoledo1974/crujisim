import pytest
from crujisim.lib import AIS


@pytest.fixture
def ais(fir_file):
    AIS.init(str(fir_file))


def test_load_fir(fir_file):
    AIS.init(str(fir_file))

    assert len(AIS.points) == 68