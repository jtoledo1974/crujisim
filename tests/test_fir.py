import pytest
from crujisim.lib.FIR import FIR


@pytest.fixture
def fir(fir_file):
    fir = FIR(str(fir_file))
    return fir


def test_load_fir(fir_file):
    FIR(str(fir_file))
