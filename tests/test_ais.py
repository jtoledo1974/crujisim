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
    assert repr(next(iter(AIS.points.values()))) == "Point('_TMA1', (80.77, 123.0))"
    ad = next(iter(AIS.aerodromes.values()))
    assert repr(ad) == "AirportHeliport(designator:'LECE', 'runwayDirections'=[RunwayDirection(designator='30', 'stdInstArrivals'={'NORTA1D': STAR('NORTA1D', NORTA, _N1D01, _N1D02, _N1D03, _N1D04, _N1D05, _N1D06, _N1D07, _N1D08, _N1D09, _N1D10, _N1D11, TERRA, end_fix: NORTA), 'MANTO1E': STAR('MANTO1E', MANTO, _AB_CNA, _M1E1, _M1E2, CNA, _CNATERRA, TERRA, _N1D10, _N1D11, TERRA, end_fix: MANTO), 'ROKIS1E': STAR('ROKIS1E', ROKIS, CNA, _CNATERRA, TERRA, _N1D10, _N1D11, TERRA, end_fix: ROKIS), 'TACOS1E': STAR('TACOS1E', TACOS, CNA, _CNATERRA, TERRA, _N1D10, _N1D11, TERRA, end_fix: TACOS), 'DUMAS1D': STAR('DUMAS1D', DUMAS, LURKO, BOPAR, TERRA, end_fix: DUMAS)}, 'stdInstDepartures'={'NORTA1A': SID('NORTA1A', CNA, _COM1, _COM2, _COM3, _N1A0, _N1A1, _N1A2, _N1A3, _N1A4, _N1A5, NORTA, end_fix: NORTA), 'MANTO1A': SID('MANTO1A', CNA, _COM1, _COM2, _COM3, _M1A1, _M1A2, _M1A3, _M1A4, _M1A5, _M1A6, _M1A7, MANTO, end_fix: MANTO), 'ROKIS1A': SID('ROKIS1A', CNA, _COM1, _COM2, _COM3, _R1A1, _R1A2, ROKIS, end_fix: ROKIS), 'TACOS1A': SID('TACOS1A', CNA, _COM1, _COM2, _COM3, _T1A1, _T1A2, TACOS, end_fix: TACOS), 'DUMAS1A': SID('DUMAS1A', CNA, _COM1, _COM2, _COM3, _D1A1, CNA, LURKO, DUMAS, end_fix: DUMAS)}), RunwayDirection(designator='12', 'stdInstArrivals'={'NORTA1D': STAR('NORTA1D', NORTA, CNA, MARES, end_fix: NORTA), 'MANTO1E': STAR('MANTO1E', MANTO, CNA, MARES, end_fix: MANTO), 'ROKIS1E': STAR('ROKIS1E', ROKIS, SISMA, MARES, end_fix: ROKIS), 'TACOS1E': STAR('TACOS1E', TACOS, SISMA, MARES, end_fix: TACOS), 'DUMAS1D': STAR('DUMAS1D', DUMAS, CNA, MARES, end_fix: DUMAS)}, 'stdInstDepartures'={'NORTA1C': SID('NORTA1C', CNA, _COM1, _COM2, _COM3, _N1A1, _N1A2, _N1A3, _N1A4, _N1A5, NORTA, end_fix: NORTA), 'MANTO1C': SID('MANTO1C', CNA, MANTO, end_fix: MANTO), 'ROKIS1C': SID('ROKIS1C', CNA, ROKIS, end_fix: ROKIS), 'TACOS1C': SID('TACOS1C', CNA, TACOS, end_fix: TACOS), 'DUMAS1C': SID('DUMAS1C', CNA, DUMAS, end_fix: DUMAS)})], 'rwyInUse'=RunwayDirection(designator='30', 'stdInstArrivals'={'NORTA1D': STAR('NORTA1D', NORTA, _N1D01, _N1D02, _N1D03, _N1D04, _N1D05, _N1D06, _N1D07, _N1D08, _N1D09, _N1D10, _N1D11, TERRA, end_fix: NORTA), 'MANTO1E': STAR('MANTO1E', MANTO, _AB_CNA, _M1E1, _M1E2, CNA, _CNATERRA, TERRA, _N1D10, _N1D11, TERRA, end_fix: MANTO), 'ROKIS1E': STAR('ROKIS1E', ROKIS, CNA, _CNATERRA, TERRA, _N1D10, _N1D11, TERRA, end_fix: ROKIS), 'TACOS1E': STAR('TACOS1E', TACOS, CNA, _CNATERRA, TERRA, _N1D10, _N1D11, TERRA, end_fix: TACOS), 'DUMAS1D': STAR('DUMAS1D', DUMAS, LURKO, BOPAR, TERRA, end_fix: DUMAS)}, 'stdInstDepartures'={'NORTA1A': SID('NORTA1A', CNA, _COM1, _COM2, _COM3, _N1A0, _N1A1, _N1A2, _N1A3, _N1A4, _N1A5, NORTA, end_fix: NORTA), 'MANTO1A': SID('MANTO1A', CNA, _COM1, _COM2, _COM3, _M1A1, _M1A2, _M1A3, _M1A4, _M1A5, _M1A6, _M1A7, MANTO, end_fix: MANTO), 'ROKIS1A': SID('ROKIS1A', CNA, _COM1, _COM2, _COM3, _R1A1, _R1A2, ROKIS, end_fix: ROKIS), 'TACOS1A': SID('TACOS1A', CNA, _COM1, _COM2, _COM3, _T1A1, _T1A2, TACOS, end_fix: TACOS), 'DUMAS1A': SID('DUMAS1A', CNA, _COM1, _COM2, _COM3, _D1A1, CNA, LURKO, DUMAS, end_fix: DUMAS)}))"


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
            assert len(rwy.stdInstDepartures) > 0


def test_sids_stars(ais):
    if ais.name in ('Ruta-Convencional.fir', 'Ruta-DGOx6.fir'):
        pytest.skip("No STARS on these")
    for ad in AIS.aerodromes.values():
        for rwy in ad.runwayDirections:
            assert len(rwy.stdInstArrivals) > 0
