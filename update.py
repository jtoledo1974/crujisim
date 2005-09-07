import tkMessageBox
import httplib

server = "www.yosoylape.com"

# First, get currently installed version
try:
	f = open('exercise-version', 'r')
	current_version = f.read()
	f.close
except:
	current_version = '2005-05-22'

# Now, try to get latest online version
try:
	conn = httplib.HTTPConnection(server)
	conn.request("GET", "/crujisim/latest-release-exercises")
	r1 = conn.getresponse()
	if (r1.status >= 200) and (r1.status < 400):
		online_version = r1.read()
	else:
		online_version = current_version
	conn.close()
except:
	online_version = current_version

if online_version > current_version:
	root = Tk()
	lbl = Label(root, text="Hay una nueva versión de los ejercicios en la web. ¿Quieres que la descargue automáticamente?")
	def descarga(e=None):
		try:
			conn = httplib.HTTPConnection(server)
			conn.request("GET", "/crujisim/ejercicios.zip")
			r1 = conn.getresponse()
			if (r1.status >= 200) and (r1.status < 400):
				archivo_ejercicios = r1.read()
				f = open('tmp-ejercicios.zip', 'w')
				f.write(archivo_ejercicios)
				f.close()
				zfile = zipfile.ZipFile('tmp-ejercicios.zip')
				test_result = zfile.testzip()
				zfile.close()
				if test_result == None:
					rename('tmp-ejercicios.zip', 'ejercicios.zip')
				else:
					mb = tkMessageBox.Message(type=tkMessageBox.OK, message="Pues parece que el archivo de ejercicios de la web es erróneo... ¡Seguimos con la versión anterior!")
					mb.show()
			else:
					mb = tkMessageBox.Message(type=tkMessageBox.OK, message="No puedo bajarme el archivo de la web... ¡Seguimos con la versión anterior!")
					mb.show()
			conn.close()
		except:
			mb = tkMessageBox.Message(type=tkMessageBox.OK, message="No puedo bajarme el archivo de la web, o el archivo es erróneo... ¡Seguimos con la versión anterior!")
			mb.show()
		root.destroy()
	butSi = Button(root, text="Sí, esclavo", command=descarga)
	def no_descarga(e=None):
		root.destroy()
	butNo = Button(root, text="No, gracias. Estoy bien así", command=no_descarga)
	lbl.grid(row=0, column=0, columnspan=2)
	butSi.grid(row=1, column=0)
	butNo.grid(row=1, column=1)
	root.mainloop()
