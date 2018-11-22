import pytest

import crujisim
from crujisim.lib import AIS
from pathlib import Path

basedir = Path(crujisim.__file__).parent
fir_files = basedir.glob('**/*.fir')


@pytest.fixture
def ais_sample():
    fir_file = next(basedir.glob('**/sample.fir'))
    AIS.init(fir_file)


@pytest.fixture(scope='module', params=fir_files)
def ais(request):
    AIS.init(str(request.param))
    return request.param


def test_load_fir(ais_sample):
    assert len(AIS.points) == 69


def test_points(ais):
    for p in AIS.points.values():
        assert isinstance(p.designator, str)
        x, y = p.pos
        assert isinstance(x, float) and isinstance(y, float)


def test_routes(ais):
    for route in AIS.routes:
        assert len(route) > 0
        for p in route:
            assert p in (p.pos for p in AIS.points.values())


def test_aerodromes(ais):
    assert len(AIS.aerodromes) > 0


def test_sids_sids(ais):
    for ad in AIS.aerodromes.values():
        for rwy in ad.runwayDirections:
            assert len(rwy.standardInstrumentDepartures) > 0


def test_sids_stars(ais):
    if ais.name in ('Ruta-Convencional.fir', 'Ruta-DGOx6.fir'):
        pytest.skip("No STARS on these")
    for ad in AIS.aerodromes.values():
        for rwy in ad.runwayDirections:
            assert len(rwy.standardInstrumentArrivals) > 0
