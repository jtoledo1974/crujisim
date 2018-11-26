from crujisim.lib.GTA import GTA

gta = GTA(exc_file="sample.exc", offline=True, stop_after_minutes=30)

for i in range(1, 30):
    gta.start()
