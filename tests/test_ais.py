import pytest
from crujisim.lib import AIS
from pathlib import Path


@pytest.fixture
def ais(fir_file):
    AIS.init(str(fir_file))


def test_load_fir(fir_file):
    AIS.init(str(fir_file))

    assert len(AIS.points) == 69


def test_load_all_firs():
    import crujisim
    basedir = Path(crujisim.__file__).parent
    fir_files = basedir.glob('**/*.fir')

    for f in fir_files:
        AIS.init(str(f))
