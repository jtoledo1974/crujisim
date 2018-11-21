from os.path import dirname, join


def get_file(fn):
    parent_dir = dirname(dirname(__file__))
    full_fn = join(parent_dir, fn)
    return full_fn


AIRCRAFT_FILE = get_file("Modelos_avo.txt")
BADA_FILE = get_file("bada.txt")
CALLSIGN_FILE = get_file("Callsigns.txt")

LEVELS_PER_HOUR_TO_FPM = 100. / 60.
FPM_TO_LEVELS_PER_HOUR = 60. / 100.
LEVELS_TO_FEET = 100.
FEET_TO_LEVELS = 1 / 100.
NM_TO_LEVELS = 6076 / 100.
LEVELS_TO_NM = 100. / 6076
