import crujisim.lib.Exercise as clE


def test_load_routedb_no_cache(exc_directory):
    clE.load_routedb(str(exc_directory))
