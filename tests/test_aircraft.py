from crujisim.lib.Aircraft import Aircraft
from datetime import datetime


def test_init(gta):
    # a = Aircraft.Aircraft(ef.callsign, ef.type, ef.adep, ef.ades,
    #                       float(ef.cfl), float(ef.rfl), ef.route,
    #                       next_wp=ef.fix, next_wp_eto=eto,
    #                       wake_hint=ef.wtc)

    eto = datetime.today()
    Aircraft("test_callsign", "A320", "LEMD", "LECE",
             320., 340., "BELEN,NORTA",
             next_wp="NORTA", next_wp_eto=eto, wake_hint="M")


def test_vect_initialized(gta):
    assert False  # Fallo encontrado al correr otros tests. Pendiente de resolver
