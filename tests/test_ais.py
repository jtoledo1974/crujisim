import pytest

import crujisim
from crujisim.lib import AIS
from pathlib import Path

basedir = Path(crujisim.__file__).parent
fir_files = basedir.glob('**/*.fir')


@pytest.fixture
def ais(fir_file):
    AIS.init(str(fir_file))


@pytest.fixture(scope='module', params=fir_files)
def ais_n(request):
    AIS.init(str(request.param))


def test_load_fir(fir_file):
    AIS.init(str(fir_file))

    assert len(AIS.points) == 69


def test_points(ais_n):
    for p in AIS.points.values():
        assert isinstance(p.designator, str)
        x, y = p.pos
        assert isinstance(x, float) and isinstance(y, float)


def test_routes(ais_n):
    for route in AIS.routes:
        assert len(route) > 0
        for p in route:
            assert p in (p.pos for p in AIS.points.values())


def test_aerodromes(ais_n):
    assert len(AIS.aerodromes) > 0
