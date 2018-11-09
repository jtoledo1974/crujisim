from crujisim.lib.GTAoffline import GTAoffline


def test_full_run(exc_directory):
    file = exc_directory / "sample.exc"
    gta = GTAoffline(exc_file=str(file), stop_after_minutes=15)
    gta.start()
    pass
