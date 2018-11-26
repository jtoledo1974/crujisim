from crujisim.lib.GTA import GTA

gta = GTA(exc_file="sample.exc", offline=True, stop_after_minutes=300)

for i in range(1, 30):
    gta.start()
