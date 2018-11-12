import os.path


def get_file(fn):
    this_dir = os.path.dirname(__file__)
    full_fn = os.path.join(this_dir, fn)
    return full_fn


AIRCRAFT_FILE = get_file("Modelos_avo.txt")
BADA_FILE = get_file("bada.txt")
CALLSIGN_FILE = get_file("Callsigns.txt")
